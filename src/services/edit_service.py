import json
import logging
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis
from config import settings
from common import isMediaMessage, buildMessageActionsKeyboard
from db import MessageMappingRepository

logger = logging.getLogger(__name__)

class EditService:
    """service to handle message editing for messages sent to channel"""
    def __init__(self, bot: Bot, redis: Redis, messageMappingRepo: MessageMappingRepository):
        self.bot = bot
        self.redis = redis
        self.messageMappingRepo = messageMappingRepo
    
    async def isInEditMode(self, userId: int) -> bool:
        key = f"editing:{userId}"
        data = await self.redis.get(key)
        return data is not None
    
    async def activateEditMode(
        self,
        userId: int,
        channelMessageId: int,
        userMessageId: int,
        isCaption: bool = False,
        targetChatId: int = None,
        isComment: bool = False,
    ) -> None:
        key = f"editing:{userId}"
        data = {
            "channelMessageId": channelMessageId,
            "userMessageId": userMessageId,
            "mode": "editing",
            "isCaption": isCaption,
            "targetChatId": targetChatId or settings.CHANNEL_ID,
            "isComment": isComment,
        }
        logger.info(f"activating edit mode for user {userId}, channelMessageId: {channelMessageId}, isCaption: {isCaption}, isComment: {isComment}")
        await self.redis.setex(key, 600, json.dumps(data))
    async def deactivateEditMode(self, userId: int) -> None:
        await self.redis.delete(f"editing:{userId}")
    
    async def processEdit(self, message: Message) -> bool:
        key = f"editing:{message.from_user.id}"
        data = await self.redis.get(key)
        if not data: return False
        try:
            editData = json.loads(data)
            if isMediaMessage(message):
                await message.reply(
                    "<b>🥀 Hahaa you can NOT send/change media files dummo 😂✌️</b>\n\n"
                    "<b>You can only edit the text/caption. Send the new text as a <i>PLAIN TEXT MESSAGE</i> 😯✍️</b>",
                    parse_mode="HTML"
                )
                return True
            await self._performEdit(message, editData)
            await self.redis.delete(key)
            targetChatId = editData.get("targetChatId", settings.CHANNEL_ID)
            isComment = editData.get("isComment", False)
            confirmationText = "<b>💗🥰 Message edited successfully ☺️💓</b>"
            if isComment:
                from common import buildCommentActionsKeyboard
                keyboard = buildCommentActionsKeyboard(canEdit=True, groupMessageId=editData["channelMessageId"])
            else:
                keyboard = buildMessageActionsKeyboard(editData["channelMessageId"], canEdit=True)
            try:
                await message.answer(
                    confirmationText,
                    reply_parameters=ReplyParameters(
                        message_id=editData["channelMessageId"],
                        chat_id=targetChatId
                    ),
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.warning(f"[EDIT] reply_parameters failed: {e}, sending without")
                await message.answer(
                    confirmationText,
                    reply_markup=keyboard
                )
            return True
            
        except TelegramAPIError as e:
            logger.error(f"failed to edit message: {e}")
            await message.reply("failed to edit message. try again")
            return True
        except ValueError as e:
            await message.reply(f"{str(e)}")
            return True
        except Exception as e:
            logger.error(f"error processing edit: {e}", exc_info=True)
            await message.reply("error occurred while editing")
            return True

    async def _performEdit(self, message: Message, editData: dict):
        channelMessageId = editData["channelMessageId"]
        targetChatId = editData.get("targetChatId", settings.CHANNEL_ID)
        isComment = editData.get("isComment", False)
        keyboard = None
        
        if isComment:
            from common import buildCommentActionsKeyboard
            keyboard = buildCommentActionsKeyboard(canEdit=True)

        if editData.get("isCaption", False):
            await self._editCaption(message, channelMessageId, targetChatId, keyboard)
        else:
            await self._editText(message, channelMessageId, targetChatId, keyboard)

        if not isComment:
            await self.messageMappingRepo.updateLastEditMessageId(
                userMessageId=editData["userMessageId"],
                userChatId=message.from_user.id,
                lastEditMessageId=message.message_id
            )

    async def _editCaption(self, message: Message, channelMessageId: int, targetChatId: int, replyMarkup=None):
        newContent = message.text or message.caption
        entities = message.entities or message.caption_entities
        if not newContent:
            raise ValueError("<b>📰 Send text or media with caption to edit foo</b>")
        await self.bot.edit_message_caption(
            chat_id=targetChatId,
            message_id=channelMessageId,
            caption=newContent,
            caption_entities=entities,
            parse_mode=None,
            reply_markup=replyMarkup,
        )

    async def _editText(self, message: Message, channelMessageId: int, targetChatId: int, replyMarkup=None):
        if not message.text:
            raise ValueError("<b>📝 Send a text message to edit bruh</b>")
        await self.bot.edit_message_text(
            chat_id=targetChatId,
            message_id=channelMessageId,
            text=message.text,
            entities=message.entities,
            parse_mode=None,
            reply_markup=replyMarkup,
        )
