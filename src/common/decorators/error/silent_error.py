from common.enums import ErrorCodeEnum
from common.decorators.error.generic_error import genericErrorDecorator
import logging

logger = logging.getLogger(__name__)

def silentErrors(operationName: str = "operation"):
    return genericErrorDecorator(
        errorCode=ErrorCodeEnum.SILENT_ERROR,
        operationName=operationName,
        logLevel=logging.WARNING,
        includeTraceback=False
    )
