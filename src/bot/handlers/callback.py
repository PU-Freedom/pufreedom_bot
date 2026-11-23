from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, ReplyParameters
from common import (
    requireMessageOwnership,
    isCaption,
    handleCallbackErrors,
    handleDeleteErrors,
    handleEditErrors,
    buildCancelEditKeyboard,
    buildEditModeMessage,
)
from services import (
    EditService, 
    MessageForwarderService, 
    MediaGroupHandler,
    NSFWDataManager
)
from config import settings
import logging
import json

logger = logging.getLogger(__name__)
router = Router(name="callbacks")

@router.callback_query(F.data.startswith("delete:"))
@requireMessageOwnership
@handleDeleteErrors("✅ Message deleted")
async def handleDelete(
    callback: CallbackQuery,
    bot: Bot,
    messageMappingRepo,
    mapping,
    redis,
    channelMessageId: int
):
    await bot.delete_message(
        chat_id=settings.CHANNEL_ID,
        message_id=channelMessageId
    )
    await messageMappingRepo.markAsDeleted(
        channelChatId=settings.CHANNEL_ID,
        channelMessageId=channelMessageId
    )
    siblingsRaw = await redis.get(f"media_group_siblings:{channelMessageId}")
    if siblingsRaw:
        for siblingId in json.loads(siblingsRaw):
            await bot.delete_message(chat_id=settings.CHANNEL_ID, message_id=siblingId)
            await messageMappingRepo.markAsDeleted(channelChatId=settings.CHANNEL_ID, channelMessageId=siblingId)
        await redis.delete(f"media_group_siblings:{channelMessageId}")
    await callback.message.edit_text("🗑 Message deleted from channel")

@router.callback_query(F.data.startswith("comment_delete"))
async def handleCommentDelete(
    callback: CallbackQuery,
    bot: Bot,
    commentMappingRepo,
    userRepo,
):
    parts = callback.data.split(":")
    groupMessageId = int(parts[1]) if len(parts) > 1 else callback.message.message_id
    mapping = await commentMappingRepo.getByGroupMessageId(
        groupChatId=settings.DISCUSSION_GROUP_ID,
        groupMessageId=groupMessageId
    )
    if not mapping:
        await callback.answer("❌ Comment not found or already deleted", show_alert=True)
        return

    user = await userRepo.getByTelegramId(callback.from_user.id)
    if not user or (mapping.userId != user.id and not user.isAdmin):
        await callback.answer("❌ You can only delete your own comments", show_alert=True)
        return

    try:
        await bot.delete_message(chat_id=settings.DISCUSSION_GROUP_ID, message_id=groupMessageId)
        await commentMappingRepo.updateById(mapping.id, isDeleted=True)
        await callback.answer("🗑 Comment deleted")
    except Exception as e:
        logger.error(f"[COMMENT DELETE] failed: {e}", exc_info=True)
        await callback.answer("❌ Failed to delete", show_alert=True)

@router.callback_query(F.data.startswith("comment_edit"))
async def handleCommentEditRequest(
    callback: CallbackQuery,
    bot: Bot,
    commentMappingRepo,
    userRepo,
    editService: EditService,
):
    parts = callback.data.split(":")
    groupMessageId = int(parts[1]) if len(parts) > 1 else callback.message.message_id
    mapping = await commentMappingRepo.getByGroupMessageId(
        groupChatId=settings.DISCUSSION_GROUP_ID,
        groupMessageId=groupMessageId
    )
    if not mapping:
        await callback.answer("❌ Comment not found or already deleted", show_alert=True)
        return

    user = await userRepo.getByTelegramId(callback.from_user.id)
    if not user or mapping.userId != user.id:
        await callback.answer("❌ You can only edit your own comments", show_alert=True)
        return

    try:
        await _startEditMode(
            callback, bot, editService,
            fromChatId=settings.DISCUSSION_GROUP_ID,
            messageId=groupMessageId,
            userMessageId=mapping.userMessageId,
            isComment=True,
        )
    except Exception as e:
        logger.error(f"[COMMENT_EDIT] failed: {e}", exc_info=True)
        await callback.answer("❌ Failed to start edit mode", show_alert=True)


