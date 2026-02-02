import re
from typing import Optional, Tuple
from aiogram.types import Message

class TelegramLinkParser:
    PRIVATE_LINK_PATTERN = re.compile(
        r"https?://t\.me/c/(\d+)/(\d+)"
    )
    
    PUBLIC_LINK_PATTERN = re.compile(
        r"https?://t\.me/([a-zA-Z0-9_]+)/(\d+)"
    )
    
    @classmethod
    def parseMessageLink(cls, link: str) -> Optional[Tuple[int, int]]:
        match = cls.PRIVATE_LINK_PATTERN.search(link)
        if match:
            chatId = int(match.group(1))
            messageId = int(match.group(2))
            chatId = -1000000000000 - chatId
            return (chatId, messageId)
        
        match = cls.PUBLIC_LINK_PATTERN.search(link)
        if match:
            username = match.group(1)
            messageId = int(match.group(2))
            return (username, messageId)
        return None
    
    @classmethod
    def extractLinkFromText(cls, text: str) -> Optional[str]:
        match = cls.PRIVATE_LINK_PATTERN.search(text)
        if match:
            return match.group(0)
        
        match = cls.PUBLIC_LINK_PATTERN.search(text)
        if match:
            return match.group(0)
        return None

def getMessageLink(chatId: int, messageId: int) -> str:
    if str(chatId).startswith("-100"): # supergroup/channel
        linkId = str(chatId)[4:]
        return f"https://t.me/c/{linkId}/{messageId}"
    else:
        return f"https://t.me/c/{abs(chatId)}/{messageId}"


def formatUserMention(message: Message) -> str:
    user = message.from_user
    if not user:
        return "unknown user"
    if user.username:
        return f"@{user.username}"
    
    name = user.firstName
    if user.lastName:
        name += f" {user.lastName}"
    return name
