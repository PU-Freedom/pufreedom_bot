from aiogram.enums import ContentType

SUPPORTED_CONTENT_TYPES = frozenset({
    ContentType.TEXT,
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.ANIMATION,
    ContentType.DOCUMENT,
    ContentType.AUDIO,
    ContentType.VOICE,
    ContentType.VIDEO_NOTE,
    ContentType.CONTACT,
    ContentType.LOCATION,
    ContentType.VENUE,
    ContentType.DICE,
    ContentType.GAME,
    ContentType.STICKER,
    ContentType.POLL,
    ContentType.STORY,
})

EDITABLE_CONTENT_TYPES = frozenset({
    ContentType.TEXT,
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.ANIMATION,
    ContentType.DOCUMENT,
    ContentType.AUDIO,
    ContentType.VOICE,
})
