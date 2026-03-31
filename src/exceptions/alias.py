from exceptions.base import BotException


class AliasError(BotException):
    pass


class AliasValidationError(AliasError):
    def __init__(self, reason: str):
        super().__init__(
            message=f"alias validation failed: {reason}",
            userMessage=reason
        )


class AliasTakenError(AliasError):
    def __init__(self, alias: str):
        super().__init__(
            message=f"alias already taken: {alias}",
            userMessage=f"The alias <code>{alias}</code> is already taken. Please choose another."
        )
