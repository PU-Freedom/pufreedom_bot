from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatType
from db import UserRepository
from services.subscription_checker import SubscriptionCheckerService
from common import AliasValidator
from exceptions import AliasValidationError, AliasTakenError, NotSubscribedError
from config import settings
import logging

logger = logging.getLogger(__name__)
router = Router(name="settings")

SETTINGS_HELP = (
    "<b>⚙️ Settings</b>\n\n"
    "<b>Alias</b> - a custom name shown on your channel posts\n\n"
    "Commands:\n"
    "• <code>/settings alias &lt;name&gt;</code> - set your alias\n"
    "• <code>/settings alias remove</code> - remove your alias\n\n"
    "Alias rules: 3-32 characters, <b>letters/digits/underscores only.</b>\n\n"
    "<i>⚠️ Your alias will be removed if you unsubscribe from the channel.</i>"
)

@router.message(Command("settings"), F.chat.type == ChatType.PRIVATE)
async def handleSettings(message: Message, bot: Bot, userRepo: UserRepository):
    try:
        user = await userRepo.getOrCreate(
            telegramId=message.from_user.id,
            username=message.from_user.username,
            firstName=message.from_user.first_name or "",
            lastName=message.from_user.last_name
        )
        args = message.text.split()[1:]
        if not args:
            aliasDisplay = f"<code>{user.alias}</code>" if user.alias else "<i>not set</i>"
            await message.answer(
                f"{SETTINGS_HELP}\n\n"
                f"<b>Your current alias:</b> {aliasDisplay}",
                parse_mode="HTML"
            )
            return

        if args[0] == "alias":
            await _handleAliasCommand(message, bot, userRepo, user, args[1:])
            return

        await message.answer(
            f"Unknown setting: <code>{args[0]}</code>\n\n{SETTINGS_HELP}",
            parse_mode="HTML"
        )
    except NotSubscribedError as e:
        await message.answer(e.userMessage)
        logger.warning(f"[SETTINGS] unsubscribed user {message.from_user.id} tried to set alias")
    except AliasTakenError as e:
        await message.answer(e.userMessage, parse_mode="HTML")
    except Exception as e:
        await message.answer("Something went wrong. Please try again later.")
        logger.error(f"[SETTINGS] unexpected error for user {message.from_user.id}: {e}", exc_info=True)


async def _handleAliasCommand(message: Message, bot: Bot, userRepo: UserRepository, user, args: list):
    if not args:
        aliasDisplay = f"<code>{user.alias}</code>" if user.alias else "<i>not set</i>"
        await message.answer(
            f"<b>Your current alias:</b> {aliasDisplay}\n\n"
            f"Use <code>/settings alias &lt;name&gt;</code> to set one, "
            f"or <code>/settings alias remove</code> to remove it.",
            parse_mode="HTML"
        )
        return

    if args[0] == "remove":
        if not user.alias:
            await message.answer("You don't have an alias set 😔\n\n Wanna fix that 🥺?")
            return
        await userRepo.clearAlias(user.id)
        logger.info(f"[SETTINGS] user {user.telegramId} removed alias")
        await message.answer("😖 Alias removed 😩")
        return

    subscriptionChecker = SubscriptionCheckerService(bot, settings.CHANNEL_ID)
    isSubscribed, subStatus = await subscriptionChecker.isSubscribed(message.from_user.id)
    if not isSubscribed:
        raise NotSubscribedError(status=subStatus)

    aliasValue = args[0]
    try:
        AliasValidator.validate(aliasValue)
    except AliasValidationError as e:
        await message.answer(e.userMessage, parse_mode="HTML")
        return

    existing = await userRepo.getByAlias(aliasValue)
    if existing and existing.id != user.id:
        existingIsSubscribed, _ = await subscriptionChecker.isSubscribed(existing.telegramId)
        if existingIsSubscribed:
            raise AliasTakenError(aliasValue)
        await userRepo.clearAlias(existing.id)
        logger.info(f"[SETTINGS] cleared alias from unsubscribed user {existing.telegramId}, reassigning to {user.telegramId}")

    await userRepo.setAlias(user.id, aliasValue)
    logger.info(f"[SETTINGS] user {user.telegramId} set alias to '{aliasValue}'")
    await message.answer(
        f"✅ Alias set to <code>{aliasValue}</code>\n\n"
        f"It will appear on your future channel posts.\n"
        f"<i>⚠️ Your alias will be removed if you unsubscribe from the channel.</i>",
        parse_mode="HTML"
    )
