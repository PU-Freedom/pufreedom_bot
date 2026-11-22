import time
import uuid
from typing import Optional
from redis.asyncio import Redis
from config import settings
from exceptions import RateLimitExceeded

# KEYS: window zset, (optional) media group decision key
# ARGV: now, window, limit, unique member, group decision ttl
# returns {retryAfter (0 = allowed), isRepeatedGroupDecision, count}
_ACQUIRE_LUA = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
if #KEYS > 1 then
  local prev = redis.call('GET', KEYS[2])
  if prev then return {tonumber(prev), 1, 0} end
end
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local count = redis.call('ZCARD', KEYS[1])
local retry = 0
if count >= limit then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  retry = math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
else
  redis.call('ZADD', KEYS[1], now, ARGV[4])
  redis.call('EXPIRE', KEYS[1], window + 60)
  count = count + 1
end
if #KEYS > 1 then
  redis.call('SET', KEYS[2], retry, 'EX', tonumber(ARGV[5]))
end
return {retry, 0, count}
"""

class RateLimiterService:
    SCOPE_POST = "messages"
    SCOPE_ANON = "anon"
    GROUP_DECISION_TTL = 60

    def __init__(self, redis: Redis):
        self.redis = redis
        self._acquireScript = redis.register_script(_ACQUIRE_LUA)
        self.limits = {
            self.SCOPE_POST: (settings.RATE_LIMIT_MESSAGES, settings.RATE_LIMIT_WINDOW_SECONDS),
            self.SCOPE_ANON: (settings.ANON_RATE_LIMIT_MESSAGES, settings.ANON_RATE_LIMIT_WINDOW_SECONDS),
        }

    def _getKey(self, userId: int, scope: str = SCOPE_POST) -> str:
        return f"ratelimit:{userId}:{scope}"

    async def acquire(self, userId: int, scope: str = SCOPE_POST, groupId: Optional[str] = None) -> bool:
        """
        True -> proceed; False -> drop silently (later item of an already rejected album);
        raises RateLimitExceeded. all items sharing a groupId use one slot/decision
        """
        limit, window = self.limits[scope]
        keys = [self._getKey(userId, scope)]
        if groupId:
            keys.append(f"ratelimit_group:{userId}:{groupId}")
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        retryAfter, isRepeat, count = await self._acquireScript(
            keys=keys,
            args=[now, window, limit, member, self.GROUP_DECISION_TTL],
        )
        if int(retryAfter) <= 0:
            return True
        if int(isRepeat):
            return False
        raise RateLimitExceeded(retryAfter=int(retryAfter), currentMessageCount=int(count), limit=limit)

    async def getMessageCount(self, userId: int, scope: str = SCOPE_POST) -> int:
        _, window = self.limits[scope]
        key = self._getKey(userId, scope)
        await self.redis.zremrangebyscore(key, "-inf", time.time() - window)
        return await self.redis.zcard(key)

    async def resetUserLimit(self, userId: int, scope: str = SCOPE_POST) -> None:
        await self.redis.delete(self._getKey(userId, scope))
