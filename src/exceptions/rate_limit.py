from exceptions.base import BotException

class RateLimitError(BotException):
    pass

class RateLimitExceeded(RateLimitError):
    def __init__(self, retryAfter: int, currentMessageCount: int, limit: int):
        self.retryAfter = retryAfter # in sec
        self.currentMessageCount = currentMessageCount
        self.limit = limit
        
        super().__init__(
            f"rate limit exceeded: {currentMessageCount}/{limit} messages",
            f"⚠️ Bruh your sending messages too quickly ⚠️\n\n"
            f"🥀 Boi slow down sending allat bs bruh 😹✌️\n\n"
            f"You done sent {currentMessageCount} messages AND the limit is {limit}.\n"
            f"Wait {retryAfter} seconds before sending again 💦"
        )
        