from typing import Optional
from aiogram.types import ReplyParameters
import logging

logger = logging.getLogger(__name__)

class ReplyParametersBuilder:
    @staticmethod
    def build(
        messageId: int,
        chatId: int,
        quoteText: Optional[str] = None,
        source: str = "unknown"
    ) -> ReplyParameters:
        if quoteText:
            logger.info(f"[{source}] including quote: {quoteText[:50]}...")
            return ReplyParameters(
                message_id=messageId,
                chat_id=chatId,
                quote=quoteText,
            )
        else:
            return ReplyParameters(
                message_id=messageId,
                chat_id=chatId
            )
    
    @staticmethod
    def buildFromMapping(
        mapping,
        quoteText: Optional[str] = None,
        source: str = "MAPPING"
    ) -> ReplyParameters:
        return ReplyParametersBuilder.build(
            messageId=mapping.channelMessageId,
            chatId=mapping.channelChatId,
            quoteText=quoteText,
            source=source
        )
    