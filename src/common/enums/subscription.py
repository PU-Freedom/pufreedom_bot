from aiogram.enums import ChatMemberStatus

SUBSCRIBED_STATUSES = frozenset({
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
})
