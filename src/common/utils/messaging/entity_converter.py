from typing import List, Optional
from aiogram.types import MessageEntity
from aiogram.utils.text_decorations import html_decoration

def entitiesToHtml(text: Optional[str], entities: Optional[List[MessageEntity]] = None) -> str:
    """always escapes, even without entities"""
    if not text:
        return ""
    return html_decoration.unparse(text, entities)
