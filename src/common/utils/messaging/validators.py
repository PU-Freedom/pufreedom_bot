from aiogram.types import Message
from aiogram.enums import ContentType
from .message_type_config import SUPPORTED_CONTENT_TYPES, EDITABLE_CONTENT_TYPES

def isMediaMessage(message: Message) -> bool:
    mediaTypes = {
        ContentType.PHOTO, 
        ContentType.VIDEO, 
        ContentType.DOCUMENT, 
        ContentType.ANIMATION,
        ContentType.AUDIO,
        ContentType.VOICE,
        ContentType.VIDEO_NOTE
    }
    return message.content_type in mediaTypes

def isSupportedType(contentType: ContentType) -> bool:
    return contentType in SUPPORTED_CONTENT_TYPES

def canEditType(contentType: ContentType) -> bool:
    return contentType in EDITABLE_CONTENT_TYPES

# bots can't post custom emoji to channels unless they own a Fragment username - telegram swaps in the fallback emoji
CUSTOM_EMOJI_NOTE = "ℹ️ Custom (premium) emoji show up as regular emoji in the channel - Telegram doesn't let bots post them there."

def hasCustomEmoji(message: Message) -> bool:
    entities = (message.entities or []) + (message.caption_entities or [])
    return any(entity.type == "custom_emoji" for entity in entities)

def isCaption(message: Message) -> bool:
    return bool(
        message.photo or 
        message.video or 
        message.document or
        message.animation or
        message.audio or
        message.voice
    )
