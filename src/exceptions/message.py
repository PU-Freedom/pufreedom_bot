from exceptions.base import BotException

class MessageError(BotException):
    pass

class MessageForwardError(MessageError):
    def __init__(self, reason: str = "unknown"):
        super().__init__(
            f"failed to forward message: {reason}",
            "Failed to send your message to the channel. Please try again"
        )


class MessageEditError(MessageError):
    def __init__(self, reason: str = "unknown"):
        super().__init__(
            f"failed to edit message: {reason}",
            "Failed to edit your message. Please try again."
        )


class MessageDeleteError(MessageError):
    def __init__(self, reason: str = "unknown"):
        super().__init__(
            f"failed to delete message: {reason}",
            "Failed to delete your message. It may have already been deleted"
        )


class MessageNotFoundError(MessageError):
    def __init__(self):
        super().__init__(
            "message mapping not found in database",
            "Could not find the original message. It may have been deleted."
        )

class InvalidReplyError(MessageError):
    def __init__(self, reason: str = "invalid reply target"):
        super().__init__(
            f"invalid reply: {reason}",
            "Failed to process reply. Please check the message link and try again."
        )
        