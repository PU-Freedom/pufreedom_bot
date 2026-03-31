from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import UserRepository, CommentMappingRepository, ChannelThreadMappingRepository
from services.messaging import MessageDispatcher
from common import TelegramLinkParser, buildCommentActionsKeyboard, MESSAGE_TYPE_CONFIGS, isSupportedType
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

class AnonCommentService:
    def __init__(
        self,
        bot: Bot,
        userRepo: UserRepository,
        commentMappingRepo: CommentMappingRepository,
        channelThreadRepo: ChannelThreadMappingRepository,
    ):
        self.bot = bot
        self.userRepo = userRepo
        self.commentMappingRepo = commentMappingRepo
        self.channelThreadRepo = channelThreadRepo
        self.groupDispatcher = MessageDispatcher(bot, settings.DISCUSSION_GROUP_ID)

    async def handle(self, message: Message) -> None:
        if not settings.DISCUSSION_GROUP_ID:
            await message.reply("Comments are not configured for this bot. Plz DM admin, call him a bitch and tell him to kill himself. Thank you.")
            return

        parsedArgs = self._parseArgs(message)
        if parsedArgs is None:
            await message.reply(ANON_HELP_TEXT, parse_mode="HTML")
            return

        link, commentText, hasNativeReply = parsedArgs

        user = await self.userRepo.getOrCreate(
            telegramId=message.from_user.id,
            username=message.from_user.username,
            firstName=message.from_user.first_name or "",
            lastName=message.from_user.last_name
        )

        threadId, replyToMessageId = await self._resolveTarget(message, link, hasNativeReply)
        if threadId is None:
            if link:
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

        if replyToMessageId:
            replyParams = ReplyParameters(
                message_id=replyToMessageId,
                chat_id=settings.DISCUSSION_GROUP_ID
            )
        else:
            replyParams = ReplyParameters(
                message_id=threadId,
                chat_id=settings.DISCUSSION_GROUP_ID
            )

        isInGroup = message.chat.id == settings.DISCUSSION_GROUP_ID
        if isInGroup:
            try:
                await self.bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                logger.warning(f"[ANON] failed to delete user message {message.message_id}: {e}")

        try:
            canEdit = (
                isSupportedType(message.content_type)
                and MESSAGE_TYPE_CONFIGS[message.content_type].canEdit
            )
            keyboard = buildCommentActionsKeyboard(canEdit=canEdit)
            result = await self.groupDispatcher.send(
                message,
                replyParams=replyParams,
                overrideCaption=commentText,
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
            logger.info(
                f"[ANON] comment posted: groupMessageId={result.messageId}, "
                f"threadId={threadId}, userId={user.id}"
            )

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
                    await message.answer(
                        confirmationText,
                        reply_markup=confirmKeyboard,
                    )

        except Exception as e:
            logger.error(f"[ANON] failed to post comment: {e}", exc_info=True)
            await message.reply("❌ Failed to post your comment. Please try again.")

    def _parseArgs(self, message: Message) -> Optional[Tuple[Optional[str], str, bool]]:
        text = message.text or message.caption or ""
        parts = text.split(None, 1)
        remainder = parts[1].strip() if len(parts) > 1 else ""

        hasMedia = any([
            message.photo, message.video, message.animation,
            message.document, message.audio, message.voice,
            message.video_note, message.sticker
        ])

        link = None
        commentText = remainder

        if remainder:
            firstToken = remainder.split()[0]
            if TelegramLinkParser.parseMessageLink(firstToken):
                link = firstToken
                commentText = remainder[len(firstToken):].strip()

        if not commentText and not hasMedia: return None

        hasNativeReply = message.reply_to_message is not None
        return (link, commentText or None, hasNativeReply)

    async def _resolveTarget(
        self,
        message: Message,
        link: Optional[str],
        hasNativeReply: bool
    ) -> Tuple[Optional[int], Optional[int]]:
        inGroup = message.chat.id == settings.DISCUSSION_GROUP_ID
        groupThreadId = message.message_thread_id if inGroup else None

        # explicit link
        if link:
            parsed = TelegramLinkParser.parseMessageLink(link)
            if parsed:
                if parsed.commentId:
                    threadId = await self._lookupThreadId(parsed.messageId)
                    if threadId is None:
                        threadId = parsed.commentId
                    return (threadId, parsed.commentId)
                else:
                    threadId = await self._lookupThreadId(parsed.messageId)
                    if threadId is not None:
                        return (threadId, None)

        # in discussion group - using thread from message context
        if inGroup and groupThreadId:
            replyToMessageId = None
            if hasNativeReply and message.reply_to_message:
                replyToMessageId = message.reply_to_message.message_id
            return (groupThreadId, replyToMessageId)

        # private chat with no resolvable link
        return (None, None)

    async def _lookupThreadId(self, channelPostId: int) -> Optional[int]:
        mapping = await self.channelThreadRepo.getByChannelPostId(channelPostId)
        if mapping is None:
            logger.warning(f"[ANON] no threadId mapping for channel post {channelPostId}")
            return None
        logger.info(f"[ANON] resolved channel post {channelPostId} -> threadId {mapping.groupThreadId}")
        return mapping.groupThreadId
