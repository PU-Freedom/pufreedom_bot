from aiogram.types import CallbackQuery
from common.enums import ErrorCodeEnum
from common.decorators.error.base import handlerErrorDecorator

def handleCallbackErrors(
    errorMessage: str = "❌ Error occurred",
    showAlert: bool = True,
    deleteMessageOnError: bool = False
):
    async def onTelegramError(callback: CallbackQuery, e: Exception):
        await callback.answer(f"{errorMessage} (Telegram Error)", show_alert=showAlert)
        if deleteMessageOnError:
            try:
                await callback.message.delete()
            except Exception:
                pass

    async def onUnexpectedError(callback: CallbackQuery, e: Exception):
        await callback.answer(errorMessage, show_alert=showAlert)
        if deleteMessageOnError:
            try:
                await callback.message.delete()
            except Exception:
                pass

    return handlerErrorDecorator(
        eventType=CallbackQuery,
        kwargName="callback",
        primaryErrorCode=ErrorCodeEnum.TG_API_ERROR,
        onTelegramError=onTelegramError,
        onUnexpectedError=onUnexpectedError
    )
