from typing import Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.user import User
from db.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
    
    async def getByTelegramId(self, telegramId: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegramId == telegramId)
        )
        return result.scalar_one_or_none()
    
    async def getOrCreate(
        self,
        telegramId: int,
        username: Optional[str] = None,
        firstName: str = "",
        lastName: Optional[str] = None
    ) -> User:
        user = await self.getByTelegramId(telegramId)
        if user:
            user.lastActiveAt = datetime.now()
            if username != user.username:
                user.username = username
            if firstName != user.firstName:
                user.firstName = firstName
            if lastName != user.lastName:
                user.lastName = lastName
            await self.session.flush()
            return user
        
        return await self.create(
            telegramId=telegramId,
            username=username,
            firstName=firstName,
            lastName=lastName
        )
    
    async def banUserByTelegramId(self, telegramId: int) -> bool:
        result = await self.session.execute(
            select(User).where(User.telegramId == telegramId)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.isBanned = True
        await self.session.flush()
        return True
    
    async def unbanUserByTelegramId(self, telegramId: int) -> bool:
        result = await self.session.execute(
            select(User).where(User.telegramId == telegramId)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.isBanned = False
        await self.session.flush()
        return True
    