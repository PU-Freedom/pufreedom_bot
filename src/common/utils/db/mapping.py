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
