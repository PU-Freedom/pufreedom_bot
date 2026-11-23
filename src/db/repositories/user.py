from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
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
        # atomic - concurrent first messages (album items) from a new user would otherwise race on the unique insert
        profile = {"username": username, "firstName": firstName, "lastName": lastName}
        stmt = (
            insert(User)
            .values(telegramId=telegramId, **profile)
            .on_conflict_do_update(
                index_elements=[User.telegramId],
                set_={**profile, "lastActiveAt": func.now(), "updatedAt": func.now()},
            )
            .returning(User)
        )
        result = await self.session.execute(
            select(User).from_statement(stmt).execution_options(populate_existing=True)
        )
        return result.scalar_one()
    
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

    async def getByAlias(self, alias: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(func.lower(User.alias) == alias.lower())
        )
        return result.scalar_one_or_none()

    async def setAlias(self, userId: int, alias: str) -> bool:
        """
        Sets alias for a user. Alias is stored lowercase.
        Returns False if alias is already taken by another user.
        """
        existing = await self.getByAlias(alias)
        if existing and existing.id != userId:
            return False
        result = await self.session.execute(
            select(User).where(User.id == userId)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.alias = alias
        await self.session.flush()
        return True

    async def clearAlias(self, userId: int) -> None:
        result = await self.session.execute(
            select(User).where(User.id == userId)
        )
        user = result.scalar_one_or_none()
        if user and user.alias:
            user.alias = None
            await self.session.flush()
    