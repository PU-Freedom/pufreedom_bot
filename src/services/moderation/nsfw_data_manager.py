from dataclasses import dataclass
from typing import Optional, List
from aiogram.types import Message
from redis.asyncio import Redis
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class PendingMedia:
    userId: int
    messages: List[Message]  # one message, or every item of an album

class NSFWDataManager:
    """keys are scoped by chat id - bot api message ids are only unique within a chat"""
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = 600 # 10mins

    @staticmethod
    def _key(chatId: int, messageId: int) -> str:
        return f"nsfw_pending:{chatId}:{messageId}"

    async def store(self, chatId: int, messageId: int, userId: int, messages: List[Message]) -> None:
        data = {
            "userId": userId,
            "messages": [m.model_dump(mode="json", exclude_none=True) for m in messages],
        }
        await self.redis.setex(self._key(chatId, messageId), self.ttl, json.dumps(data))
        logger.info(f"[NSFW_STORE] stored {len(messages)} message(s) for prompt {messageId}")

    async def claim(self, chatId: int, messageId: int) -> Optional[PendingMedia]:
        """atomic get+delete so a double tap can't post twice"""
        key = self._key(chatId, messageId)
        async with self.redis.pipeline(transaction=True) as pipe:
            value, _ = await pipe.get(key).delete(key).execute()
        if not value:
            return None
        data = json.loads(value)
        return PendingMedia(
            userId=data["userId"],
            messages=[Message.model_validate(m) for m in data["messages"]],
        )

    async def restore(self, chatId: int, messageId: int, pending: PendingMedia) -> None:
        await self.store(chatId, messageId, pending.userId, pending.messages)

    async def cancel(self, chatId: int, messageId: int) -> None:
        await self.redis.delete(self._key(chatId, messageId))
        logger.info(f"[NSFW_STORE] cancelled NSFW check for message {messageId}")