@router.callback_query(F.data == "cancel_edit")
@handleCallbackErrors("Failed to cancel edit mode")
async def cancelEdit(callback: CallbackQuery, editService: EditService):
    await editService.deactivateEditMode(callback.from_user.id)
    await callback.message.edit_text("edit mode cancelled")
    await callback.answer()

@router.callback_query(F.data.startswith("edit:"))
@requireMessageOwnership
@handleEditErrors()
async def handleEditRequest(
    callback: CallbackQuery,
    bot: Bot,
    editService: EditService,
    **kwargs,
):
    await _startEditMode(
        callback, bot, editService,
        fromChatId=settings.CHANNEL_ID,
        messageId=kwargs['channelMessageId'],
        userMessageId=kwargs['mapping'].userMessageId,
    )

@router.callback_query(F.data.startswith("alias:"))
async def handleAliasTap(callback: CallbackQuery):
    await callback.answer(f"✍️ Posted by {callback.data.split(':', 1)[1]}")

@router.callback_query(F.data.startswith("nsfw_safe:"))
@handleCallbackErrors("Failed to process your decision")
async def handleNSFWSafe(
    callback: CallbackQuery,
    messageForwarder: MessageForwarderService,
    mediaGroupHandler: MediaGroupHandler
):
    await _handleNSFWDecision(callback, messageForwarder, mediaGroupHandler, hasSpoiler=False)

@router.callback_query(F.data.startswith("nsfw_mark:"))
@handleCallbackErrors("Failed to process your decision")
async def handleNSFWMark(
    callback: CallbackQuery,
    messageForwarder: MessageForwarderService,
    mediaGroupHandler: MediaGroupHandler
):
    await _handleNSFWDecision(callback, messageForwarder, mediaGroupHandler, hasSpoiler=True)

@router.callback_query(F.data.startswith("nsfw_cancel:"))
@handleCallbackErrors("Failed to cancel")
async def handleNSFWCancel(
    callback: CallbackQuery,
    messageForwarder: MessageForwarderService
):
    messageId = int(callback.data.split(":")[1])
    nsfwDataManager = NSFWDataManager(messageForwarder.redis)
    await nsfwDataManager.cancel(callback.message.chat.id, messageId)
    await callback.message.edit_text("🚫 Message cancelled")
    await callback.answer()

async def _handleNSFWDecision(
    callback: CallbackQuery,
    messageForwarder: MessageForwarderService,
    mediaGroupHandler: MediaGroupHandler,
    hasSpoiler: bool
) -> None:
    messageId = int(callback.data.split(":")[1])
    chatId = callback.message.chat.id
    nsfwDataManager = NSFWDataManager(messageForwarder.redis)

    pending = await nsfwDataManager.claim(chatId, messageId)
    if not pending:
        await callback.answer("❌ Request expired", show_alert=True)
        return
    try:
        user = await messageForwarder.userRepo.getById(pending.userId)
        if pending.messages[0].media_group_id:
            await mediaGroupHandler.sendToChannel(pending.messages, user, hasSpoiler=hasSpoiler)
        else:
            await messageForwarder._sendToChannel(pending.messages[0], user, hasSpoiler=hasSpoiler)
    except Exception:
        await nsfwDataManager.restore(chatId, messageId, pending)
        raise
    await callback.message.delete()
    await callback.answer()

async def _startEditMode(
    callback: CallbackQuery,
    bot: Bot,
    editService: EditService,
    fromChatId: int,
    messageId: int,
    userMessageId: int,
    isComment: bool = False,
) -> None:
    # the forwarded copy is the preview - it keeps all formatting and can be copied from
    preview = await bot.forward_message(chat_id=callback.from_user.id, from_chat_id=fromChatId, message_id=messageId)
    isCaptionFlag = isCaption(preview)
    await editService.activateEditMode(
        userId=callback.from_user.id,
        channelMessageId=messageId,
        userMessageId=userMessageId,
        isCaption=isCaptionFlag,
        targetChatId=fromChatId,
        isComment=isComment,
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=buildEditModeMessage(isCaptionFlag),
        reply_markup=buildCancelEditKeyboard(),
        reply_parameters=ReplyParameters(message_id=preview.message_id),
    )
    await callback.answer()
