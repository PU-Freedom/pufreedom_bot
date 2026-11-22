from typing import Optional, Dict, Any, List
from redis.asyncio import Redis
import logging
import json

logger = logging.getLogger(__name__)

class NSFWDataManager:
    """keys are scoped by chat id - bot api message ids are only unique within a chat"""
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = 600 # 10mins

    @staticmethod
    def _singleKey(chatId: int, messageId: int) -> str:
        return f"nsfw_pending:{chatId}:{messageId}"

    @staticmethod
    def _groupKey(chatId: int, firstMessageId: int) -> str:
        return f"nsfw_pending_group:{chatId}:{firstMessageId}"

    async def storeSingleMedia(
        self,
        messageId: int,
        userId: int,
        messageChatId: int,
        replyToMessageId: Optional[int] = None,
        replyToChatId: Optional[int] = None,
        quoteText: Optional[str] = None,
        stripReplyLink: bool = False,
    ) -> None:
        data = {
            'userId': userId,
            'messageChatId': messageChatId,
            'messageId': messageId,
            'replyToMessageId': replyToMessageId,
            'replyToChatId': replyToChatId,
            'quoteText': quoteText,
            'stripReplyLink': stripReplyLink,
        }
        await self.redis.setex(self._singleKey(messageChatId, messageId), self.ttl, json.dumps(data))
        logger.info(f"[NSFW_STORE] stored single media data for message {messageId}")

    async def storeMediaGroup(
        self,
        firstMessageId: int,
        userId: int,
        messageIds: List[int],
        chatId: int,
        replyToMessageId: Optional[int] = None,
        replyToChatId: Optional[int] = None,
        quoteText: Optional[str] = None
    ) -> None:
        data = {
            'userId': userId,
            'messageIds': messageIds,
            'chatId': chatId,
            'replyToMessageId': replyToMessageId,
            'replyToChatId': replyToChatId,
            'quoteText': quoteText
        }
        await self.redis.setex(self._groupKey(chatId, firstMessageId), self.ttl, json.dumps(data))
        logger.info(f"[NSFW_STORE :: MEDIA GROUP] stored data for group {firstMessageId}")

    async def _pop(self, key: str) -> Optional[Dict[str, Any]]:
        """atomic get+delete so a double tap can't post twice"""
        async with self.redis.pipeline(transaction=True) as pipe:
            value, _ = await pipe.get(key).delete(key).execute()
        return json.loads(value) if value else None

    async def claimSingleMedia(self, chatId: int, messageId: int) -> Optional[Dict[str, Any]]:
        return await self._pop(self._singleKey(chatId, messageId))

    async def claimMediaGroup(self, chatId: int, messageId: int) -> Optional[Dict[str, Any]]:
        return await self._pop(self._groupKey(chatId, messageId))

    async def restoreSingleMedia(self, chatId: int, messageId: int, data: Dict[str, Any]) -> None:
        await self.redis.setex(self._singleKey(chatId, messageId), self.ttl, json.dumps(data))

    async def restoreMediaGroup(self, chatId: int, messageId: int, data: Dict[str, Any]) -> None:
        await self.redis.setex(self._groupKey(chatId, messageId), self.ttl, json.dumps(data))

    async def cancel(self, chatId: int, messageId: int) -> None:
        await self.redis.delete(self._singleKey(chatId, messageId), self._groupKey(chatId, messageId))
        logger.info(f"[NSFW_STORE] cancelled NSFW check for message {messageId}")
