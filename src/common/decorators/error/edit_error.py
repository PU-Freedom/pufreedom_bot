from aiogram.types import CallbackQuery
from common.enums import ErrorCodeEnum
from common.decorators.error import handlerErrorDecorator

def handleEditErrors():
    async def onTelegramError(callback: CallbackQuery, e: Exception):
        await callback.answer("❌ Failed to start edit mode", show_alert=True)

    async def onUnexpectedError(callback: CallbackQuery, e: Exception):
        await callback.answer("❌ Error occurred", show_alert=True)

    return handlerErrorDecorator(
        eventType=CallbackQuery,
        kwargName="callback",
        primaryErrorCode=ErrorCodeEnum.EDIT_ERROR,
        onTelegramError=onTelegramError,
        onUnexpectedError=onUnexpectedError
    )
