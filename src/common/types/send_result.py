from typing import Optional, NamedTuple
from aiogram.types import Message

class SendResult(NamedTuple):
    messageId: int
    chatId: int
    sentMessage: Optional[Message]
    canEdit: bool
