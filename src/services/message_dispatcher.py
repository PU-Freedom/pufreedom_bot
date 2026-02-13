from typing import Optional, NamedTuple
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ContentType
from services.text_handler import TextMessageHandler
from services.poll_handler import PollMessageHandler
from services.media import MediaMessageHandler
from exceptions import ChannelPostError
from common import SendResult
import logging

logger = logging.getLogger(__name__)

class MessageDispatcher:
    def __init__(self, bot: Bot, channelChatId: int):
        self.bot = bot
        self.channelChatId = channelChatId
        self.textHandler = TextMessageHandler(bot)
        self.mediaHandler = MediaMessageHandler(bot)
        self.pollHandler = PollMessageHandler(bot)
        self._handlers = {
            ContentType.TEXT: self._handleText,
            ContentType.PHOTO: self._handlePhoto,
            ContentType.VIDEO: self._handleVideo,
            ContentType.ANIMATION: self._handleAnimation,
            ContentType.DOCUMENT: self._handleDocument,
            ContentType.POLL: self._handlePoll,
            ContentType.STICKER: self._handleSticker,
        }

    async def send(
        self,
        message: Message,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None
    ) -> SendResult:
        contentType = message.content_type
        handler = self._handlers.get(contentType)
        if not handler:
            raise ChannelPostError(f"Unsupported message type: {contentType}")

        logger.debug(f"[DISPATCHER] routing {contentType} message")
        try:
            return await handler(
                message=message,
                replyParams=replyParams,
                hasSpoiler=hasSpoiler,
                overrideCaption=overrideCaption
            )
        except TelegramBadRequest as e:
            if "REPLY_MESSAGE_ID_INVALID" in str(e) and replyParams:
                logger.warning(f"[DISPATCHER] reply_parameters failed, adding reply context to text")
                
                replyPrefix = self._buildReplyPrefix(replyParams)
                if contentType == ContentType.TEXT:
                    overrideCaption = replyPrefix + (message.text or "")
                else:
                    overrideCaption = replyPrefix + (overrideCaption or message.caption or "")
                return await handler(
                    message=message,
                    replyParams=None,
                    hasSpoiler=hasSpoiler,
                    overrideCaption=overrideCaption
                )
            else:
                raise

    def _buildReplyPrefix(self, replyParams: ReplyParameters) -> str:
        from common import getMessageLink
        messageLink = getMessageLink(replyParams.chat_id, replyParams.message_id)
        return f"<b>↩️ <a href='{messageLink}'>Replying to message</a></b>\n\n"

    async def _handleText(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters], 
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> SendResult:
        result = await self.textHandler.sendTextMessage(
            message, 
            self.channelChatId, 
            replyParams,
            overrideText=overrideCaption
        )
        return SendResult(result.message_id, self.channelChatId, None, canEdit=True)

    async def _handlePhoto(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters],
        hasSpoiler: bool = False, 
        overrideCaption: Optional[str] = None, 
        **kwargs
    ) -> SendResult:
        sentMessage = await self.mediaHandler.sendPhotoMessage(
            message, self.channelChatId, replyParams, hasSpoiler, overrideCaption
        )
        return SendResult(sentMessage.message_id, self.channelChatId, sentMessage, canEdit=True)

    async def _handleVideo(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters],
        hasSpoiler: bool = False, 
        overrideCaption: Optional[str] = None, 
        **kwargs
    ) -> SendResult:
        sentMessage = await self.mediaHandler.sendVideoMessage(
            message, self.channelChatId, replyParams, hasSpoiler, overrideCaption
        )
        return SendResult(sentMessage.message_id, self.channelChatId, sentMessage, canEdit=True)

    async def _handleAnimation(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters],
        hasSpoiler: bool = False, 
        overrideCaption: Optional[str] = None, 
        **kwargs
    ) -> SendResult:
        sentMessage = await self.mediaHandler.sendAnimationMessage(
            message, self.channelChatId, replyParams, hasSpoiler, overrideCaption
        )
        return SendResult(sentMessage.message_id, self.channelChatId, sentMessage, canEdit=True)

    async def _handleDocument(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters],
        overrideCaption: Optional[str] = None, 
        **kwargs
    ) -> SendResult:
        sentMessage = await self.mediaHandler.sendDocumentMessage(
            message, self.channelChatId, replyParams, overrideCaption
        )
        return SendResult(sentMessage.message_id, self.channelChatId, sentMessage, canEdit=True)

    async def _handlePoll(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters], 
        **kwargs
    ) -> SendResult:
        sentMessage = await self.pollHandler.sendPollMessage(message, self.channelChatId, replyParams)
        return SendResult(sentMessage.message_id, self.channelChatId, sentMessage, canEdit=False)

    async def _handleSticker(
        self, 
        message: Message, 
        replyParams: Optional[ReplyParameters], 
        **kwargs
    ) -> SendResult:
        result = await self.bot.copy_message(
            chat_id=self.channelChatId,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            reply_parameters=replyParams
        )
        return SendResult(result.message_id, self.channelChatId, None, canEdit=False)
    