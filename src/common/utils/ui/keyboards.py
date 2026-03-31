from typing import Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import settings

def buildAliasKeyboard(
    alias: str,
    groupId: Optional[int] = None,
    groupMsgId: Optional[int] = None,
) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=f"✍️ {alias}", callback_data=f"alias:{alias}")]
    if groupId and groupMsgId:
        numericId = str(abs(groupId))[3:]
        commentsUrl = f"https://t.me/c/{numericId}/{groupMsgId}?thread={groupMsgId}"
        buttons.append(InlineKeyboardButton(text="💬 Comments", url=commentsUrl))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

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

def buildCommentActionsKeyboard(
    canEdit: bool = False,
    groupMessageId: Optional[int] = None,
) -> InlineKeyboardMarkup:
    """
    groupMessageId: embed in callback data when keyboard is on a private message
    (so the handler can identify the group message). Omit for group-posted keyboards
    — the handler will use callback.message.message_id instead.
    """
    suffix = f":{groupMessageId}" if groupMessageId is not None else ""
    buttons = []
    if canEdit:
        buttons.append(
            InlineKeyboardButton(
                text="✏️ Edit",
                callback_data=f"comment_edit{suffix}"
            )
        )
    buttons.append(
        InlineKeyboardButton(
            text="🗑 Delete",
            callback_data=f"comment_delete{suffix}"
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def buildCancelEditKeyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Cancel edit", callback_data="cancel_edit")]
    ])

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
    