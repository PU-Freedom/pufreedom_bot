from functools import wraps
from typing import Callable, Any, Optional, Type
from aiogram.exceptions import TelegramAPIError
from common.enums import ErrorCodeEnum
import logging

logger = logging.getLogger(__name__)

def _findEvent(eventType: Type, args: tuple, kwargs: dict, kwargName: str):
    """extract the event object (CallbackQuery or Message) from handler args"""
    for arg in args:
        if isinstance(arg, eventType):
            return arg
    return kwargs.get(kwargName)

def handlerErrorDecorator(
    eventType: Type,
    kwargName: str,
    primaryErrorCode: ErrorCodeEnum,
    onTelegramError: Optional[Callable] = None,
    onUnexpectedError: Optional[Callable] = None,
    onSuccess: Optional[Callable] = None,
    logContext: Optional[str] = None
):
    """
    base decorator for handler-level err handling
    what it does/covers:
    -- extraction of event obj from args/kwargs
    -- try/catch skeleton
    -- logging with ErrorCodeEnum

    what it does NOT cover:
    -- what to actually send back to the user on error/success
    -- anything else defined by the callbacks passed in

    args:
    -- eventType:           event class to extract (CallbackQuery or Message)
    -- kwargName:           kwargs key to fall back to if not found in positional args
    -- primaryErrorCode:    ErrorCodeEnum used in log output
    -- onTelegramError:     async (event, exception) -> None; called for TelegramAPIError 
                            if None -> TelegramAPIError falls through to onUnexpectedError
                            (had to include this cuz not all decorators handle TelegramAPIError - e.g. messageErros)
    -- onUnexpectedError:   async (event, exception) -> None; called for any other exception
    -- onSuccess:           async (event, result) -> None; called after handler completes successfully. 
                            !NOTE only used by decorators that NEED a success path
                            (e.g. handleDeleteErrors answering with sucess message)
    -- logContext:          optional extra str appended to the log line
    """
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(*args, **kwargs) -> Any:
            event = _findEvent(eventType, args, kwargs, kwargName)
            contextStr = f" [{logContext}]" if logContext else ""
            try:
                result = await handler(*args, **kwargs)
                if onSuccess and event:
                    await onSuccess(event, result)
                return result

            except TelegramAPIError as e:
                if onTelegramError:
                    logger.error(
                        f"[{primaryErrorCode.value}] :: {handler.__name__}{contextStr} -- {e}",
                        exc_info=True
                    )
                    if event:
                        await onTelegramError(event, e)
                else:
                    logger.error(
                        f"[{ErrorCodeEnum.UNEXPECTED_ERROR.value}] :: "
                        f"[{primaryErrorCode.value}] :: {handler.__name__}{contextStr} -- {e}",
                        exc_info=True
                    )
                    if event and onUnexpectedError:
                        await onUnexpectedError(event, e)
            except Exception as e:
                logger.error(
                    f"[{ErrorCodeEnum.UNEXPECTED_ERROR.value}] :: "
                    f"[{primaryErrorCode.value}] :: {handler.__name__}{contextStr} -- {e}",
                    exc_info=True
                )
                if event and onUnexpectedError:
                    await onUnexpectedError(event, e)
        return wrapper
    return decorator
