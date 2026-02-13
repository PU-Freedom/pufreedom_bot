from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyParameters
)
from common import (
    requireMessageOwnership, 
    isCaption, 
    entitiesToHtml,
    handleCallbackErrors,
    handleDeleteErrors,
    handleEditErrors
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
    channelMessage = await bot.forward_message(
        chat_id=callback.from_user.id,
        from_chat_id=settings.CHANNEL_ID,
        message_id=channelMessageId
    )
    await bot.delete_message(
        chat_id=callback.from_user.id,
        message_id=channelMessage.message_id
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
    cancelKeyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Cancel edit", callback_data="cancel_edit")]
    ])
    separator = '-' * 10
    instructions = (
        f"<b>✏️ Edit mode activated</b>\n\n"
        f"<b>Current text:</b>\n"
        f"{separator}\n"
        f"<blockquote>{formattedText}</blockquote>\n"
        f"{separator}\n"
        f"<b>Send the new {'caption' if isCaptionFlag else 'text'}</b>"
    )
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
        originalMessage = await bot.forward_message(
            chat_id=callback.from_user.id,
            from_chat_id=singleMediaData['messageChatId'],
            message_id=singleMediaData['messageId']
        )
        await bot.delete_message(
            chat_id=callback.from_user.id,
            message_id=originalMessage.message_id
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
        forceQuoteText=mediaGroupData.get('quoteText')
    )
    await nsfwDataManager.deleteMediaGroup(messageId)
    await callback.message.delete()
    await callback.answer()
