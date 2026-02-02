from typing import Any
from common.enums import ErrorCodeEnum
from common.decorators.error.generic_error import genericErrorDecorator
import logging

logger = logging.getLogger(__name__)

def handleServiceErrors(operationName: str, reraise: bool = False, defaultReturn: Any = None):
    return genericErrorDecorator(
        errorCode=ErrorCodeEnum.SERVICE_ERROR,
        operationName=operationName,
        reraise=reraise,
        defaultReturn=defaultReturn
    )
