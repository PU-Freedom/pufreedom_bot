from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import UserRepository, MessageMappingRepository
from services.reply_resolver import ReplyResolverService
from services.rate_limiting import RateLimiterService
from services.media import MediaGroupHandler
from services.messaging import MessageDispatcher
from services.moderation import NSFWChecker, NSFWDataManager
from services.subscription_checker import SubscriptionCheckerService
from common import (
    buildMessageActionsKeyboard,
    buildNSFWPromptKeyboard,
    buildAliasKeyboard,
    MappingUtil,
    ReplyParametersBuilder,
    entitiesToHtml,
    removeLink,
    LinkMatch,
    NSFW_WARNING_HTML,
)
from exceptions import (
    MessageForwardError,
    RateLimitExceeded,
    NotSubscribedError,
)
from config import settings
import logging

logger = logging.getLogger(__name__)

class MessageForwarderService:
    def __init__(
        self,
        bot: Bot,
        userRepo: UserRepository,
        messageMappingRepo: MessageMappingRepository,
        replyResolver: ReplyResolverService,
        rateLimiter: RateLimiterService,
        nsfwChecker: NSFWChecker,
        redis
    ):
        self.bot = bot
        self.userRepo = userRepo
        self.messageMappingRepo = messageMappingRepo
        self.replyResolver = replyResolver
        self.rateLimiter = rateLimiter
        self.nsfwChecker = nsfwChecker
        self.redis = redis
        self.CHANNEL_ID = settings.CHANNEL_ID

        self.dispatcher = MessageDispatcher(bot, self.CHANNEL_ID)
        self.mediaGroupHandler = MediaGroupHandler(
            bot, userRepo, messageMappingRepo, replyResolver, nsfwChecker, redis
        )
        self.nsfwDataManager = NSFWDataManager(redis)
        self.subscriptionChecker = SubscriptionCheckerService(bot, self.CHANNEL_ID)

    async def forwardMessage(self, message: Message) -> None:
        self._logIncoming(message)
        user = await self.userRepo.getOrCreate(
            telegramId=message.from_user.id,
            username=message.from_user.username,
            firstName=message.from_user.first_name or "",
            lastName=message.from_user.last_name
        )
        if user.isBanned:
            await message.reply("❌ You are banned from using this bot 🚮")
            return

        isSubscribed, subStatus = await self.subscriptionChecker.isSubscribed(message.from_user.id)
        if not isSubscribed:
            logger.info(f"[SUB_CHECK] user {message.from_user.id} blocked - status={subStatus}")
            if user.alias:
                await self.userRepo.clearAlias(user.id)
                logger.info(f"[SUB_CHECK] cleared alias for unsubscribed user {user.telegramId}")
            raise NotSubscribedError(status=subStatus)

        # counted on arrival, not after sending - nsfw prompts and albums send later from a different message
        allowed = await self.rateLimiter.acquire(message.from_user.id, groupId=message.media_group_id)
        if not allowed:
            logger.info(f"[RATE_LIMIT] dropping item of rejected album {message.media_group_id}")
            return
        if message.media_group_id:
            await self.mediaGroupHandler.handleMediaGroupMessage(message, user)
            return

        hasMedia = message.photo or message.video or message.animation
        if settings.ENABLE_NSFW_CHECK and hasMedia:
            await self._handleNSFWCheck(message, user)
        else:
            await self._sendToChannel(message, user)

    async def _handleNSFWCheck(self, message: Message, user):
        logger.info(f"[NSFW_CHECK] checking messageId - {message.message_id}")
        replyParams, consumedLink = await self.replyResolver.resolveWithLink(message, self.CHANNEL_ID)
        replyChannelMessageId = replyParams.message_id if replyParams else None
        replyChannelChatId = replyParams.chat_id if replyParams else None
        quoteText = message.quote.text if message.quote else None
        stripReplyLink = consumedLink is not None
        if settings.ENFORCED_NSFW_CHECK:
            isSafe, reason = await self.nsfwChecker.checkMessage(self.bot, message)
            hasSpoiler = addWarning = False
            if not isSafe:
                logger.warning(f"[NSFW_CHECK] NSFW auto-detected from user {message.from_user.id}: {reason}")
                await message.reply(
                    f"🔞 <b>NSFW content detected</b>\n\n"
                    f"Reason: {reason}\n"
                    f"Your message will be posted with a spoiler and warning",
                    parse_mode="HTML"
                )
                hasSpoiler = addWarning = True
            await self._sendToChannel(
                message, user, hasSpoiler=hasSpoiler, addWarning=addWarning,
                forceReplyToMessageId=replyChannelMessageId,
                forceReplyToChatId=replyChannelChatId,
                forceQuoteText=quoteText,
                stripReplyLink=stripReplyLink,
            )
        else:
            await self.nsfwDataManager.storeSingleMedia(
                messageId=message.message_id,
                userId=user.id,
                messageChatId=message.chat.id,
                replyToMessageId=replyChannelMessageId,
                replyToChatId=replyChannelChatId,
                quoteText=quoteText,
                stripReplyLink=stripReplyLink,
            )
            await message.reply(
                "<b>📸 Media detected</b>\n\n"
                "Does this contain NSFW/Sensitive content(or a spoiler)?\n"
                "Marking as NSFW will add a spoiler blur",
                parse_mode="HTML",
                reply_markup=buildNSFWPromptKeyboard(message.message_id)
            )

    async def _sendToChannel(
        self,
        message: Message,
        user,
        hasSpoiler: bool = False,
        addWarning: bool = False,
        forceReplyToMessageId: int = None,
        forceReplyToChatId: int = None,
        originalUserMessageId: int = None,
        forceQuoteText: str = None,
        stripReplyLink: bool = False,
    ) -> None:
        """stripReplyLink: forced reply target came from a link in the text, so remove that link"""
        result = None
        try:
            replyParams, consumedLink = await self._resolveReplyParams(
                message, forceReplyToMessageId, forceReplyToChatId, forceQuoteText, stripReplyLink
            )
            isText = message.text is not None
            text = message.text if isText else message.caption
            entities = message.entities if isText else message.caption_entities

            overrideCaption = None
            if consumedLink and text:
                cleanedText, cleanedEntities = removeLink(text, entities, consumedLink)
                logger.info(f"[FORWARDER] removing consumed reply link: {consumedLink.url}")
                if cleanedText:
                    overrideCaption = entitiesToHtml(cleanedText, cleanedEntities)
                elif not isText:
                    overrideCaption = ""

            if addWarning:
                baseText = overrideCaption if overrideCaption is not None else entitiesToHtml(text, entities)
                overrideCaption = NSFW_WARNING_HTML + baseText

            alias = user.alias
            result = await self.dispatcher.send(
                message,
                replyParams=replyParams,
                hasSpoiler=hasSpoiler,
                overrideCaption=overrideCaption,
            )

            if alias:
                try:
                    await self.bot.edit_message_reply_markup(
                        chat_id=self.CHANNEL_ID,
                        message_id=result.messageId,
                        reply_markup=buildAliasKeyboard(alias)
                    )
                except Exception as e:
                    logger.warning(f"[ALIAS] failed to attach alias keyboard to {result.messageId}: {e}")
                if settings.DISCUSSION_GROUP_ID:
                    await self.redis.setex(f"pending_alias:{result.messageId}", 60, alias)
                    logger.info(f"[ALIAS] stored pending alias for channel msg {result.messageId}")

            mappingUserMessageId = originalUserMessageId or message.message_id
            await MappingUtil.createAndLog(
                self.messageMappingRepo,
                userId=user.id,
                userChatId=message.chat.id,
                userMessageId=mappingUserMessageId,
                channelChatId=result.chatId,
                channelMessageId=result.messageId
            )
            await self._sendConfirmation(message, result)
        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"error in _sendToChannel: {e}", exc_info=True)
            raise MessageForwardError(str(e))

    async def _resolveReplyParams(
        self,
        message: Message,
        forceReplyToMessageId: int = None,
        forceReplyToChatId: int = None,
        forceQuoteText: str = None,
        stripReplyLink: bool = False,
    ) -> tuple[ReplyParameters | None, LinkMatch | None]:
        if forceReplyToMessageId and forceReplyToChatId:
            logger.info(
                f"[FORWARDER] using forced reply: "
                f"messageId={forceReplyToMessageId}, chatId={forceReplyToChatId}, "
                f"hasQuote={forceQuoteText is not None}"
            )
            replyParams = ReplyParametersBuilder.build(
                messageId=forceReplyToMessageId,
                chatId=forceReplyToChatId,
                quoteText=forceQuoteText,
                source="FORWARDER_FORCED"
            )
            consumedLink = None
            if stripReplyLink:
                # re-find on this message so offsets/entity identity match its own text
                _, consumedLink = await self.replyResolver.findOwnLink(message)
            return replyParams, consumedLink
        return await self.replyResolver.resolveWithLink(message, self.CHANNEL_ID)
    
    async def _sendConfirmation(self, originalMessage: Message, result) -> None:
        keyboard = None
        keyboard = buildMessageActionsKeyboard(result.messageId, canEdit=result.canEdit)
        confirmationText = "😍 Your message was sent to the channel 💓💗"
        try:
            await self.bot.send_message(
                chat_id=originalMessage.chat.id,
                text=confirmationText,
                reply_parameters=ReplyParameters(
                    message_id=result.messageId,
                    chat_id=result.chatId
                ),
                reply_markup=keyboard
            )
            logger.info(f"[CONFIRMATION] sent with cross-chat reply to channel message {result.messageId}")
            return
        except Exception as e:
            logger.warning(f"[CONFIRMATION] cross-chat reply failed: {e}")
        
        try:
            await self.bot.send_message(
                chat_id=originalMessage.chat.id,
                text=confirmationText,
                reply_parameters=ReplyParameters(
                    message_id=originalMessage.message_id
                ),
                reply_markup=keyboard
            )
            logger.info(f"[CONFIRMATION] sent with reply to USER MESSAGE {originalMessage.message_id}")
            return
        except Exception as e:
            logger.warning(f"[CONFIRMATION] reply to user message failed: {e}")
        
        try:
            await self.bot.send_message(
                chat_id=originalMessage.chat.id,
                text=confirmationText,
                reply_markup=keyboard
            )
            logger.info(f"[CONFIRMATION] sent WITHOUT reply parameters")
        except Exception as e:
            logger.error(f"[CONFIRMATION] all attempts failed: {e}")
            raise

    def _logIncoming(self, message: Message):
        logger.info(f"[FORWARD_START] {'=' * 5} NEW MESSAGE {'=' * 5}")
        logger.info(f"[FORWARD_START] messageId={message.message_id}, contentType={message.content_type}")
        logger.info(f"[FORWARD_START] hasReply={message.reply_to_message is not None}")
        if message.reply_to_message:
            logger.info(
                f"[FORWARD_START] replyTo: messageId={message.reply_to_message.message_id}, "
                f"chatId={message.reply_to_message.chat.id}"
            )
        if message.quote:
            logger.info(f"[FORWARD_START] quote: {message.quote.text[:100] if message.quote.text else None}")
        if message.media_group_id:
            logger.info(f"[FORWARD_START] mediaGroupId={message.media_group_id}")
        logger.info(f"[FORWARD_START] {'=' * 7}")
