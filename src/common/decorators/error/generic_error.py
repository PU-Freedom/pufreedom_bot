from functools import wraps
from typing import Callable, Any
from common.enums import ErrorCodeEnum
import logging

logger = logging.getLogger(__name__)

def genericErrorDecorator(
    errorCode: ErrorCodeEnum,
    operationName: str,
    logLevel: int = logging.ERROR,
    reraise: bool = False,
    defaultReturn: Any = None,
    includeTraceback: bool = True
):
    '''
    kind of a base but for generic (not aiogram objs related) errors
    '''
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await handler(*args, **kwargs)
            except Exception as e:
                msg = f"[{errorCode.value}] :: {operationName} :: ({handler.__name__}) -- {e}"
                logger.log(logLevel, msg, exc_info=includeTraceback)
                if reraise:
                    raise
                return defaultReturn
        return wrapper
    return decorator
