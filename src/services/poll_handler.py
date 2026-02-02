from typing import Optional
from aiogram import Bot
from aiogram.types import Message, ReplyParameters

class PollMessageHandler:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def sendPollMessage(
        self,
        message: Message,
        channel_id: int,
        replyParams: Optional[ReplyParameters] = None,
    ) -> Message:
        poll = message.poll
        return await self.bot.send_poll(
            chat_id=channel_id,
            question=poll.question,
            options=[option.text for option in poll.options],
            is_anonymous=poll.is_anonymous,
            allows_multiple_answers=poll.allows_multiple_answers,
            reply_parameters=replyParams
        )
    