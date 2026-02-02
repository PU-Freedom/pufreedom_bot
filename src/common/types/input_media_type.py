from typing import Union
from aiogram.types import (
    InputMediaPhoto, 
    InputMediaVideo, 
    InputMediaDocument
)

InputMediaType = Union[InputMediaPhoto, InputMediaVideo, InputMediaDocument]
