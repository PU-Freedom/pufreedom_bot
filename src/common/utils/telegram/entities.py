"""
helpers for editing message text WITHOUT breaking its formatting entities

!NOTE tg entity offsets/lengths are in UTF-16 code units, python str indexes are
code points -> any emoji / astral char before an entity shifts them apart.
everything here takes python str indexes for the cut range and converts internally
"""
from typing import List, Optional, Tuple
from aiogram.types import MessageEntity

Entities = Optional[List[MessageEntity]]

def utf16Len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2

def cutRange(text: str, entities: Entities, start: int, end: int) -> Tuple[str, Entities]:
    if start >= end:
        return text, entities
    s16 = utf16Len(text[:start])
    e16 = utf16Len(text[:end])
    removed = e16 - s16

    def remap(pos: int) -> int:
        if pos <= s16: return pos
        if pos <= e16: return s16
        return pos - removed

    newEntities = []
    for entity in entities or []:
        newStart = remap(entity.offset)
        newEnd = remap(entity.offset + entity.length)
        if newEnd > newStart:
            newEntities.append(entity.model_copy(update={"offset": newStart, "length": newEnd - newStart}))
    return text[:start] + text[end:], newEntities or None

def stripText(text: str, entities: Entities) -> Tuple[str, Entities]:
    trailing = len(text) - len(text.rstrip())
    if trailing:
        text, entities = cutRange(text, entities, len(text) - trailing, len(text))
    leading = len(text) - len(text.lstrip())
    if leading:
        text, entities = cutRange(text, entities, 0, leading)
    return text, entities

def dropEntity(entities: Entities, target: MessageEntity) -> Entities:
    remaining = [e for e in entities or [] if e is not target]
    return remaining or None

def removeLink(text: str, entities: Entities, linkMatch) -> Tuple[str, Entities]:
    """linkMatch must come from findLinks() on this same text/entities (text_link is matched by identity)"""
    if linkMatch.entity is not None:
        entities = dropEntity(entities, linkMatch.entity)
    elif linkMatch.start is not None:
        start, end = linkMatch.start, linkMatch.end
        if end < len(text) and text[end] == " ":
            end += 1
        elif start > 0 and text[start - 1] == " ":
            start -= 1
        text, entities = cutRange(text, entities, start, end)
    return stripText(text, entities)
