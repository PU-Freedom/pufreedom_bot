from exceptions.base import BotException

class ChannelError(BotException):
    pass

class ChannelAccessError(ChannelError):
    def __init__(self):
        super().__init__(
            "bot does not have access to the channel",
            "Bot is not configured correctly. Please contact the administrator"
        )

class ChannelPostError(ChannelError):
    def __init__(self, reason: str = "unknown"):
        super().__init__(
            f"failed to post to channel: {reason}",
            "Failed to post to the channel. Please try again later"
        )

class ChannelPermissionError(ChannelError):
    def __init__(self, permission: str):
        super().__init__(
            f"bot lacks permission: {permission}",
            "Bot does not have required permissions in the channel. Please contact the administrator"
        )
