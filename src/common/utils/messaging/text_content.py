from dataclasses import dataclass
from typing import List, Optional
from aiogram.types import Message, MessageEntity
from ..telegram.entities import utf16Len, removeLink, joinText

@dataclass
class TextContent:
    text: str
    entities: Optional[List[MessageEntity]] = None

def _nsfwWarning() -> TextContent:
    title = "⚠️ NSFW content warning"
    body = f"{title}\nThis media was detected as NSFW"
    return TextContent(f"{body}\n\n", [
        MessageEntity(type="blockquote", offset=0, length=utf16Len(body)),
        MessageEntity(type="bold", offset=0, length=utf16Len(title)),
    ])

NSFW_WARNING = _nsfwWarning()

def originalText(message: Message) -> TextContent:
    if message.text is not None:
        return TextContent(message.text, message.entities)
    return TextContent(message.caption or "", message.caption_entities)

def buildTextOverride(message: Message, consumedLink=None, addWarning: bool = False) -> Optional[TextContent]:
    """None = keep the message's own text/caption untouched"""
    if consumedLink is None and not addWarning:
        return None
    content = originalText(message)
    text, entities = content.text, content.entities
    if consumedLink is not None and text:
        text, entities = removeLink(text, entities, consumedLink)
    if addWarning:
        text, entities = joinText((NSFW_WARNING.text, NSFW_WARNING.entities), (text, entities))
    return TextContent(text, entities)
