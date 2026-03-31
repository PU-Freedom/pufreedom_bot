from exceptions.base import BotException
from common import settings

class NotSubscribedError(BotException):
    def __init__(self, status: str = "left", channelChatId: str=settings.CHANNEL_USERNAME):
        messages = {
            "left": (
                "You need to subscribe to the channel to use this bot 📢\n\n"
                f'<b><a href="t.me/{channelChatId}">Join the channel first</a>, then try again.</b>'
            ),
            "kicked": (
                "You are banned from the channel and cannot use this bot 🚫"
            ),
        }
        userMessage = messages.get(status, messages["left"])
        super().__init__(
            message=f"user not subscribed to channel (status={status})",
            userMessage=userMessage
        )
        self.status = status
