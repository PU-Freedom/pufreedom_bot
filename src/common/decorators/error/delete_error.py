from aiogram.types import CallbackQuery
from common.enums import ErrorCodeEnum
from common.decorators.error import handlerErrorDecorator

def handleDeleteErrors(successMessage: str = "✅ Deleted successfully"):
    async def onTelegramError(callback: CallbackQuery, e: Exception):
        if "message to delete not found" in str(e).lower():
            await callback.answer("❌ Already deleted or not found", show_alert=True)
        else:
            await callback.answer("❌ Failed to delete", show_alert=True)

    async def onUnexpectedError(callback: CallbackQuery, e: Exception):
        await callback.answer("❌ Error occurred", show_alert=True)

    async def onSuccess(callback: CallbackQuery, _):
        await callback.answer(successMessage)

    return handlerErrorDecorator(
        eventType=CallbackQuery,
        kwargName="callback",
        primaryErrorCode=ErrorCodeEnum.DELETE_ERROR,
        onTelegramError=onTelegramError,
        onUnexpectedError=onUnexpectedError,
        onSuccess=onSuccess
    )
