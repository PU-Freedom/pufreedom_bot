from dataclasses import dataclass
from typing import Callable, Dict, Any
from aiogram.enums import ContentType
from aiogram.types import Message, ReplyParameters
from .message_params_builder import MessageParamsBuilder

@dataclass
class MessageTypeConfig:
    """
    maps each tg ContentType to its send method and param builder

    attributes:
    - sendMethod: name of the bot method to call (e.g., send_photo, copy_message)
    - paramBuilder: function that builds parameters for the send method
    - canEdit: flag indicating whether message can be edited
    """
    sendMethod: str
    paramBuilder: Callable[[Message, int, ReplyParameters, ...], Dict[str, Any]]
    canEdit: bool = False

MESSAGE_TYPE_CONFIGS: Dict[ContentType, MessageTypeConfig] = {
    ContentType.TEXT: MessageTypeConfig(
        sendMethod="copy_message",
        paramBuilder=MessageParamsBuilder.buildCopyMessageParams,
        canEdit=True,
    ),
    ContentType.PHOTO: MessageTypeConfig(
        sendMethod="send_photo",
        paramBuilder=MessageParamsBuilder.buildPhotoParams,
        canEdit=True,
    ),
    ContentType.VIDEO: MessageTypeConfig(
        sendMethod="send_video",
        paramBuilder=MessageParamsBuilder.buildVideoParams,
        canEdit=True,
    ),
    ContentType.ANIMATION: MessageTypeConfig(
        sendMethod="send_animation",
        paramBuilder=MessageParamsBuilder.buildAnimationParams,
        canEdit=True,
    ),
    ContentType.DOCUMENT: MessageTypeConfig(
        sendMethod="send_document",
        paramBuilder=MessageParamsBuilder.buildDocumentParams,
        canEdit=True,
    ),
    ContentType.AUDIO: MessageTypeConfig(
        sendMethod="send_audio",
        paramBuilder=MessageParamsBuilder.buildAudioParams,
        canEdit=True,
    ),
    ContentType.VOICE: MessageTypeConfig(
        sendMethod="send_voice",
        paramBuilder=MessageParamsBuilder.buildVoiceParams,
        canEdit=True,
    ),
    ContentType.VIDEO_NOTE: MessageTypeConfig(
        sendMethod="send_video_note",
        paramBuilder=MessageParamsBuilder.buildVideoNoteParams,
        canEdit=False,
    ),
    ContentType.CONTACT: MessageTypeConfig(
        sendMethod="send_contact",
        paramBuilder=MessageParamsBuilder.buildContactParams,
        canEdit=False,
    ),
    ContentType.LOCATION: MessageTypeConfig(
        sendMethod="send_location",
        paramBuilder=MessageParamsBuilder.buildLocationParams,
        canEdit=False,
    ),
    ContentType.VENUE: MessageTypeConfig(
        sendMethod="send_venue",
        paramBuilder=MessageParamsBuilder.buildVenueParams,
        canEdit=False,
    ),
    ContentType.DICE: MessageTypeConfig(
        sendMethod="send_dice",
        paramBuilder=MessageParamsBuilder.buildDiceParams,
        canEdit=False,
    ),
    ContentType.GAME: MessageTypeConfig(
        sendMethod="send_game",
        paramBuilder=MessageParamsBuilder.buildGameParams,
        canEdit=False,
    ),
    ContentType.STICKER: MessageTypeConfig(
        sendMethod="send_sticker",
        paramBuilder=MessageParamsBuilder.buildStickerParams,
        canEdit=False,
    ),
    ContentType.POLL: MessageTypeConfig(
        sendMethod="send_poll",
        paramBuilder=MessageParamsBuilder.buildPollParams,
        canEdit=False,
    ),
    ContentType.STORY: MessageTypeConfig(
        sendMethod="copy_message",
        paramBuilder=MessageParamsBuilder.buildCopyMessageParams,
        canEdit=False,
    ),
}

def getConfig(contentType: ContentType) -> MessageTypeConfig:
    return MESSAGE_TYPE_CONFIGS[contentType]
