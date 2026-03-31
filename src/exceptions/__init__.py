from exceptions.base import (
    BotException,
    ValidationError,
    DatabaseError,
    ConfigurationError,
)
from exceptions.message import (
    MessageError,
    MessageForwardError,
    MessageEditError,
    MessageDeleteError,
    MessageNotFoundError,
    InvalidReplyError,
)
from exceptions.rate_limit import (
    RateLimitError,
    RateLimitExceeded,
)
from exceptions.channel import (
    ChannelError,
    ChannelAccessError,
    ChannelPostError,
    ChannelPermissionError,
)
from exceptions.subscription import (
    NotSubscribedError,
)
from exceptions.alias import (
    AliasError,
    AliasValidationError,
    AliasTakenError,
)

__all__ = [
    # base
    "BotException",
    "ValidationError",
    "DatabaseError",
    "ConfigurationError",
    # message
    "MessageError",
    "MessageForwardError",
    "MessageEditError",
    "MessageDeleteError",
    "MessageNotFoundError",
    "InvalidReplyError",
    # rate limit
    "RateLimitError",
    "RateLimitExceeded",
    # channel
    "ChannelError",
    "ChannelAccessError",
    "ChannelPostError",
    "ChannelPermissionError",
    # subscription
    "NotSubscribedError",
    # alias
    "AliasError",
    "AliasValidationError",
    "AliasTakenError",
]
