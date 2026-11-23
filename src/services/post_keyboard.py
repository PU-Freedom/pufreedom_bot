import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from redis.asyncio import Redis
from common import buildAliasKeyboard
from config import settings

logger = logging.getLogger(__name__)

class PostKeyboardService:
    """
    the 💬 Comments button needs the discussion thread id, which arrives in a separate update
    (the auto-forward) that can be handled before or after the post's own handler finishes.
    each side writes its half to redis, then reads the other's - whichever sees both attaches the button
    """
    TTL = 300

    def __init__(self, bot: Bot, redis: Redis):
        self.bot = bot
        self.redis = redis

    @staticmethod
    def build(alias: Optional[str], groupMsgId: Optional[int] = None) -> Optional[InlineKeyboardMarkup]:
        if not alias:
            return None
        return buildAliasKeyboard(alias, settings.DISCUSSION_GROUP_ID, groupMsgId)

    async def onPostSent(self, channelMsgId: int, alias: Optional[str]) -> None:
        if not (alias and settings.DISCUSSION_GROUP_ID):
            return
        await self.redis.setex(f"pending_alias:{channelMsgId}", self.TTL, alias)
        groupMsgId = await self.redis.get(f"post_thread:{channelMsgId}")
        if groupMsgId:
            await self._attach(channelMsgId, alias, int(groupMsgId))

    async def onThreadCreated(self, channelMsgId: int, groupMsgId: int) -> None:
        await self.redis.setex(f"post_thread:{channelMsgId}", self.TTL, groupMsgId)
        alias = await self.redis.get(f"pending_alias:{channelMsgId}")
        if alias:
            await self._attach(channelMsgId, _decode(alias), groupMsgId)

    async def _attach(self, channelMsgId: int, alias: str, groupMsgId: int) -> None:
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=settings.CHANNEL_ID,
                message_id=channelMsgId,
                reply_markup=self.build(alias, groupMsgId),
            )
            logger.info(f"[ALIAS] attached comments button to {channelMsgId} (thread {groupMsgId})")
        except TelegramBadRequest as e:
            # both sides can see both halves - the second edit is a no-op
            if "message is not modified" not in str(e):
                logger.warning(f"[ALIAS] failed to edit channel post {channelMsgId}: {e}")

def _decode(value) -> str:
    return value.decode() if isinstance(value, bytes) else value
