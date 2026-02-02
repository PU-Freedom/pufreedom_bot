from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from config.settings import settings

class DatabaseManager:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._sessionMaker: async_sessionmaker | None = None
    
    def init(self):
        self._engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            poolclass=NullPool,
            pool_pre_ping=True,
        )
        
        self._sessionMaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def close(self):
        if self._engine:
            await self._engine.dispose()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._sessionMaker:
            raise RuntimeError("database not initted")
        
        async with self._sessionMaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @property
    def engine(self) -> AsyncEngine:
        if not self._engine:
            raise RuntimeError("database not initted")
        return self._engine

dbManager = DatabaseManager()
async def getSession() -> AsyncGenerator[AsyncSession, None]:
    async with dbManager.session() as session:
        yield session
        