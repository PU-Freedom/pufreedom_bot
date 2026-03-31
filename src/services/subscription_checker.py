from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from common import SUBSCRIBED_STATUSES
import logging

logger = logging.getLogger(__name__)

class SubscriptionCheckerService:
    def __init__(self, bot: Bot, channelId: int):
        self.bot = bot
        self.channelId = channelId

    async def getStatus(self, telegramId: int) -> str:
        """
        Returns the subscription status:
        'subscribed' - active member/admin/owner/restricted
        'left'       - left or never joined
        'kicked'     - banned from the channel
        'unknown'    - check failed (bot likely missing admin rights); callers should fail open
        """
        try:
            member = await self.bot.get_chat_member(
                chat_id=self.channelId,
                user_id=telegramId
            )
            if member.status in SUBSCRIBED_STATUSES:
                return "subscribed"
            if member.status == ChatMemberStatus.KICKED:
                return "kicked"
            return "left"
        except TelegramBadRequest as e:
            logger.warning(f"[SUB_CHECK] bad request for user {telegramId}: {e}")
            return "left"
        except TelegramForbiddenError as e:
            logger.error(
                f"[SUB_CHECK] bot cannot check membership "
                f"(missing admin rights on channel?): {e}"
            )
            return "unknown"
        except Exception as e:
            logger.error(f"[SUB_CHECK] unexpected error for user {telegramId}: {e}", exc_info=True)
            return "unknown"

    async def isSubscribed(self, telegramId: int) -> tuple[bool, str]:
        """
        returns: (is_subscribed, status). 
        !NOTE: 'unknown' status is treated as subscribed (fail open)
        """
        status = await self.getStatus(telegramId)
        return status in ("subscribed", "unknown"), status
