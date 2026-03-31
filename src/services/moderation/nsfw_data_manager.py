from typing import Optional, Dict, Any, List
from redis.asyncio import Redis
import logging
import json

logger = logging.getLogger(__name__)

class NSFWDataManager:
    """for nsfw check data storage and retrieval from redis"""
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = 600 # 10mins
    
    async def storeSingleMedia(
        self,
        messageId: int,
        userId: int,
        messageChatId: int,
        replyToMessageId: Optional[int] = None,
        replyToChatId: Optional[int] = None,
        quoteText: Optional[str] = None
    ) -> None:
        key = f"nsfw_pending:{messageId}"
        data = {
            'userId': userId,
            'messageChatId': messageChatId,
            'messageId': messageId,
            'replyToMessageId': replyToMessageId,
            'replyToChatId': replyToChatId,
            'quoteText': quoteText
        }
        if quoteText:
            logger.info(f"[NSFW_STORE] saving quote: {quoteText[:50]}...")

        await self.redis.setex(key, self.ttl, json.dumps(data))
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
        key = f"nsfw_pending_group:{firstMessageId}"
        data = {
            'userId': userId,
            'messageIds': messageIds,
            'chatId': chatId,
            'replyToMessageId': replyToMessageId,
            'replyToChatId': replyToChatId,
            'quoteText': quoteText
        }
        if quoteText:
            logger.info(f"[NSFW_STORE :: MEDIA GROUP] saving quote for group: {quoteText[:50]}...")
        
        await self.redis.setex(key, self.ttl, json.dumps(data))
        logger.info(f"[NSFW_STORE :: MEDIA GROUP] stored data for group {firstMessageId}")
    
    async def retrieveSingleMedia(self, messageId: int) -> Optional[Dict[str, Any]]:
        key = f"nsfw_pending:{messageId}"
        data = await self.redis.get(key)
        if data: return json.loads(data)
        return None
    
    async def retrieveMediaGroup(self, messageId: int) -> Optional[Dict[str, Any]]:
        key = f"nsfw_pending_group:{messageId}"
        data = await self.redis.get(key)
        if data: return json.loads(data)
        return None
    
    async def deleteSingleMedia(self, messageId: int) -> None:
        key = f"nsfw_pending:{messageId}"
        await self.redis.delete(key)
    
    async def deleteMediaGroup(self, messageId: int) -> None:
        key = f"nsfw_pending_group:{messageId}"
        await self.redis.delete(key)
    
    async def cancel(self, messageId: int) -> None:
        await self.deleteSingleMedia(messageId)
        await self.deleteMediaGroup(messageId)
        logger.info(f"[NSFW_STORE] cancelled NSFW check for message {messageId}")
