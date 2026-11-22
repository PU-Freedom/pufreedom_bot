from typing import Optional
from aiogram.types import Message
from .entity_converter import entitiesToHtml
from ..telegram.entities import removeLink

NSFW_WARNING_HTML = (
    "<blockquote><b>⚠️ NSFW content warning</b>\n"
    "This media was detected as NSFW</blockquote>\n\n"
)

class CaptionBuilder:
    @staticmethod
    def buildCaption(
        message: Message,
        addWarning: bool = False,
        consumedLink=None,
    ) -> tuple[Optional[str], Optional[str]]:
        text = message.caption or ""
        entities = message.caption_entities
        if consumedLink is not None and text:
            text, entities = removeLink(text, entities, consumedLink)

        caption = entitiesToHtml(text, entities)
        if addWarning:
            caption = NSFW_WARNING_HTML + caption
        return (caption, "HTML") if caption else (None, None)
