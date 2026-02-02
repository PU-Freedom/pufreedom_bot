import redis.asyncio as redis
from typing import Optional
from config.settings import settings

class RedisManager:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    async def init(self):
        self._client = await redis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        if self._client:
            await self._client.close()
    
    @property
    def client(self) -> redis.Redis:
        if not self._client:
            raise RuntimeError("redis not initted")
        return self._client

redisManager = RedisManager()
