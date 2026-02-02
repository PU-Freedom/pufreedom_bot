from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from common import ErrorCodeEnum
import logging

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseMiddleware):
    """
    !NOTE :: this is NOT a primary error handler
    its more of a last resort safety net (i)

    all handlers are (and shuold be) decorated with the appropriate error decorator
    (handleCallbackErrors, handleDeleteErrors, handleMessageErrors, etc.)
    which handle errors with full context
    
    !NOTE this middleware only exists to catch anything that SLIPS THROUGH those decorators
    !NOTE if you see logs from here 
        -> something upstream is MISSING ERROR HANDLING!!!!!!
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(
                f"[{ErrorCodeEnum.UNHANDLED_ERROR.value}] :: {handler.__name__ if hasattr(handler, '__name__') else 'unknown'}: {e}",
                exc_info=True
            )
            errorMessage = "❌ Unexpected error occurred. Try again later"
            if isinstance(event, Message):
                await event.reply(errorMessage)
            elif isinstance(event, CallbackQuery):
                await event.answer(errorMessage, show_alert=True)
