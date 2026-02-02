class BotException(Exception):
    def __init__(self, message: str, userMessage: str | None = None):
        """
        message - internal err message for logging
        userMessage - err message we gonna show to user
        """
        self.message = message
        self.userMessage = userMessage or "Something went wrong. Please try again later"
        super().__init__(self.message)

class ValidationError(BotException):
    pass

class DatabaseError(BotException):
    pass

class ConfigurationError(BotException):
    pass
