from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from common import checkUserNotBanned, handleMessageErrors
from services import MessageForwarderService, EditService
from exceptions import BotException, RateLimitExceeded
import logging

logger = logging.getLogger(__name__)
router = Router(name="private")

@router.message(CommandStart())
@handleMessageErrors("Failed to send welcome message")
async def cmdStart(message: Message):
    await message.answer(
        "Welcome to PU Freedom bruh\n\n"
        "I mean.. you know what to do\n\n"
        "media files (photos, videos, docs) are supported so GO KRAAAZY - aint nobody holding your freak here\n"
        "polls are good to go too\n\n"
        "NOTE: you can send up to 5 messages per minute"
    )

@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.content_type.in_({
        "text", "photo", "video", "animation", "document", "poll", "sticker"
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
        "This message type is not supported cuh\n\n"
        "Supported types:\n"
        "• text messages\n"
        "• photos\n"
        "• videos\n"
        "• animations (gifs)\n"
        "• documents\n"
        "• polls\n"
        "• stickers"
    )
