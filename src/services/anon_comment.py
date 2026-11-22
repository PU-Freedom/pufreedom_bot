import html
from dataclasses import dataclass
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import (
    UserRepository,
    CommentMappingRepository,
    ChannelThreadMappingRepository
)
from services.messaging import MessageDispatcher
from services.rate_limiting import RateLimiterService
from services.subscription_checker import SubscriptionCheckerService
from common import (
    TelegramLinkParser,
    ParsedLink,
    classifyOwnLink,
    cutRange,
    stripText,
    TextContent,
    buildCommentActionsKeyboard,
    canEditType,
    getMessageLink
)
from exceptions import RateLimitExceeded, NotSubscribedError
from config import settings
import logging

logger = logging.getLogger(__name__)

CHANNEL_USERNAME = settings.CHANNEL_USERNAME
ANON_HELP_TEXT = (
    "📢 <b>Anonymous comment</b>\n\n"
    "<b>Usage:</b>\n"
    "• In a comment section: <code>/anon your text</code>\n"
    f"• From bot: <code>/anon https://t.me/{CHANNEL_USERNAME}/123 your text</code>\n"
    f"• Reply to a comment: <code>/anon https://t.me/{CHANNEL_USERNAME}/123?comment=456 your text</code>\n\n"
    "⚠️ <b>Privacy note:</b> using Telegram's native reply with <code>/anon</code> "
    "can expose your identity (user will see deleted reply from your account).\n"
    "<b>Use a comment link method for full anonymity.</b>\n\n"
    "🚸 <b>Additional note:</b>\n"
    "Its also recommended to send anon messages <b>via bot</b>:\n"
    "<i>Users that are online in chat or have their notifications ON\n"
    "<b>might see your profile.</b></i>"
)
BANNED_TEXT = "❌ You are banned from using this bot 🚮"
FOREIGN_LINK_TEXT = "❌ That link is not a post or comment from our channel."

@dataclass
class AnonArgs:
    parsedLink: Optional[ParsedLink]
    comment: TextContent
    hasNativeReply: bool

