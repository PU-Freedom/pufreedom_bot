from aiogram import Router, F, Bot
from aiogram.types import Message, MessageOriginChannel
from aiogram.filters import Command
from db import (
    CommentMappingRepository,
    ChannelThreadMappingRepository
)
from common import buildAliasKeyboard, getMessageLink
from config import settings
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)
router = Router(name="group")

@router.message(
    F.chat.id == settings.DISCUSSION_GROUP_ID,
    F.forward_origin.type == "channel",
    F.forward_origin.chat.id == settings.CHANNEL_ID,
)
async def handleChannelForward(
    message: Message, 
    bot: Bot, 
    redis: Redis, 
    channelThreadRepo: ChannelThreadMappingRepository
):
    """
    when channel post is auto-forwarded to linked discussion group:
    - persist channel_post -> group thread_id mapping to db (used by /anon)
    - attach alias keyboard to the channel post if a pending alias exists
    """
    origin: MessageOriginChannel = message.forward_origin
    channelMsgId = origin.message_id
    if not channelMsgId: return

    try:
        await channelThreadRepo.upsert(channelPostId=channelMsgId, groupThreadId=message.message_id)
        logger.info(f"[THREAD] stored mapping: channelPost={channelMsgId} -> groupThread={message.message_id}")
    except Exception as e:
        logger.warning(f"[THREAD] failed to store thread mapping for post {channelMsgId}: {e}")

    alias = await redis.get(f"pending_alias:{channelMsgId}")
    if not alias: return

    alias = alias.decode() if isinstance(alias, bytes) else alias
    await redis.delete(f"pending_alias:{channelMsgId}")
    try:
        await bot.edit_message_reply_markup(
            chat_id=settings.CHANNEL_ID,
            message_id=channelMsgId,
            reply_markup=buildAliasKeyboard(alias, settings.DISCUSSION_GROUP_ID, message.message_id)
        )
        logger.info(
            f"[ALIAS] attached keyboard to channel message {channelMsgId} "
            f"(group message {message.message_id})"
        )
    except Exception as e:
        logger.warning(f"[ALIAS] failed to edit channel post {channelMsgId}: {e}")


@router.message(
    F.chat.id == settings.DISCUSSION_GROUP_ID,
    Command("anon")
)
async def handleAnonInGroup(message: Message, anonCommentService):
    await anonCommentService.handle(message)


@router.message(
    F.chat.id == settings.DISCUSSION_GROUP_ID,
    F.reply_to_message.as_("replyTo")
)
async def handleReplyToComment(
    message: Message, 
    bot: Bot, 
    commentMappingRepo: CommentMappingRepository, 
    replyTo: Message
):
    if not replyTo: return

    mapping = await commentMappingRepo.getByGroupMessageId(
        groupChatId=message.chat.id,
        groupMessageId=replyTo.message_id
    )
    if not mapping: return

    commentLink = getMessageLink(message.chat.id, replyTo.message_id)
    replyLink = getMessageLink(message.chat.id, message.message_id)
    replyText = message.text or message.caption
    
    messageParts = [f'<i><b>💬 Someone replied to <a href="{commentLink}">your anonymous comment</a></b></i>']
    if replyText:
        preview = (replyText[:200] + "...") if len(replyText) > 200 else replyText
        messageParts.append(f"\n<b>📝 Preview:</b>\n<blockquote>{preview}</blockquote>")
    messageParts.append(f'\n<b><a href="{replyLink}">View reply</a></b>')
    notificationText = "\n".join(messageParts)
    try:
        await bot.send_message(
            chat_id=mapping.userChatId,
            text=notificationText,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logger.info(
            f"[ANON] notified user {mapping.userId} about reply to comment {replyTo.message_id}"
        )
    except Exception as e:
        logger.warning(f"[ANON] failed to notify comment author {mapping.userId}: {e}")
