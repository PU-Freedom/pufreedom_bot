import re
import logging
from dataclasses import dataclass
from typing import Optional, Union, List, Tuple
from aiogram import Bot
from aiogram.types import MessageEntity
from config import settings

logger = logging.getLogger(__name__)

@dataclass
class ParsedLink:
    chatId: Union[int, str]
    messageId: int
    commentId: Optional[int] = None
    threadId: Optional[int] = None

@dataclass
class LinkMatch:
    url: str
    parsed: ParsedLink
    start: Optional[int] = None
    end: Optional[int] = None
    entity: Optional[MessageEntity] = None

class TelegramLinkParser:
    """
    supported formats (scheme optional, t.me | telegram.me | telegram.dog):
    - t.me/<username>/<msg>            - t.me/c/<id>/<msg>
    - t.me/<username>/<thread>/<msg>   - t.me/c/<id>/<thread>/<msg>
    - t.me/s/<username>/<msg>
    - any of the above + query (?comment=N, ?thread=N, ?single ... in any order)
    """
    LINK_PATTERN = re.compile(
        r"(?<![\w./@])"
        r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/"
        r"(?:s/)?"
        r"(?:c/(?P<privateId>\d+)|(?P<username>[a-zA-Z][a-zA-Z0-9_]{3,31}))"
        r"/(?P<first>\d+)(?:/(?P<second>\d+))?(?!\w)"
        r"(?P<query>\?[\w=&%\-]*)?",
        re.IGNORECASE,
    )
    _COMMENT_PARAM = re.compile(r"[?&]comment=(\d+)")
    _THREAD_PARAM = re.compile(r"[?&]thread=(\d+)")

    @classmethod
    def _fromMatch(cls, match: re.Match) -> ParsedLink:
        if match.group("privateId"):
            chatId: Union[int, str] = int(f"-100{match.group('privateId')}")
        else:
            chatId = match.group("username")

        first, second = int(match.group("first")), match.group("second")
        threadId = None
        if second is not None:
            threadId, messageId = first, int(second)
        else:
            messageId = first

        query = match.group("query") or ""
        commentMatch = cls._COMMENT_PARAM.search(query)
        threadMatch = cls._THREAD_PARAM.search(query)
        if threadMatch:
            threadId = int(threadMatch.group(1))
        return ParsedLink(
            chatId=chatId,
            messageId=messageId,
            commentId=int(commentMatch.group(1)) if commentMatch else None,
            threadId=threadId,
        )

    @classmethod
    def parseMessageLink(cls, link: str) -> Optional[ParsedLink]:
        match = cls.LINK_PATTERN.search(link or "")
        return cls._fromMatch(match) if match else None

    @classmethod
    def parseExactLink(cls, token: str) -> Optional[ParsedLink]:
        match = cls.LINK_PATTERN.fullmatch(token or "")
        return cls._fromMatch(match) if match else None

    @classmethod
    def extractLinkFromText(cls, text: str) -> Optional[str]:
        match = cls.LINK_PATTERN.search(text or "")
        return match.group(0) if match else None

    @classmethod
    def findLinks(cls, text: Optional[str], entities: Optional[List[MessageEntity]] = None) -> List[LinkMatch]:
        found: List[Tuple[int, LinkMatch]] = []
        text = text or ""
        for match in cls.LINK_PATTERN.finditer(text):
            found.append((match.start(), LinkMatch(
                url=match.group(0), parsed=cls._fromMatch(match), start=match.start(), end=match.end()
            )))
        for entity in entities or []:
            if entity.type != "text_link" or not entity.url:
                continue
            parsed = cls.parseMessageLink(entity.url)
            if parsed:
                found.append((entity.offset, LinkMatch(url=entity.url, parsed=parsed, entity=entity)))
        found.sort(key=lambda item: item[0])
        return [linkMatch for _, linkMatch in found]

_usernameCache: dict[str, Optional[int]] = {}
_USERNAME_CACHE_MAX = 1000

async def _resolveUsername(bot: Bot, username: str) -> Optional[int]:
    key = username.lower()
    if key in _usernameCache:
        return _usernameCache[key]
    try:
        chat = await bot.get_chat(f"@{username}")
        chatId = chat.id
    except Exception as e:
        logger.info(f"[LINK] could not resolve @{username}: {e}")
        chatId = None
    if len(_usernameCache) >= _USERNAME_CACHE_MAX:
        _usernameCache.clear()
    _usernameCache[key] = chatId
    return chatId

async def classifyOwnLink(bot: Bot, parsed: ParsedLink) -> Optional[Tuple[str, int]]:
    """returns ("channel" | "group", numericChatId), or None for foreign/unresolvable links"""
    chatId = parsed.chatId
    if isinstance(chatId, str):
        if settings.CHANNEL_USERNAME and chatId.lower() == settings.CHANNEL_USERNAME.lower():
            return ("channel", settings.CHANNEL_ID)
        chatId = await _resolveUsername(bot, chatId)
        if chatId is None:
            return None
    if chatId == settings.CHANNEL_ID:
        return ("channel", chatId)
    if settings.DISCUSSION_GROUP_ID and chatId == settings.DISCUSSION_GROUP_ID:
        return ("group", chatId)
    return None

def getMessageLink(chatId: int, messageId: Optional[int] = None) -> str:
    strId = str(chatId)
    linkId = strId[4:] if strId.startswith("-100") else strId.lstrip("-")
    base = f"https://t.me/c/{linkId}"
    return f"{base}/{messageId}" if messageId else base