class AnonCommentService:
    def __init__(
        self,
        bot: Bot,
        userRepo: UserRepository,
        commentMappingRepo: CommentMappingRepository,
        channelThreadRepo: ChannelThreadMappingRepository,
        rateLimiter: RateLimiterService,
    ):
        self.bot = bot
        self.userRepo = userRepo
        self.commentMappingRepo = commentMappingRepo
        self.channelThreadRepo = channelThreadRepo
        self.rateLimiter = rateLimiter
        self.subscriptionChecker = SubscriptionCheckerService(bot, settings.CHANNEL_ID)
        self.groupDispatcher = MessageDispatcher(bot, settings.DISCUSSION_GROUP_ID)

    async def handle(self, message: Message) -> None:
        if not settings.DISCUSSION_GROUP_ID:
            await message.reply("Comments are not configured for this bot. Plz DM admin, call him a bitch and tell him to kill himself. Thank you.")
            return

        args = self._parseArgs(message)
        if args is None:
            await message.reply(ANON_HELP_TEXT, parse_mode="HTML")
            return

        isInGroup = message.chat.id == settings.DISCUSSION_GROUP_ID
        user = await self.userRepo.getOrCreate(
            telegramId=message.from_user.id,
            username=message.from_user.username,
            firstName=message.from_user.first_name or "",
            lastName=message.from_user.last_name
        )

        if user.isBanned:
            await self._deny(message, isInGroup, BANNED_TEXT)
            return
        isSubscribed, subStatus = await self.subscriptionChecker.isSubscribed(message.from_user.id)
        if not isSubscribed:
            await self._deny(message, isInGroup, NotSubscribedError(status=subStatus).userMessage)
            return

        target = await self._resolveTarget(message, args.parsedLink, args.hasNativeReply)
        if target == "foreign":
            await self._deny(message, isInGroup, FOREIGN_LINK_TEXT, deleteInGroup=False)
            return
        threadId, replyToMessageId = target
        if threadId is None:
            if args.parsedLink:
                await message.reply(
                    "❌ <b>Couldn't find the comment thread for that post.</b>\n\n"
                    "This usually happens for older posts. You have two options:\n\n"
                    "• <b>Open the post's comment section</b> and use <code>/anon your text</code> directly there\n"
                    "• <b>Use a comment link</b> to reply to a specific comment:\n"
                    f'  <code>/anon https://t.me/{settings.CHANNEL_USERNAME}/123?comment=456 your text</code>',
                    parse_mode="HTML"
                )
            else:
                await message.reply(ANON_HELP_TEXT, parse_mode="HTML")
            return

        # last, so typos / unresolvable targets don't burn a slot
        try:
            await self.rateLimiter.acquire(message.from_user.id, scope=RateLimiterService.SCOPE_ANON)
        except RateLimitExceeded as e:
            logger.warning(f"[ANON] rate limit exceeded for user {message.from_user.id}")
            await self._deny(message, isInGroup, e.userMessage)
            return

        replyParams = ReplyParameters(
            message_id=replyToMessageId or threadId,
            chat_id=settings.DISCUSSION_GROUP_ID
        )

        if isInGroup:
            await self._deleteQuietly(message)

        try:
            canEdit = canEditType(message.content_type)
            keyboard = buildCommentActionsKeyboard(canEdit=canEdit)
            result = await self.groupDispatcher.send(
                message,
                replyParams=replyParams,
                newText=args.comment,
                replyMarkup=keyboard,
            )

            await self.commentMappingRepo.create(
                userId=user.id,
                userChatId=message.from_user.id,
                userMessageId=message.message_id,
                groupChatId=settings.DISCUSSION_GROUP_ID,
                groupMessageId=result.messageId,
                channelPostId=threadId
            )
            logger.info(f"[ANON] comment posted: groupMessageId={result.messageId}, threadId={threadId}")

            if replyToMessageId:
                await self._notifyRepliedAnonAuthor(replyToMessageId, result.messageId, args.comment.text)

            if not isInGroup:
                confirmKeyboard = buildCommentActionsKeyboard(
                    canEdit=canEdit,
                    groupMessageId=result.messageId,
                )
                confirmationText = "✅ Your anonymous comment was posted."
                try:
                    await message.answer(
                        confirmationText,
                        reply_parameters=ReplyParameters(
                            message_id=result.messageId,
                            chat_id=settings.DISCUSSION_GROUP_ID,
                        ),
                        reply_markup=confirmKeyboard,
                    )
                except Exception:
                    await message.answer(confirmationText, reply_markup=confirmKeyboard)

        except Exception as e:
            logger.error(f"[ANON] failed to post comment: {e}", exc_info=True)
            # in the group the command is already deleted, so it can't be replied to
            await self._respond(message, isInGroup, "❌ Failed to post your comment. Please try again.")

    def _parseArgs(self, message: Message) -> Optional[AnonArgs]:
        isText = message.text is not None
        text = (message.text if isText else message.caption) or ""
        entities = message.entities if isText else message.caption_entities

        hasMedia = any([
            message.photo, message.video, message.animation,
            message.document, message.audio, message.voice,
            message.video_note, message.sticker
        ])

        stripped = text.lstrip()
        cmdStart = len(text) - len(stripped)
        cmdEnd = cmdStart + (len(stripped.split(None, 1)[0]) if stripped else 0)
        cutEnd = cmdEnd

        parsedLink = None
        rest = text[cmdEnd:]
        restStripped = rest.lstrip()
        if restStripped:
            firstToken = restStripped.split(None, 1)[0]
            parsedLink = TelegramLinkParser.parseExactLink(firstToken)
            if parsedLink:
                cutEnd = cmdEnd + (len(rest) - len(restStripped)) + len(firstToken)

        commentText, commentEntities = cutRange(text, entities, 0, cutEnd)
        commentText, commentEntities = stripText(commentText, commentEntities)

        if not commentText and not hasMedia:
            return None
        return AnonArgs(
            parsedLink=parsedLink,
            comment=TextContent(commentText, commentEntities),
            hasNativeReply=message.reply_to_message is not None,
        )

    async def _resolveTarget(
        self,
        message: Message,
        parsedLink: Optional[ParsedLink],
        hasNativeReply: bool
    ) -> Tuple[Optional[int], Optional[int]] | str:
        """(threadId, replyToMessageId), (None, None) if unresolvable, or "foreign" for links to other chats"""
        inGroup = message.chat.id == settings.DISCUSSION_GROUP_ID
        groupThreadId = message.message_thread_id if inGroup else None

        if parsedLink:
            own = await classifyOwnLink(self.bot, parsedLink)
            if own is None:
                return "foreign"
            kind, _ = own
            if kind == "group":
                return (parsedLink.threadId or parsedLink.messageId, parsedLink.messageId)
            if parsedLink.commentId:
                threadId = await self._lookupThreadId(parsedLink.messageId)
                return (threadId if threadId is not None else parsedLink.commentId, parsedLink.commentId)
            threadId = await self._lookupThreadId(parsedLink.messageId)
            if threadId is not None:
                return (threadId, None)

        # in discussion group - using thread from message context
        if inGroup and groupThreadId:
            replyToMessageId = None
            if hasNativeReply and message.reply_to_message:
                replyToMessageId = message.reply_to_message.message_id
            return (groupThreadId, replyToMessageId)

        return (None, None)

    async def _deny(self, message: Message, isInGroup: bool, text: str, deleteInGroup: bool = True) -> None:
        """in the group the command is public and tied to the user's profile -> delete it and reply in DM"""
        if isInGroup and deleteInGroup:
            await self._deleteQuietly(message)
        await self._respond(message, isInGroup and deleteInGroup, text)

    async def _respond(self, message: Message, privately: bool, text: str) -> None:
        try:
            if privately:
                await self.bot.send_message(message.from_user.id, text, parse_mode="HTML")
            else:
                await message.reply(text, parse_mode="HTML")
        except Exception as e:
            logger.info(f"[ANON] could not notify user {message.from_user.id}: {e}")

    async def _deleteQuietly(self, message: Message) -> None:
        try:
            await self.bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logger.warning(f"[ANON] failed to delete user message {message.message_id}: {e}")

    async def _notifyRepliedAnonAuthor(
        self,
        repliedToMessageId: int,
        replyMessageId: int,
        replyText: Optional[str]
    ) -> None:
        mapping = await self.commentMappingRepo.getByGroupMessageId(
            groupChatId=settings.DISCUSSION_GROUP_ID,
            groupMessageId=repliedToMessageId
        )
        if not mapping:
            return
        commentLink = getMessageLink(settings.DISCUSSION_GROUP_ID, repliedToMessageId)
        replyLink = getMessageLink(settings.DISCUSSION_GROUP_ID, replyMessageId)
        messageParts = [f'<i><b>💬 Someone replied to <a href="{commentLink}">your anonymous comment</a></b></i>']
        if replyText:
            preview = (replyText[:200] + "...") if len(replyText) > 200 else replyText
            messageParts.append(f"\n<b>📝 Preview:</b>\n<blockquote>{html.escape(preview)}</blockquote>")
        messageParts.append(f'\n<b><a href="{replyLink}">View reply</a></b>')
        try:
            await self.bot.send_message(
                chat_id=mapping.userChatId,
                text="\n".join(messageParts),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info(f"[ANON] notified author of comment {repliedToMessageId} about anon reply")
        except Exception as e:
            logger.warning(f"[ANON] failed to notify anon comment author {mapping.userId}: {e}")

    async def _lookupThreadId(self, channelPostId: int) -> Optional[int]:
        mapping = await self.channelThreadRepo.getByChannelPostId(channelPostId)
        if mapping is None:
            logger.warning(f"[ANON] no threadId mapping for channel post {channelPostId}")
            return None
        logger.info(f"[ANON] resolved channel post {channelPostId} -> threadId {mapping.groupThreadId}")
        return mapping.groupThreadId
