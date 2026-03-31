from aiogram.types import Message
from aiogram.enums import ContentType
from .message_type_config import MESSAGE_TYPE_CONFIGS

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
    return contentType in MESSAGE_TYPE_CONFIGS

def isCaption(message: Message) -> bool:
    return bool(
        message.photo or 
        message.video or 
        message.document or
        message.animation or
        message.audio or
        message.voice
    )
