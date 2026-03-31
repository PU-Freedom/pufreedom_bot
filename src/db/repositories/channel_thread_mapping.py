from typing import Optional
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.channel_thread_mapping import ChannelThreadMapping
from db.repositories.base import BaseRepository


class ChannelThreadMappingRepository(BaseRepository[ChannelThreadMapping]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChannelThreadMapping, session)

    async def getByChannelPostId(self, channelPostId: int) -> Optional[ChannelThreadMapping]:
        result = await self.session.execute(
            select(ChannelThreadMapping).where(
                ChannelThreadMapping.channelPostId == channelPostId
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, channelPostId: int, groupThreadId: int) -> None:
        stmt = (
            insert(ChannelThreadMapping)
            .values(channelPostId=channelPostId, groupThreadId=groupThreadId)
            .on_conflict_do_update(
                constraint="uq_channel_thread_channelPostId",
                set_={"groupThreadId": groupThreadId}
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
