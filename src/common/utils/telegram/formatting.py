from typing import List, Optional
from aiogram.types import MessageEntity

def preserveEntities(
    text: str,
    entities: Optional[List[MessageEntity]] = None
) -> tuple[str, Optional[List[MessageEntity]]]:
    if not entities:
        return (text, None)
    validEntities = []
    textLen = len(text)    
    for entity in entities:
        if entity.offset + entity.length <= textLen:
            validEntities.append(entity)
    return (text, validEntities if validEntities else None)

def escapeMarkdown(text: str) -> str:
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def truncateText(text: str, max_length: int = 4096, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
