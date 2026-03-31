import time
from redis.asyncio import Redis
from config import settings
from exceptions import RateLimitExceeded

class RateLimiterService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.limit = settings.RATE_LIMIT_MESSAGES
        self.window = settings.RATE_LIMIT_WINDOW_SECONDS
    
    def _getKey(self, userId: int) -> str:
        return f"ratelimit:{userId}:messages"
    
    async def checkRateLimit(self, userId: int) -> None:
        key = self._getKey(userId)
        currentTime = int(time.time())
        windowStart = currentTime - self.window
        
        await self.redis.zremrangebyscore(key, 0, windowStart)
        count = await self.redis.zcard(key)
        
        if count >= self.limit:
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldestTime = int(oldest[0][1])
                retryAfter = oldestTime + self.window - currentTime
                raise RateLimitExceeded(
                    retryAfter=max(1, retryAfter),
                    currentMessageCount=count,
                    limit=self.limit
                )
    
    async def recordMessage(self, userId: int) -> None:
        key = self._getKey(userId)
        currentTime = time.time()
        await self.redis.zadd(key, {str(currentTime): currentTime})
        await self.redis.expire(key, self.window + 60)
    
    async def getMessageCount(self, userId: int) -> int:
        key = self._getKey(userId)
        currentTime = int(time.time())
        windowStart = currentTime - self.window
        await self.redis.zremrangebyscore(key, 0, windowStart)
        return await self.redis.zcard(key)
    
    async def resetUserLimit(self, userId: int) -> None:
        key = self._getKey(userId)
        await self.redis.delete(key)
        