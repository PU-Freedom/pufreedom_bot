from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, ReplyParameters
from common import (
    requireMessageOwnership,
    isCaption,
    entitiesToHtml,
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
        groupMessage = await _fetchAndDeleteForwardedMessage(
            bot, callback.from_user.id, settings.DISCUSSION_GROUP_ID, groupMessageId
        )
        isCaptionFlag = isCaption(groupMessage)
        currentText = groupMessage.caption if isCaptionFlag else (groupMessage.text or "")
        currentEntities = groupMessage.caption_entities if isCaptionFlag else groupMessage.entities
        formattedText = entitiesToHtml(currentText, currentEntities) if currentText else "(no text)"

        await editService.activateEditMode(
            userId=callback.from_user.id,
            channelMessageId=groupMessageId,
            userMessageId=mapping.userMessageId,
            isCaption=isCaptionFlag,
            targetChatId=settings.DISCUSSION_GROUP_ID,
            isComment=True,
        )
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=buildEditModeMessage(formattedText, isCaptionFlag),
            parse_mode="HTML",
            reply_markup=buildCancelEditKeyboard()
        )
        await callback.answer()
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
    channelMessageId = kwargs['channelMessageId']
    mapping = kwargs['mapping']
    channelMessage = await _fetchAndDeleteForwardedMessage(
        bot, callback.from_user.id, settings.CHANNEL_ID, channelMessageId
    )
    isCaptionFlag = isCaption(channelMessage)
    currentText = channelMessage.caption if isCaptionFlag else (channelMessage.text or "")
    currentEntities = channelMessage.caption_entities if isCaptionFlag else channelMessage.entities
    formattedText = entitiesToHtml(currentText, currentEntities) if currentText else "(no text)"
    logger.debug(f'isCaption flag - {isCaptionFlag}')
    await editService.activateEditMode(
        userId=callback.from_user.id,
        channelMessageId=channelMessageId,
        userMessageId=mapping.userMessageId,
        isCaption=isCaptionFlag
    )
    instructions = buildEditModeMessage(formattedText, isCaptionFlag)
    cancelKeyboard = buildCancelEditKeyboard()
    try:
        await callback.message.answer(
            instructions,
            parse_mode="HTML",
            reply_markup=cancelKeyboard,
            reply_parameters=ReplyParameters(
                message_id=mapping.channelMessageId,
                chat_id=settings.CHANNEL_ID
            )
        )
    except Exception as e:
        logger.warning(f"[EDIT] reply_parameters failed: {e}, sending without")
        await callback.message.answer(
            instructions,
            parse_mode="HTML",
            reply_markup=cancelKeyboard
        )
    await callback.answer()
        
@router.callback_query(F.data.startswith("nsfw_safe:"))
@handleCallbackErrors("Failed to process your decision")
async def handleNSFWSafe(
    callback: CallbackQuery,
    bot: Bot,
    messageForwarder: MessageForwarderService,
    mediaGroupHandler: MediaGroupHandler
):
    await _handleNSFWDecision(
        callback, 
        bot, 
        messageForwarder, 
        mediaGroupHandler, 
        hasSpoiler=False
    )

@router.callback_query(F.data.startswith("nsfw_mark:"))
@handleCallbackErrors("Failed to process your decision")
async def handleNSFWMark(
    callback: CallbackQuery,
    bot: Bot,
    messageForwarder: MessageForwarderService,
    mediaGroupHandler: MediaGroupHandler
):
    await _handleNSFWDecision(
        callback, 
        bot, 
        messageForwarder, 
        mediaGroupHandler, 
        hasSpoiler=True
    )

@router.callback_query(F.data.startswith("nsfw_cancel:"))
@handleCallbackErrors("Failed to cancel")
async def handleNSFWCancel(
    callback: CallbackQuery,
    messageForwarder: MessageForwarderService
):
    messageId = int(callback.data.split(":")[1])
    nsfwDataManager = NSFWDataManager(messageForwarder.redis)
    await nsfwDataManager.cancel(messageId)
    await callback.message.edit_text("🚫 Message cancelled")
    await callback.answer()

async def _handleNSFWDecision(
    callback: CallbackQuery,
    bot: Bot,
    messageForwarder: MessageForwarderService,
    mediaGroupHandler: MediaGroupHandler,
    hasSpoiler: bool
) -> None:
    messageId = int(callback.data.split(":")[1])
    nsfwDataManager = NSFWDataManager(messageForwarder.redis)

    singleMediaData = await nsfwDataManager.retrieveSingleMedia(messageId)
    if singleMediaData:
        originalMessage = await _fetchAndDeleteForwardedMessage(
            bot, callback.from_user.id, singleMediaData['messageChatId'], singleMediaData['messageId']
        )
        user = await messageForwarder.userRepo.getById(singleMediaData['userId'])
        await messageForwarder._sendToChannel(
            originalMessage, 
            user, 
            hasSpoiler=hasSpoiler,
            addWarning=False,
            forceReplyToMessageId=singleMediaData.get('replyToMessageId'),
            forceReplyToChatId=singleMediaData.get('replyToChatId'),
            originalUserMessageId=singleMediaData['messageId'],
            forceQuoteText=singleMediaData.get('quoteText')
        )
        await nsfwDataManager.deleteSingleMedia(messageId)
        await callback.message.delete()
        await callback.answer()
        return
    
    mediaGroupData = await nsfwDataManager.retrieveMediaGroup(messageId)
    if not mediaGroupData:
        await callback.answer("❌ Request expired", show_alert=True)
        return
    
    messageIds = [
        {
            'messageId': messageId,
            'chatId': mediaGroupData['chatId'],
            'userId': mediaGroupData['userId']
        }
        for messageId in mediaGroupData['messageIds']
    ]
    user = await messageForwarder.userRepo.getById(mediaGroupData['userId'])
    await mediaGroupHandler.sendToChannel(
        messageIds,
        user,
        mediaGroupData['chatId'],
        hasSpoiler=hasSpoiler,
        addWarning=False,
        forceReplyToMessageId=mediaGroupData.get('replyToMessageId'),
        forceReplyToChatId=mediaGroupData.get('replyToChatId'),
        forceQuoteText=mediaGroupData.get('quoteText'),
        alias=user.alias
    )
    await nsfwDataManager.deleteMediaGroup(messageId)
    await callback.message.delete()
    await callback.answer()

async def _fetchAndDeleteForwardedMessage(bot: Bot, userId: int, fromChatId: int, messageId: int):
    msg = await bot.forward_message(chat_id=userId, from_chat_id=fromChatId, message_id=messageId)
    await bot.delete_message(chat_id=userId, message_id=msg.message_id)
    return msg