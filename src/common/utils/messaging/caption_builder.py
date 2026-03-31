from typing import Optional
from aiogram.types import Message
from .entity_converter import entitiesToHtml
from ..telegram.link_parser import TelegramLinkParser

class CaptionBuilder:
    @staticmethod
    def buildCaption(
        message: Message,
        addWarning: bool = False,
        isReplyLinkToBeRemoved: bool = False,
        hasReply: bool = False,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        build caption from msg w/ opt modifs
        """
        originalCaption = message.caption if message.caption else ""
        captionEntities = message.caption_entities

        if originalCaption and captionEntities:
            formattedCaption = entitiesToHtml(originalCaption, captionEntities)
        else:
            formattedCaption = originalCaption

        caption = formattedCaption
        useHtmlParseMode = bool(captionEntities)
        parseMode = 'HTML' if useHtmlParseMode else None

        if isReplyLinkToBeRemoved and hasReply and caption:
            extractedLink = TelegramLinkParser.extractLinkFromText(caption)
            if extractedLink:
                caption = caption.replace(extractedLink, "").strip()

        if addWarning:
            warningText = (
                "<blockquote><b>⚠️ NSFW content warning</b>\n"
                "This media was detected as NSFW</blockquote>\n\n"
            )
            caption = warningText + caption if caption else warningText
            parseMode = 'HTML'

        return caption if caption else None, parseMode
    