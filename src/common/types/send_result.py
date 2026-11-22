from typing import NamedTuple

class SendResult(NamedTuple):
    messageId: int
    chatId: int
    canEdit: bool
