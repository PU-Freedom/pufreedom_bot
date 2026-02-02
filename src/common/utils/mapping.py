from typing import Optional
import logging
from db import MessageMappingRepository, MessageMapping

logger = logging.getLogger(__name__)

class MappingUtil:
    @staticmethod
    async def createAndLog(
        repo: MessageMappingRepository,
        userId: int,
        userChatId: int,
        userMessageId: int,
        channelChatId: int,
        channelMessageId: int
    ) -> MessageMapping:
        mapping = await repo.createMapping(
            userId=userId,
            userChatId=userChatId,
            userMessageId=userMessageId,
            channelChatId=channelChatId,
            channelMessageId=channelMessageId
        )
        logger.info(
            f"[MAPPING_CREATE] created mapping: "
            f"userChatId={userChatId}, userMessage={userMessageId} -> "
            f"channelChatId={channelChatId}, channelMessageId={channelMessageId}"
        )
        return mapping
    
    @staticmethod
    async def findReplyMapping(
        repo: MessageMappingRepository,
        userChatId: int,
        userMessageId: int,
        context: str = "MAPPING"
    ) -> Optional[MessageMapping]:
        mapping = await repo.getByUserMessage(
            userChatId=userChatId,
            userMessageId=userMessageId
        )
        if mapping:
            logger.info(
                f"[{context}] == OK == found mapping: "
                f"userMessage={userMessageId} -> "
                f"channelMessage={mapping.channelMessageId}, "
                f"channelChat={mapping.channelChatId}"
            )
        else:
            logger.warning(
                f"[{context}] == X == NO mapping found for "
                f"userMessage={userMessageId} in chat={userChatId}"
            )
        return mapping
    