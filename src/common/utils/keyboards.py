from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import settings

def buildMessageActionsKeyboard(
    messageId: int,
    canEdit: bool = True
) -> Optional[InlineKeyboardMarkup]:
    buttons = []
    if settings.ENABLE_EDIT and canEdit:
        buttons.append(
            InlineKeyboardButton(
                text="✏️ Edit",
                callback_data=f"edit:{messageId}"
            )
        )
    if settings.ENABLE_DELETE:
        buttons.append(
            InlineKeyboardButton(
                text="🗑 Delete",
                callback_data=f"delete:{messageId}"
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

def buildMessageActionsKeyboardFromMessage(
    messageId: int,
    originalMessage: Message
) -> Optional[InlineKeyboardMarkup]:
    canEdit = (
        (originalMessage.text or originalMessage.caption) and 
        not originalMessage.poll
    )
    return buildMessageActionsKeyboard(messageId, canEdit)

def buildNSFWPromptKeyboard(messageId: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Safe content", callback_data=f"nsfw_safe:{messageId}"),
            InlineKeyboardButton(text="🔞 Mark as NSFW (Spoiler)", callback_data=f"nsfw_mark:{messageId}")
        ],
        [
            InlineKeyboardButton(text="🚫 Cancel", callback_data=f"nsfw_cancel:{messageId}")
        ]
    ])
    