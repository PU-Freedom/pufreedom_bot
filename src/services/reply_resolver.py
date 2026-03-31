from typing import Optional
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import MessageMappingRepository
from common import TelegramLinkParser, ReplyParametersBuilder
from config import settings
import logging

logger = logging.getLogger(__name__)

class ReplyResolverService:
    def __init__(
        self,
        bot: Bot,
        messageMappingRepo: MessageMappingRepository
    ):
        self.bot = bot
        self.messageMappingRepo = messageMappingRepo
    
    async def resolve(
        self,
        message: Message,
        targetChatId: int
    ) -> Optional[ReplyParameters]:
        logger.info(f"[RESOLVE] starting resolution for message {message.message_id}")
        logger.info(f"[RESOLVE] has externalReply: {message.external_reply is not None}")
        logger.info(f"[RESOLVE] has replyToMessage: {message.reply_to_message is not None}")
        
        if message.external_reply:
            logger.info(f"[RESOLVE] resolving external reply | messageId - {message.message_id}")
            result = self._resolveExternal(message)
            logger.info(f"[RESOLVE] external reply RESOLVED: messageId={result.message_id if result else None}, chatId={result.chat_id if result else None}")
            return result

        if message.reply_to_message:
            logger.info(
                f"[RESOLVE] resolving direct reply for message {message.message_id} "
                f"-> replyToMessageId {message.reply_to_message.message_id}"
            )
            result = await self._resolveDirect(message, message.reply_to_message, targetChatId)
            if result:
                logger.info(
                    f"[RESOLVE] == OK == DIRECT reply resolved: messageId={result.message_id}, "
                    f"chatId={result.chat_id}"
                )
            else:
                logger.warning(f"[RESOLVE] == X == direct reply NOT resolved - no mapping found)")
            return result

        text = message.text or message.caption
        if not text:
            logger.info(f"[RESOLVE] no reply found for message {message.message_id}")
            return None
            
        link = TelegramLinkParser.extractLinkFromText(text)
        if link:
            logger.info(f"[RESOLVE] found link in text: {link}")
            return await self._resolveLink(link)

        logger.info(f"[RESOLVE] no reply found for message {message.message_id}")
        return None

    def _resolveExternal(self, message: Message) -> Optional[ReplyParameters]:
        externalReply = message.external_reply
        chatId = None
        if externalReply.chat:
            chatId = externalReply.chat.id
        elif hasattr(externalReply, 'origin') and externalReply.origin:
            if hasattr(externalReply.origin, 'chat') and externalReply.origin.chat:
                chatId = externalReply.origin.chat.id
        if not chatId:
            logger.info("[EXTERNAL] no chatId - skipping reply context")
            return None

        validOrigins = {settings.CHANNEL_ID}
        if settings.DISCUSSION_GROUP_ID:
            validOrigins.add(settings.DISCUSSION_GROUP_ID)

        if chatId not in validOrigins:
            logger.info(
                f"[EXTERNAL] reply to chat {chatId} - skipping, not channel or discussion group"
            )
            return None
        logger.info(f"[EXTERNAL] reply to our channel/group (chatId={chatId}) - creating params")
        quoteText = message.quote.text if message.quote else None
        return ReplyParametersBuilder.build(
            messageId=externalReply.message_id,
            chatId=chatId,
            quoteText=quoteText,
            source="EXTERNAL"
        )

    async def _resolveDirect(
        self, 
        originalMessage: Message,
        replyToMessage: Message, 
        targetChatId: int
    ) -> Optional[ReplyParameters]:
        logger.info(
            f"[DIRECT] trying mapping for user message: "
            f"chatId={replyToMessage.chat.id}, messageId={replyToMessage.message_id}"
        )
        mapping = await self.messageMappingRepo.getByUserMessageOrLastEditMessage(
            userChatId=replyToMessage.chat.id,
            userMessageId=replyToMessage.message_id
        )
        if mapping:
            logger.info(
                f"[DIRECT] == OK == mapping found; channel message info: "
                f"chatId={mapping.channelChatId}, messageId={mapping.channelMessageId}"
            )
            quoteText = originalMessage.quote.text if originalMessage.quote else None
            return ReplyParametersBuilder.buildFromMapping(
                mapping,
                quoteText=quoteText,
                source="DIRECT"
            )
        else:
            logger.warning(
                f"[DIRECT] == X == NO MAPPING FOUND for user message "
                f"replyToMessageMessageId={replyToMessage.message_id} | replyTochatId={replyToMessage.chat.id}"
            )
        
        if replyToMessage.forward_origin and hasattr(replyToMessage.forward_origin, 'chat'):
            logger.info(f"[DIRECT] checking forward origin..")
            origin = replyToMessage.forward_origin
            return ReplyParametersBuilder.build(
                messageId=getattr(origin, 'message_id'),
                chatId=origin.chat.id,
                source="DIRECT_FORWARD_ORIGIN"
            )
        logger.info(f"[DIRECT] no forward origin either -> returning None")
        return None

    async def _resolveLink(self, text: str) -> Optional[ReplyParameters]:
        link = TelegramLinkParser.extractLinkFromText(text)
        if link:
            parsed = TelegramLinkParser.parseMessageLink(link)
            if parsed:
                chatId = parsed.chatId
                if isinstance(chatId, str):
                    try:
                        chat = await self.bot.get_chat(f"@{chatId}")
                        chatId = chat.id
                        logger.info(f"[LINK] resolved username '{parsed.chatId}' to numeric ID {chat.id}")
                    except Exception as e:
                        logger.error(f"[LINK] failed to resolve username to chat ID: {e}")
                        return None

                if parsed.commentId and settings.DISCUSSION_GROUP_ID:
                    logger.info(
                        f"[LINK] comment link resolved: groupId={settings.DISCUSSION_GROUP_ID}, "
                        f"commentId={parsed.commentId}"
                    )
                    return ReplyParameters(
                        message_id=parsed.commentId,
                        chat_id=settings.DISCUSSION_GROUP_ID
                    )

                logger.info(f"[LINK] resolved link: chatId={chatId}, messageId={parsed.messageId}")
                return ReplyParameters(message_id=parsed.messageId, chat_id=chatId)
        return None
    