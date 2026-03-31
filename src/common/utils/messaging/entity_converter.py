from typing import List, Optional
from aiogram.types import MessageEntity
import html

def entitiesToHtml(text: str, entities: Optional[List[MessageEntity]] = None) -> str:
    """
    converts tg message entities to html formatting with proper nesting support
    args:
    -- text: the message text
    -- entities: list of messageEntity objs
    returns: html formatted string
    """
    if not entities or not text: return text
    escapedText = html.escape(text)
    events = []
    for entity in entities:
        events.append((entity.offset, 'open', entity))
        events.append((entity.offset + entity.length, 'close', entity))
    
    events.sort(key=lambda x: (x[0], x[1] == 'open'))
    result = []; openTags = []; lastPos = 0
    for pos, eventType, entity in events:
        if pos > lastPos:
            result.append(escapedText[lastPos:pos])
        if eventType == 'open':
            tag = _getOpeningTag(entity)
            result.append(tag)
            openTags.append((entity, tag))
        else:
            for i in range(len(openTags) - 1, -1, -1):
                if openTags[i][0] == entity:
                    tagsToReopen = []
                    for j in range(len(openTags) - 1, i, -1):
                        closingTag = _getClosingTag(openTags[j][0])
                        result.append(closingTag)
                        tagsToReopen.append(openTags[j])
                    closingTag = _getClosingTag(entity)
                    result.append(closingTag)
                    openTags.pop(i)
                    for tagInfo in reversed(tagsToReopen):
                        openingTag = _getOpeningTag(tagInfo[0])
                        result.append(openingTag)
                    break
        lastPos = pos
    if lastPos < len(escapedText):
        result.append(escapedText[lastPos:])
    return ''.join(result)

def _getOpeningTag(entity: MessageEntity) -> str:
    if entity.type == "bold":
        return "<b>"
    elif entity.type == "italic":
        return "<i>"
    elif entity.type == "underline":
        return "<u>"
    elif entity.type == "strikethrough":
        return "<s>"
    elif entity.type == "spoiler":
        return "<span class='tg-spoiler'>"
    elif entity.type == "code":
        return "<code>"
    elif entity.type == "pre":
        language = entity.language or ""
        return f"<pre><code class='language-{language}'>"
    elif entity.type == "text_link":
        url = entity.url or ""
        return f"<a href='{html.escape(url)}'>"
    elif entity.type == "text_mention":
        user_id = entity.user.id if entity.user else ""
        return f"<a href='tg://user?id={user_id}'>"
    elif entity.type == "blockquote":
        return "<blockquote>"
    else:
        return ""

def _getClosingTag(entity: MessageEntity) -> str:
    if entity.type == "bold":
        return "</b>"
    elif entity.type == "italic":
        return "</i>"
    elif entity.type == "underline":
        return "</u>"
    elif entity.type == "strikethrough":
        return "</s>"
    elif entity.type == "spoiler":
        return "</span>"
    elif entity.type == "code":
        return "</code>"
    elif entity.type == "pre":
        return "</code></pre>"
    elif entity.type in ["text_link", "text_mention"]:
        return "</a>"
    elif entity.type == "blockquote":
        return "</blockquote>"
    else:
        return ""
    