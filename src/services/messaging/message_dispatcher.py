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
        logger.debug(
            f"[DISPATCHER] Sending {contentType.name} "
            f"via {config.sendMethod}"
        )
        try:
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
                f"[DISPATCHER] 🔧 Params for {contentType.name}: "
                f"{list(params.keys())}"
            )
            
            # get tg api method dynamically and call it
            # sendMethod = getattr(self.bot, config.sendMethod)
            result = await sendMethod(**params)
            
            logger.info(
                f"[DISPATCHER] successfully sent {contentType.name} "
                f"(method: {config.sendMethod})"
            )
            
            # NOTE: copy_message returns MessageId obj
            # others return Message (sentMessage)
            messageId = (
                result.message_id 
                if hasattr(result, 'message_id') 
                else result
            )
            sentMessage = (
                result 
                if hasattr(result, 'message_id') 
                else None
            )
            return SendResult(
                messageId=messageId,
                chatId=self.channelChatId,
                sentMessage=sentMessage,
                canEdit=config.canEdit
            )
            
        except TelegramAPIError as e:
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
            # param errors (wrong param type, missing required param, etc.)
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
        