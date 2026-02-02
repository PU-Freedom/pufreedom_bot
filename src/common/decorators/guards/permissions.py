from functools import wraps
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery
from db import UserRepository, MessageMappingRepository
from config import settings

def checkUserNotBanned(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(*args, **kwargs) -> Any:
        event = args[0] if args else None
        if not event:
            return await handler(*args, **kwargs)
        
        userRepo: UserRepository = kwargs.get('userRepo')
        if not userRepo:
            return await handler(*args, **kwargs)
        
        userId = None
        if isinstance(event, Message):
            userId = event.from_user.id
        elif isinstance(event, CallbackQuery):
            userId = event.from_user.id
        
        if not userId: return await handler(*args, **kwargs)
        user = await userRepo.getByTelegramId(userId)
        fafoTxt = "❌ You are banned from using this bot. FAFO\n\nNow get tf out buddy"
        if user and user.isBanned:
            if isinstance(event, Message):
                await event.reply(fafoTxt)
            elif isinstance(event, CallbackQuery):
                await event.answer(fafoTxt, show_alert=True)
            return
        return await handler(*args, **kwargs)
    return wrapper

def requireMessageOwnership(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(*args, **kwargs) -> Any:
        callback: CallbackQuery = args[0] if args else None
        if not callback:
            return await handler(*args, **kwargs)
        
        messageMappingRepo: MessageMappingRepository = kwargs.get('messageMappingRepo')
        if not messageMappingRepo:
            return await handler(*args, **kwargs)

        try:
            channelMessageId = int(callback.data.split(":")[1])
        except (IndexError, ValueError):
            await callback.answer("❌ invalid message id", show_alert=True)
            return
        
        mapping = await messageMappingRepo.getByChannelMessage(
            channelChatId=settings.CHANNEL_ID,
            channelMessageId=channelMessageId
        )
        
        if not mapping:
            await callback.answer(
                "❌ Message not found or already deleted",
                show_alert=True
            )
            return
        
        if mapping.user.telegramId != callback.from_user.id:
            await callback.answer(
                "❌ You can only manage your own messages",
                show_alert=True
            )
            return
        kwargs['mapping'] = mapping
        kwargs['channelMessageId'] = channelMessageId
        return await handler(*args, **kwargs)
    return wrapper
