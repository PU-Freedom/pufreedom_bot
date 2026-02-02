from typing import Optional
from aiogram.types import Message
from common.enums import ErrorCodeEnum
from common.decorators.error import handlerErrorDecorator

def handleMessageErrors(
    errorMessage: str = "❌ Unexpected error occurred. Try again later",
    logContext: Optional[str] = None
):
    async def onUnexpectedError(message: Message, e: Exception):
        await message.reply(errorMessage)

    return handlerErrorDecorator(
        eventType=Message,
        kwargName="message",
        primaryErrorCode=ErrorCodeEnum.GENERAL_ERROR,
        onTelegramError=None,
        onUnexpectedError=onUnexpectedError,
        logContext=logContext
    )
