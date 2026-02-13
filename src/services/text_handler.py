from aiogram.types import Message, ReplyParameters
from typing import Optional
from aiogram import Bot
from config import settings

class TextMessageHandler:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def sendTextMessage(
        self,
        message: Message,
        channelChatId: int = settings.CHANNEL_ID,
        replyParams: Optional[ReplyParameters] = None,
        overrideText: Optional[str] = None
    ) -> Message:
        if overrideText is not None:
            return await self.bot.send_message(
                chat_id=channelChatId,
                text=overrideText,
                parse_mode="HTML",
                reply_parameters=replyParams
            )
        else:
            return await self.bot.copy_message(
                chat_id=channelChatId,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_parameters=replyParams
            )
