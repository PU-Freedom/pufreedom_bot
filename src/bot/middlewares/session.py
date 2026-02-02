from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from config import dbManager
from db import UserRepository, MessageMappingRepository
from services import (
    MessageForwarderService,
    ReplyResolverService,
    EditService
)

class SessionMiddleware(BaseMiddleware):
    """
    per-request SessionMiddleware opens a DB session and builds
    session scoped services each update, reading singletons from dp
    
    so session scoped services are not registered globally 
    as *global-single-instance-deps*(singletons) but only when requested
    
    singleton dependencies (redis, rateLimiter,nsfwChecker)
        are registered in main.py via Dispatcher and are already available in `data` -
        we just read them here, not having to re-create them
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with dbManager.session() as session:
            bot = data.get("bot")
            redis = data.get("redis")
            nsfwChecker = data.get("nsfwChecker")
            rateLimiter = data.get("rateLimiter")

            userRepo = UserRepository(session)
            messageMappingRepo = MessageMappingRepository(session)
            replyResolver = ReplyResolverService(bot, messageMappingRepo)
            editService = EditService(bot, redis, messageMappingRepo)
            messageForwarder = MessageForwarderService(
                bot,
                userRepo,
                messageMappingRepo,
                replyResolver,
                rateLimiter,
                nsfwChecker,
                redis
            )
            data["userRepo"] = userRepo
            data["editService"] = editService
            data["replyResolver"] = replyResolver
            data["messageForwarder"] = messageForwarder
            data["mediaGroupHandler"] = messageForwarder.mediaGroupHandler
            data["messageMappingRepo"] = messageMappingRepo
            return await handler(event, data)
        