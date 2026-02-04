import asyncio
import json
import logging
from typing import List
from aiogram import Bot
from aiogram.types import (
    Message, 
    InputMediaPhoto, 
    InputMediaVideo, 
    InputMediaDocument,
    ReplyParameters
)
from db import UserRepository, MessageMappingRepository
from services.nsfw import NSFWChecker
from services.reply_resolver import ReplyResolverService
from common import (
    buildNSFWPromptKeyboard, 
    getMessageLink, 
    entitiesToHtml,
    MappingUtil,
    InputMediaType,
)
from config import settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class MediaGroupHandler:
    def __init__(
        self,
        bot: Bot,
        userRepo: UserRepository,
        messageMappingRepo: MessageMappingRepository,
        replyResolver: ReplyResolverService,
        nsfwChecker: NSFWChecker,
        redis: Redis
    ):
        self.bot = bot
        self.userRepo = userRepo
        self.messageMappingRepo = messageMappingRepo
        self.nsfwChecker = nsfwChecker
        self.replyResolver = replyResolver
        self.redis = redis
    
    async def handleMediaGroupMessage(self, message: Message, user) -> None:
        """collect n batch media group messages"""
        groupId = message.media_group_id
        bufferKey = f"media_group:{groupId}"
        counterKey = f"media_group_counter:{groupId}"
        processedKey = f"media_group_processed:{groupId}"
        
        if await self.redis.get(processedKey):
            logger.info(f"group {groupId} already processed, skipping message {message.message_id}")
            return
        
        count = await self.redis.incr(counterKey)
        await self.redis.expire(counterKey, 10)
        replyChannelMessageId = None
        replyChannelChatId = None
        if count == 1 and message.reply_to_message:
            mapping = await self.messageMappingRepo.getByUserMessageOrLastEditMessage(
                userChatId=message.reply_to_message.chat.id,
                userMessageId=message.reply_to_message.message_id
            )
            if mapping:
                replyChannelMessageId = mapping.channelMessageId
                replyChannelChatId = mapping.channelChatId
                logger.info(
                    f"[MEDIA_GROUP_REPLY] found reply mapping for group: "
                    f"userMessage={message.reply_to_message.message_id} -> "
                    f"channelMessageId={replyChannelMessageId}, channelChatId={replyChannelChatId}"
                )
        
        quoteText = None
        if count == 1 and message.quote and message.quote.text:
            quoteText = message.quote.text
            logger.info(f"[MEDIA_GROUP] saving quote text: {quoteText[:50]}...")

        existingData = await self.redis.get(bufferKey)
        if existingData:
            bufferData = json.loads(existingData)
            messageIds = bufferData.get('messageIds', [])
            if not replyChannelMessageId and 'replyToMessageId' in bufferData:
                replyChannelMessageId = bufferData.get('replyToMessageId')
                replyChannelChatId = bufferData.get('replyToChatId')
        else: messageIds = []
        messageIds.append({
            'messageId': message.message_id,
            'chatId': message.chat.id,
            'userId': user.id
        })
        bufferData = {
            'messageIds': messageIds,
            'userId': user.id,
            'replyToMessageId': replyChannelMessageId,
            'replyToChatId': replyChannelChatId,
            'quoteText': quoteText
        }
        await self.redis.setex(bufferKey, 10, json.dumps(bufferData))
        if count == 1:
            logger.info(f"message {message.message_id} spawning coordinator for group {groupId}")
            asyncio.create_task(self._coordinateGroup(groupId))
        else:
            logger.info(f"message {message.message_id} added to group {groupId} (count: {count})")

    async def _coordinateGroup(self, groupId: str):
        bufferKey = f"media_group:{groupId}"
        processedKey = f"media_group_processed:{groupId}"
        counterKey = f"media_group_counter:{groupId}"
        try:
            await asyncio.sleep(2)
            finalData = await self.redis.get(bufferKey)
            if not finalData:
                logger.warning(f"no buffer data found for group {groupId}")
                return
            
            finalBuffer = json.loads(finalData)
            await self.redis.setex(processedKey, 10, "1")
            await self._processGroup(groupId, finalBuffer)
            await self.redis.delete(bufferKey)
            await self.redis.delete(counterKey)
        except Exception as e:
            logger.error(f"error coordinating group {groupId}: {e}", exc_info=True)
    
    async def _processGroup(self, groupId: str, bufferData: dict):
        messageIds = bufferData['messageIds']
        userId = bufferData['userId']
        logger.info(f"processing media group {groupId} with {len(messageIds)} messages")
        try:
            user = await self.userRepo.getById(userId)
            chatId = messageIds[0]['chatId']
            if settings.ENABLE_NSFW_CHECK:
                await self._handleNSFWCheck(messageIds, user, chatId, bufferData)
            else:
                await self.sendToChannel(
                    messageIds, 
                    user, 
                    chatId, 
                    hasSpoiler=False,
                    forceReplyToMessageId=bufferData.get('replyToMessageId'),
                    forceReplyToChatId=bufferData.get('replyToChatId'),
                    forceQuoteText=bufferData.get('quoteText')
                )
        except Exception as e:
            logger.error(f"error processing media group: {e}", exc_info=True)

    async def _handleNSFWCheck(self, messageIds: List[dict], user, chatId: int, bufferData: dict):
        if settings.ENFORCED_NSFW_CHECK:
            firstMessage = await self.bot.forward_message(
                chat_id=chatId,
                from_chat_id=chatId,
                message_id=messageIds[0]['messageId']
            )
            await self.bot.delete_message(chatId, firstMessage.message_id)
            isSafe, reason = await self.nsfwChecker.checkMessage(self.bot, firstMessage)            
            hasSpoiler = False
            if not isSafe:
                logger.warning(f"nsfw album detected from user {user.telegramId}")
                await self.bot.send_message(
                    chat_id=chatId,
                    text=(
                        f"<b>🔞 NSFW content detected</b>\n\n"
                        f"Reason: {reason}\n"
                        f"Your post will be sent with spoilers"
                    ),
                    parse_mode="HTML"
                )
                hasSpoiler = True
            await self.sendToChannel(
                messageIds, 
                user, 
                chatId, 
                hasSpoiler=hasSpoiler,
                forceReplyToMessageId=bufferData.get('replyToMessageId'),
                forceReplyToChatId=bufferData.get('replyToChatId'),
                forceQuoteText=bufferData.get('quoteText')
            )
        else:
            await self._promptUser(messageIds, user, chatId, bufferData)

    async def _promptUser(self, messageIds: List[dict], user, chatId: int, bufferData: dict):
        keyboard = buildNSFWPromptKeyboard(messageIds[0]['messageId'])
        key = f"nsfw_pending_group:{messageIds[0]['messageId']}"
        data = {
            'userId': user.id,
            'messageIds': [m['messageId'] for m in messageIds],
            'chatId': chatId,
            'replyToMessageId': bufferData.get('replyToMessageId'),
            'replyToChatId': bufferData.get('replyToChatId'),
            'quoteText': bufferData.get('quoteText')
        }
        await self.redis.setex(key, 300, json.dumps(data))
        await self.bot.send_message(
            chat_id=chatId,
            text=(
                "<b>📸 Media detected</b>\n\n"
                "Do these media files contain NSFW/Sensitive content?\n"
                "Marking as NSFW will add spoiler to all images"
            ),
            parse_mode="HTML",
            reply_markup=keyboard
        )

    async def sendToChannel(
        self, 
        messageIds: List[dict],
        user,
        chatId: int,
        hasSpoiler: bool = False,
        addWarning: bool = False,
        forceReplyToMessageId: int = None,
        forceReplyToChatId: int = None,
        forceQuoteText: str = None
    ) -> None:
        try:
            firstOriginalMessage = await self.bot.forward_message(
                chat_id=chatId,
                from_chat_id=chatId,
                message_id=messageIds[0]['messageId']
            )
            if forceReplyToMessageId and forceReplyToChatId:
                if forceQuoteText:
                    logger.info(f"[MEDIA_GROUP] including forced quote: {forceQuoteText[:50]}...")
                    replyParams = ReplyParameters(
                        message_id=forceReplyToMessageId,
                        chat_id=forceReplyToChatId,
                        quote=forceQuoteText,
                        quote_parse_mode="HTML"
                    )
                else:
                    logger.info(
                        f"[MEDIA_GROUP] using forced reply params (no quotes) "
                        f"messageId={forceReplyToMessageId}, chatId={forceReplyToChatId}"
                    )
                    replyParams = ReplyParameters(
                        message_id=forceReplyToMessageId,
                        chat_id=forceReplyToChatId
                    )
            else:
                replyParams = await self.replyResolver.resolve(firstOriginalMessage, settings.CHANNEL_ID)
                if replyParams:
                    logger.info(
                        f"[MEDIA_GROUP] == OK == reply params: "
                        f"messageId={replyParams.message_id}, chatId={replyParams.chat_id}"
                    )
                else:
                    logger.warning(f"[MEDIA_GROUP] == X == NO REPLY PARAMS")
            await self.bot.delete_message(chatId, firstOriginalMessage.message_id)
            
            messages = []
            for messageData in messageIds:
                message = await self.bot.forward_message(
                    chat_id=chatId,
                    from_chat_id=chatId,
                    message_id=messageData['messageId']
                )
                messages.append(message)
                await self.bot.delete_message(chatId, message.message_id)
            
            mediaGroup = []
            for idx, message in enumerate(messages):
                if idx == 0:
                    originalCaption = message.caption if message.caption else ""
                    captionEntities = message.caption_entities
                    if originalCaption and captionEntities:
                        formattedCaption = entitiesToHtml(originalCaption, captionEntities)
                    else:
                        formattedCaption = originalCaption
                    
                    caption = formattedCaption
                    useHtmlParse = bool(captionEntities)

                    # !NOTE: send_media_group does NOT support reply_parameters at the Telegram API level 
                    # -> reply context is included in text message 
                    # --> as a link prefix in the first items caption
                    if replyParams:
                        messageLink = getMessageLink(
                            replyParams.chat_id, 
                            replyParams.message_id
                        )
                        replyPrefix = f"<b>↩️ <a href='{messageLink}'>Replying to message</a></b>"
                        logger.info(f"[MEDIA_GROUP] constructed reply prefix: {replyPrefix}")
                        caption = replyPrefix + "\n\n" + caption if caption else replyPrefix
                        logger.info(f"[MEDIA_GROUP] final caption length: {len(caption)}")
                        useHtmlParse = True
                    
                    if addWarning:
                        warningText = (
                            "<blockquote><b>⚠️ NSFW content warning</b>\n"
                            "This media was detected as NSFW</blockquote>\n\n"
                        )
                        caption = warningText + caption
                        useHtmlParse = True
                    if not caption: caption = None
                else:
                    caption = None
                    useHtmlParse = False

                parseMode = "HTML" if useHtmlParse and caption else None
                mediaItem = self._resolveMediaItemType(message, caption, hasSpoiler, parseMode)
                if mediaItem:
                    mediaGroup.append(mediaItem)
                else:
                    logger.warning(f"message {message.message_id} in group had no recognizable media")
            
            if not mediaGroup:
                raise ValueError("no valid media items found to send in group")
            logger.info("sending MEDIA GROUP (reply context embedded in caption)")
            sentMessages = await self.bot.send_media_group(
                chat_id=settings.CHANNEL_ID,
                media=mediaGroup
            )
            for messageData, sentMessage in zip(messageIds, sentMessages):
                await MappingUtil.createAndLog(
                    self.messageMappingRepo,
                    userId=user.id,
                    userChatId=messageData['chatId'],
                    userMessageId=messageData['messageId'],
                    channelChatId=sentMessage.chat.id,
                    channelMessageId=sentMessage.message_id
                )
            from common import buildMessageActionsKeyboard
            keyboard = buildMessageActionsKeyboard(
                sentMessages[0].message_id,
                canEdit=False
            )
            confirmText = "😘😍 Message sent"
            confirmText += " with 😍NSFW😍 spoilers 🔞" if hasSpoiler else " to the channel 😚☺️😽"
            await self.bot.send_message(
                chat_id=chatId,
                text=confirmText,
                reply_parameters=ReplyParameters(
                    message_id=sentMessages[0].message_id,
                    chat_id=settings.CHANNEL_ID
                ),
                reply_markup=keyboard
            )
            logger.info(f"[MEDIA_GROUP] sent media group with {len(messages)} items to channel")
            if len(sentMessages) > 1:
                firstId = sentMessages[0].message_id
                siblingIds = [message.message_id for message in sentMessages[1:]]
                await self.redis.setex(
                    f"media_group_siblings:{firstId}",
                    604800,  # 7 days
                    json.dumps(siblingIds)
                )
        except Exception as e:
            logger.error(f"error sending media group: {e}", exc_info=True)
            raise

    @staticmethod
    def _resolveMediaItemType(
        message: Message, 
        caption: str | None = None,
        hasSpoiler: bool = False, 
        parseMode: str | None = None,
    ) -> InputMediaType | None:
        kwargs = {"caption": caption, "parse_mode": parseMode}
        if message.photo:
            return InputMediaPhoto(
                media=message.photo[-1].file_id, 
                has_spoiler=hasSpoiler, 
                **kwargs
            )
        videoObj = message.video or message.animation
        if videoObj:
            return InputMediaVideo(
                media=videoObj.file_id, 
                has_spoiler=hasSpoiler, 
                **kwargs
            )
        if message.document:
            return InputMediaDocument(
                media=message.document.file_id, 
                **kwargs
            )
        return None
        