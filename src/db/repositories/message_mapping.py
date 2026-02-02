import logging
from typing import Optional
from sqlalchemy import (
    or_,
    and_,
    update,
    select, 
)
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.message_mapping import MessageMapping
from db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

class MessageMappingRepository(BaseRepository[MessageMapping]):
    def __init__(self, session: AsyncSession):
        super().__init__(MessageMapping, session)
    
    async def getByUserMessage(
        self,
        userChatId: int,
        userMessageId: int
    ) -> Optional[MessageMapping]:
        result = await self.session.execute(
            select(MessageMapping).where(
                and_(
                    MessageMapping.userChatId == userChatId,
                    MessageMapping.userMessageId == userMessageId,
                    MessageMapping.isDeleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def getByChannelMessage(
        self,
        channelChatId: int,
        channelMessageId: int
    ) -> Optional[MessageMapping]:
        result = await self.session.execute(
            select(MessageMapping)
            .options(selectinload(MessageMapping.user))
            .where(
                and_(
                    MessageMapping.channelChatId == channelChatId,
                    MessageMapping.channelMessageId == channelMessageId,
                    MessageMapping.isDeleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def getByUserMessageOrLastEditMessage(
        self,
        userChatId: int,
        userMessageId: int
    ) -> Optional[MessageMapping]:
        result = await self.session.execute(
            select(MessageMapping).where(
                and_(
                    MessageMapping.userChatId == userChatId,
                    MessageMapping.isDeleted == False,
                    or_(
                        MessageMapping.userMessageId == userMessageId,
                        MessageMapping.userLastEditMessageId == userMessageId
                    )
                )
            )
        )
        mapping = result.scalar_one_or_none()
        logger.info(f"[GET_MAPPING] found: {mapping is not None}")
        if mapping:
            logger.info(
                f"[GET_MAPPING] details: userMessageId={mapping.userMessageId}, "
                f"channelMessageId={mapping.channelMessageId}, "
                f"lastEditId={mapping.userLastEditMessageId}"
            )
        return mapping
    
    async def createMapping(
        self,
        userId: int,
        userChatId: int,
        userMessageId: int,
        channelChatId: int,
        channelMessageId: int
    ) -> MessageMapping:
        mapping = await self.create(
            userId=userId,
            userChatId=userChatId,
            userMessageId=userMessageId,
            channelChatId=channelChatId,
            channelMessageId=channelMessageId
        )
        await self.session.flush()
        await self.session.commit()  
        return mapping
    
    async def markAsDeleted(
        self,
        channelChatId: int,
        channelMessageId: int
    ) -> bool:
        result = await self.session.execute(
            select(MessageMapping).where(
                and_(
                    MessageMapping.channelChatId == channelChatId,
                    MessageMapping.channelMessageId == channelMessageId
                )
            )
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            return False
        mapping.isDeleted = True
        await self.session.flush()
        return True
    
    async def updateLastEditMessageId(
        self,
        userMessageId: int,
        userChatId: int,
        lastEditMessageId: int
    ) -> None:
        await self.session.execute(
            update(MessageMapping)
            .where(
                MessageMapping.userMessageId == userMessageId,
                MessageMapping.userChatId == userChatId
            )
            .values(userLastEditMessageId=lastEditMessageId)
        )
        await self.session.commit()
