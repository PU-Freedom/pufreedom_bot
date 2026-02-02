from typing import Optional
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from common import preserveEntities

class MediaMessageHandler:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def sendPhotoMessage(
        self,
        message: Message,
        channelChatId: int,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None
    ) -> Message:
        photo = message.photo[-1]
        if overrideCaption is not None:
            caption = overrideCaption
            entities = None
        else:
            caption, entities = preserveEntities(
                message.caption or "",
                message.caption_entities
            )
        parseMode = self._resolveParseMode(overrideCaption)
        return await self.bot.send_photo(
            chat_id=channelChatId,
            photo=photo.file_id,
            caption=caption if caption else None,
            caption_entities=entities,
            reply_parameters=replyParams,
            has_spoiler=hasSpoiler,
            parse_mode=parseMode
        )
    
    async def sendVideoMessage(
        self,
        message: Message,
        channelChatId: int,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None
    ) -> Message:
        if overrideCaption is not None:
            caption = overrideCaption
            entities = None
        else:
            caption, entities = preserveEntities(
                message.caption or "",
                message.caption_entities
            )
        parseMode = self._resolveParseMode(overrideCaption)
        return await self.bot.send_video(
            chat_id=channelChatId,
            video=message.video.file_id,
            caption=caption if caption else None,
            caption_entities=entities,
            reply_parameters=replyParams,
            has_spoiler=hasSpoiler,
            parse_mode=parseMode
        )
    
    async def sendDocumentMessage(
        self,
        message: Message,
        channelChatId: int,
        replyParams: Optional[ReplyParameters] = None,
        overrideCaption: Optional[str] = None
    ) -> Message:
        if overrideCaption is not None:
            caption = overrideCaption
            entities = None
        else:
            caption, entities = preserveEntities(
                message.caption or "",
                message.caption_entities
            )
        parseMode = self._resolveParseMode(overrideCaption)
        return await self.bot.send_document(
            chat_id=channelChatId,
            document=message.document.file_id,
            caption=caption if caption else None,
            caption_entities=entities,
            reply_parameters=replyParams,
            parse_mode=parseMode
        )
    
    async def sendAnimationMessage(
        self,
        message: Message,
        channelChatId: int,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None
    ) -> Message:
        if overrideCaption is not None:
            caption = overrideCaption
            entities = None
        else:
            caption, entities = preserveEntities(
                message.caption or "",
                message.caption_entities
            )
        parseMode = self._resolveParseMode(overrideCaption)
        return await self.bot.send_animation(
            chat_id=channelChatId,
            animation=message.animation.file_id,
            caption=caption if caption else None,
            caption_entities=entities,
            reply_parameters=replyParams,
            has_spoiler=hasSpoiler,
            parse_mode=parseMode
        )
    
    def _resolveParseMode(self, overrideCaption: str | None) -> str | None:
        return "HTML" if overrideCaption else None
    