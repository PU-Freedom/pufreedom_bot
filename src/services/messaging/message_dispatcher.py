from typing import Optional
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from aiogram.exceptions import TelegramAPIError
from common import SendResult, MESSAGE_TYPE_CONFIGS, isSupportedType
from exceptions import ChannelPostError
import logging

logger = logging.getLogger(__name__)

class MessageDispatcher:
    def __init__(self, bot: Bot, channelChatId: int):
        self.bot = bot
        self.channelChatId = channelChatId
        logger.info(f"[DISPATCHER] initted for channel {channelChatId}")
    
    async def send(
        self,
        message: Message,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None,
        threadId: Optional[int] = None,
        replyMarkup=None,
    ) -> SendResult:
        """
        send message to the channel based on its content type
        process:
        - look up message type config
        - build params using param builder for given content type
        - calls appropriate tg api method
        - return SendResult dto with message details
        """
        contentType = message.content_type
        if not isSupportedType(contentType):
            logger.error(f"[DISPATCHER] == X == unsupported content type: {contentType}")
            raise ChannelPostError(f"Unsupported message type: {contentType}")
        
        config = MESSAGE_TYPE_CONFIGS[contentType]
        if not hasSpoiler and not overrideCaption and not replyMarkup and not message.forward_origin:
            try:
                copyParams = {
                    "chat_id": self.channelChatId,
                    "from_chat_id": message.chat.id,
                    "message_id": message.message_id,
                }
                if replyParams:
                    copyParams["reply_parameters"] = replyParams
                if threadId:
                    copyParams["message_thread_id"] = threadId
                result = await self.bot.copy_message(**copyParams)
                logger.info(f"[DISPATCHER] successfully sent {contentType.name} (method: copy_message)")
                return SendResult(
                    messageId=result.message_id,
                    chatId=self.channelChatId,
                    sentMessage=None,
                    canEdit=config.canEdit,
                )
            except TelegramAPIError as e:
                logger.warning(
                    f"[DISPATCHER] copy_message failed for {contentType.name} ({e}), "
                    f"falling back to {config.sendMethod}"
                )

        logger.debug(f"[DISPATCHER] Sending {contentType.name} via {config.sendMethod}")
        params = config.paramBuilder(
            message,
            self.channelChatId,
            replyParams,
            hasSpoiler=hasSpoiler,
            overrideCaption=overrideCaption
        )
        if threadId:
            params["message_thread_id"] = threadId

        if replyMarkup and "from_chat_id" not in params:
            params["reply_markup"] = replyMarkup
        if "text" in params and "from_chat_id" not in params:
            logger.info(f"[DISPATCHER] text override detected - using send_message")
            sendMethod = self.bot.send_message
        else:
            sendMethod = getattr(self.bot, config.sendMethod)
        logger.debug(
            f"[DISPATCHER] Params for {contentType.name}: "
            f"{list(params.keys())}"
        )
        return await self._callSendMethod(sendMethod, params, replyParams, contentType, config)

    async def _callSendMethod(self, sendMethod, params, replyParams, contentType, config) -> SendResult:
        """extracted err handling logic to make it less nested and ugly"""
        try:
            result = await sendMethod(**params)
            logger.info(
                f"[DISPATCHER] successfully sent {contentType.name} "
                f"(method: {config.sendMethod})"
            )
            return self._buildSendResult(result, config)

        except TelegramAPIError as e:
            if replyParams and "reply_parameters" in params:
                logger.warning(
                    f"[DISPATCHER] {config.sendMethod} failed with reply params ({e}), "
                    f"retrying without reply params"
                )
                params.pop("reply_parameters")
                try:
                    result = await sendMethod(**params)
                    logger.info(
                        f"[DISPATCHER] successfully sent {contentType.name} "
                        f"without reply params (method: {config.sendMethod})"
                    )
                    return self._buildSendResult(result, config)
                except TelegramAPIError as retryErr:
                    logger.error(
                        f"[DISPATCHER] == X == retry without reply params also failed for "
                        f"{contentType.name}: {retryErr}",
                        exc_info=True
                    )
                    raise ChannelPostError(
                        f"Telegram API error sending {contentType.name}: {retryErr}"
                    ) from retryErr
            logger.error(
                f"[DISPATCHER] == X == Telegram API error sending {contentType.name} "
                f"via {config.sendMethod}: {e}",
                exc_info=True
            )
            raise ChannelPostError(
                f"Telegram API error sending {contentType.name}: {e}"
            ) from e
        except AttributeError as e:
            logger.error(
                f"[DISPATCHER] == X == Configuration error for {contentType.name}: {e} "
                f"(method: {config.sendMethod})",
                exc_info=True
            )
            raise ChannelPostError(
                f"Invalid configuration for {contentType.name}: {e}"
            ) from e
        except TypeError as e:
            logger.error(
                f"[DISPATCHER] == X == parameter error for {contentType.name}: {e} "
                f"(method: {config.sendMethod}, params: {list(params.keys())})",
                exc_info=True
            )
            raise ChannelPostError(
                f"Parameter error sending {contentType.name}: {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"[DISPATCHER] == X == unexpected error sending {contentType.name}: {e}",
                exc_info=True
            )
            raise ChannelPostError(
                f"Unexpected error sending {contentType.name}: {e}"
            ) from e

    def _buildSendResult(self, result, config) -> SendResult:
        # NOTE: copy_message returns MessageId obj, others return Message
        messageId = result.message_id if hasattr(result, 'message_id') else result
        sentMessage = result if hasattr(result, 'message_id') else None
        return SendResult(
            messageId=messageId,
            chatId=self.channelChatId,
            sentMessage=sentMessage,
            canEdit=config.canEdit
        )
