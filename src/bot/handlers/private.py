from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.filters import CommandStart, Command
from common import checkUserNotBanned, handleMessageErrors, settings
from services import MessageForwarderService, EditService, AnonCommentService
from exceptions import BotException, RateLimitExceeded, NotSubscribedError
import logging

logger = logging.getLogger(__name__)
router = Router(name="private")

@router.message(CommandStart())
@handleMessageErrors("Failed to send welcome message")
async def cmdStart(message: Message, channelChatId: str = settings.CHANNEL_USERNAME):
    await message.answer(
        f'<b>🧃 Welcome to <a href="t.me/{channelChatId}">PU Freedom 🆓🏡</a></b>\n\n'
        "<b>🐊 I mean.. you know what to do 😋🍽</b>\n\n"
        "<b>🎥 All content types are supported 👶🏿</b>\n\n"
        "<b><i>Posting something crazy😛👅?</i> Use the Spoiler Overlay to R⬛️D⬛️CT your media.</b>\n"
        "<b>🥹 We dont censor, but we do suggest keeping it clean for the scrolls (but its still up to you).</b>"
    )

@router.message(F.chat.type == ChatType.PRIVATE, Command("anon"))
async def handleAnon(message: Message, anonCommentService: AnonCommentService):
    await anonCommentService.handle(message)

@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.content_type.in_({
        "text",
        "photo", "video", "animation", "document", "audio", "voice",
        "poll", "sticker", "dice", "game",
        "location", "venue", "contact",
        "video_note",
        "story"
    })
)
@checkUserNotBanned
async def handleMessage(
    message: Message,
    messageForwarder: MessageForwarderService,
    editService: EditService
):
    if message.from_user.id == 777000 or message.from_user.is_bot: return
    wasEdited = await editService.processEdit(message)
    if wasEdited: return
    try:
        await messageForwarder.forwardMessage(message)
    except RateLimitExceeded as e:
        await message.reply(e.userMessage)
        logger.warning(
            f"rate limit exceeded for user {message.from_user.id}: "
            f"{e.currentMessageCount}/{e.limit}"
        )
    except NotSubscribedError as e:
        await message.reply(e.userMessage)
        logger.warning(f"unsubscribed user {message.from_user.id} blocked (status={e.status})")
    except BotException as e:
        await message.reply(e.userMessage)
        logger.error(f"bot exception: {e.message}", exc_info=True)
    except Exception as e:
        await message.reply("Unexpected error occurred. Try again later")
        logger.error(f"unexpected error from {message.from_user.id}: {e}", exc_info=True)

@router.message(F.chat.type == ChatType.PRIVATE)
@handleMessageErrors("Failed to send unsupported type message")
async def handleUnsupported(message: Message):
    await message.reply(
        "This message type is not supported\n\n"
        "Now why the FUCK it is NOT supported? DM admin, call him slurs, this bitch cant even setup full content support properly\n"
        "Admin shuold lowk off himself"
    )
