from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.comment_mapping import CommentMapping
from db.repositories.base import BaseRepository


class CommentMappingRepository(BaseRepository[CommentMapping]):
    def __init__(self, session: AsyncSession):
        super().__init__(CommentMapping, session)

    async def getByGroupMessageId(self, groupChatId: int, groupMessageId: int) -> Optional[CommentMapping]:
        result = await self.session.execute(
            select(CommentMapping).where(
                CommentMapping.groupChatId == groupChatId,
                CommentMapping.groupMessageId == groupMessageId,
                CommentMapping.isDeleted == False
            )
        )
        return result.scalar_one_or_none()

    async def getByUserMessage(self, userChatId: int, userMessageId: int) -> Optional[CommentMapping]:
        result = await self.session.execute(
            select(CommentMapping).where(
                CommentMapping.userChatId == userChatId,
                CommentMapping.userMessageId == userMessageId
            )
        )
        return result.scalar_one_or_none()
