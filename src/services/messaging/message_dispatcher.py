from typing import Optional
from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message, ReplyParameters, LinkPreviewOptions
from aiogram.exceptions import TelegramAPIError
from common import SendResult, TextContent, originalText, isSupportedType, canEditType
from exceptions import ChannelPostError
import logging

logger = logging.getLogger(__name__)

SPOILER_MEDIA_FIELDS = {
    ContentType.PHOTO: "photo",
    ContentType.VIDEO: "video",
    ContentType.ANIMATION: "animation",
}

class MessageDispatcher:
    """
    sends a user's message into a chat, keeping formatting as native entities:
    - default: copy_message (new caption + entities if changed)
    - text message with changed text: send_message (copy can't replace text)
    - forced spoiler the user didn't set: send_photo/video/animation (copy has no has_spoiler)
    """
    def __init__(self, bot: Bot, chatId: int):
        self.bot = bot
        self.chatId = chatId

    async def send(
        self,
        message: Message,
        replyParams: Optional[ReplyParameters] = None,
        newText: Optional[TextContent] = None,
        forceSpoiler: bool = False,
        replyMarkup=None,
    ) -> SendResult:
        contentType = message.content_type
        if not isSupportedType(contentType):
            raise ChannelPostError(f"Unsupported message type: {contentType}")

        method, params = self._build(message, newText, forceSpoiler)
        params["chat_id"] = self.chatId
        params["parse_mode"] = None
        if replyMarkup:
            params["reply_markup"] = replyMarkup
        if replyParams:
            params["reply_parameters"] = replyParams

        try:
            result = await method(**params)
        except TelegramAPIError as e:
            if "reply_parameters" not in params:
                raise ChannelPostError(f"Telegram API error sending {contentType}: {e}") from e
            logger.warning(f"[DISPATCHER] send failed with reply params ({e}), retrying without")
            params.pop("reply_parameters")
            try:
                result = await method(**params)
            except TelegramAPIError as retryErr:
                raise ChannelPostError(f"Telegram API error sending {contentType}: {retryErr}") from retryErr

        logger.info(f"[DISPATCHER] sent {contentType} to {self.chatId} via {method.__name__}")
        return SendResult(messageId=result.message_id, chatId=self.chatId, canEdit=canEditType(contentType))

    def _build(self, message: Message, newText: Optional[TextContent], forceSpoiler: bool):
        contentType = message.content_type
        field = SPOILER_MEDIA_FIELDS.get(contentType)
        if forceSpoiler and field and not message.has_media_spoiler:
            caption = newText if newText is not None else originalText(message)
            media = message.photo[-1] if field == "photo" else getattr(message, field)
            return getattr(self.bot, f"send_{field}"), {
                field: media.file_id,
                "has_spoiler": True,
                "caption": caption.text or None,
                "caption_entities": caption.entities,
                "show_caption_above_media": message.show_caption_above_media,
            }

        if contentType == ContentType.TEXT and newText is not None and newText.text:
            previewOff = message.link_preview_options and message.link_preview_options.is_disabled
            return self.bot.send_message, {
                "text": newText.text,
                "entities": newText.entities,
                "link_preview_options": LinkPreviewOptions(is_disabled=True) if previewOff else None,
            }

        params = {"from_chat_id": message.chat.id, "message_id": message.message_id}
        if newText is not None and contentType != ContentType.TEXT:
            params["caption"] = newText.text
            params["caption_entities"] = newText.entities
            params["show_caption_above_media"] = message.show_caption_above_media
        return self.bot.copy_message, params
