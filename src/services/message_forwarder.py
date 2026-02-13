from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import UserRepository, MessageMappingRepository
from services.reply_resolver import ReplyResolverService
from services.rate_limiter import RateLimiterService
from services.media import MediaGroupHandler
from services.message_dispatcher import MessageDispatcher
from services.nsfw import NSFWChecker, NSFWDataManager
from common import (
    buildMessageActionsKeyboardFromMessage,
    buildNSFWPromptKeyboard,
    MappingUtil,
    TelegramLinkParser
)
from exceptions import (
    MessageForwardError,
    RateLimitExceeded
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

        await self.rateLimiter.checkRateLimit(message.from_user.id)
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
        replyChannelMessageId = None
        replyChannelChatId = None
        if message.reply_to_message:
            mapping = await self.messageMappingRepo.getByUserMessageOrLastEditMessage(
                userChatId=message.reply_to_message.chat.id,
                userMessageId=message.reply_to_message.message_id
            )
            if mapping:
                replyChannelMessageId = mapping.channelMessageId
                replyChannelChatId = mapping.channelChatId
                logger.info(
                    f"[NSFW_CHECK] reply target mapped: "
                    f"channelMessageId={replyChannelMessageId}"
                )
            else:
                logger.warning(
                    f"[NSFW_CHECK] no mapping for reply target "
                    f"userMessageId={message.reply_to_message.message_id}"
                )
        quoteText = message.quote.text if message.quote else None
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
                forceQuoteText=quoteText
            )
        else:
            await self.nsfwDataManager.storeSingleMedia(
                messageId=message.message_id,
                userId=user.id,
                messageChatId=message.chat.id,
                replyToMessageId=replyChannelMessageId,
                replyToChatId=replyChannelChatId,
                quoteText=quoteText
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
        forceQuoteText: str = None
    ) -> None:
        result = None
        try:
            replyParams = await self._resolveReplyParams(
                message, forceReplyToMessageId, forceReplyToChatId, forceQuoteText
            )
            overrideCaption = None
            if replyParams and not message.reply_to_message and not message.external_reply:
                messageText = message.text or message.caption or ""
                extractedLink = TelegramLinkParser.extractLinkFromText(messageText)
                if extractedLink:
                    cleanedText = messageText.replace(extractedLink, "").strip()
                    logger.info(f"[FORWARDER] removed link from message: {extractedLink}")
                    overrideCaption = cleanedText if cleanedText else None
            
            if addWarning:
                warningText = (
                    "<blockquote><b>⚠️ NSFW content warning</b>\n"
                    "This media was detected as NSFW</blockquote>\n\n"
                )
                baseText = overrideCaption or message.caption or message.text or ""
                overrideCaption = warningText + baseText
            result = await self.dispatcher.send(
                message,
                replyParams=replyParams,
                hasSpoiler=hasSpoiler,
                overrideCaption=overrideCaption
            )
            await self.rateLimiter.recordMessage(message.from_user.id)
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
            logger.error(f"error sending to channel: {e}", exc_info=True)
            raise MessageForwardError(str(e))

    async def _resolveReplyParams(
        self,
        message: Message,
        forceReplyToMessageId: int = None,
        forceReplyToChatId: int = None,
        forceQuoteText: str = None
    ) -> ReplyParameters | None:
        if forceReplyToMessageId and forceReplyToChatId:
            logger.info(
                f"[FORWARDER] using forced reply: "
                f"messageId={forceReplyToMessageId}, chatId={forceReplyToChatId}, "
                f"hasQuote={forceQuoteText is not None}"
            )
            params = ReplyParameters(
                message_id=forceReplyToMessageId,
                chat_id=forceReplyToChatId
            )
            if forceQuoteText:
                params = ReplyParameters(
                    message_id=forceReplyToMessageId,
                    chat_id=forceReplyToChatId,
                    quote=forceQuoteText,
                    quote_parse_mode="HTML"
                )
            return params
        replyParams = await self.replyResolver.resolve(message, self.CHANNEL_ID)
        if replyParams:
            logger.info(f"[FORWARDER] resolved reply: messageId={replyParams.message_id}, chatId={replyParams.chat_id}")
        else:
            logger.info(f"[FORWARDER] no reply params")
        return replyParams
    
    async def _sendConfirmation(self, originalMessage: Message, result) -> None:
        keyboard = None
        if result.sentMessage:
            keyboard = buildMessageActionsKeyboardFromMessage(result.messageId, result.sentMessage)
        elif result.sentMessage is None:
            from common import buildMessageActionsKeyboard
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
