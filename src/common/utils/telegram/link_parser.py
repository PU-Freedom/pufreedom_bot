import re
from dataclasses import dataclass
from typing import Optional, Union
from aiogram.types import Message

@dataclass
class ParsedLink:
    chatId: Union[int, str]
    messageId: int
    commentId: Optional[int] = None

class TelegramLinkParser:
    PRIVATE_LINK_PATTERN = re.compile(
        r"https?://t\.me/c/(\d+)/(\d+)(?:\?comment=(\d+))?"
    )

    PUBLIC_LINK_PATTERN = re.compile(
        r"https?://t\.me/([a-zA-Z0-9_]+)/(\d+)(?:\?comment=(\d+))?"
    )

    @classmethod
    def parseMessageLink(cls, link: str) -> Optional[ParsedLink]:
        match = cls.PRIVATE_LINK_PATTERN.search(link)
        if match:
            chatId = int(f"-100{match.group(1)}")
            messageId = int(match.group(2))
            commentId = int(match.group(3)) if match.group(3) else None
            return ParsedLink(chatId=chatId, messageId=messageId, commentId=commentId)

        match = cls.PUBLIC_LINK_PATTERN.search(link)
        if match:
            username = match.group(1)
            messageId = int(match.group(2))
            commentId = int(match.group(3)) if match.group(3) else None
            return ParsedLink(chatId=username, messageId=messageId, commentId=commentId)    

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

def getMessageLink(chatId: int, messageId: Optional[int] = None) -> str:
    strId = str(chatId)
    linkId = strId[4:] if strId.startswith("-100") else strId.lstrip("-")
    base = f"https://t.me/c/{linkId}"
    return f"{base}/{messageId}" if messageId else base

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
