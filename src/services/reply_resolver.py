from typing import Optional
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import MessageMappingRepository
from common import TelegramLinkParser
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
            logger.info(f"[RESOLVE] external reply RESOLVED: messageId={result.message_id}, chatId={result.chat_id}")
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

    def _resolveExternal(self, message: Message) -> ReplyParameters:
        externalReply = message.external_reply
        
        if not externalReply.chat or not externalReply.chat.id:
            logger.error(f"[EXTERNAL] external_reply has NO CHAT INFO")
            raise ValueError("external reply missing chat information")
        
        chatId = externalReply.chat.id
        messageId = externalReply.message_id
        logger.info(f"[EXTERNAL] resolved chatId={chatId}, messageId={messageId}")
        if message.quote and message.quote.text:
            logger.info(f"[EXTERNAL] has quote text: {message.quote.text[:50]}...")
            return ReplyParameters(
                message_id=messageId,
                chat_id=chatId,
                quote=message.quote.text,
                quote_parse_mode="HTML"
            )
        else:
            logger.info(f"[EXTERNAL] no quote text")
            return ReplyParameters(
                message_id=messageId,
                chat_id=chatId
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
            if originalMessage.quote and originalMessage.quote.text:
                logger.info(f"[DIRECT] including quote: {originalMessage.quote.text[:50]}...")
                try:
                    return ReplyParameters(
                        message_id=mapping.channelMessageId,
                        chat_id=mapping.channelChatId,
                        quote=originalMessage.quote.text,
                        quote_parse_mode="HTML"
                    )
                except Exception as e:
                    return ReplyParameters(
                        message_id=mapping.channelMessageId,
                        chat_id=mapping.channelChatId
                    )
            else:
                return ReplyParameters(
                    message_id=mapping.channelMessageId,
                    chat_id=mapping.channelChatId
                )
        else:
            logger.warning(
                f"[DIRECT] == X == NO MAPPING FOUND for user message "
                f"replyToMessageMessageId={replyToMessage.message_id} | replyTochatId={replyToMessage.chat.id}"
            )
        
        if replyToMessage.forward_origin and hasattr(replyToMessage.forward_origin, 'chat'):
            logger.info(f"[DIRECT] checking forward origin..")
            origin = replyToMessage.forward_origin
            return ReplyParameters(
                message_id=getattr(origin, 'message_id'),
                chat_id=origin.chat.id
            )
        logger.info(f"[DIRECT] no forward origin either -> returning None")
        return None

    async def _resolveLink(self, text: str) -> Optional[ReplyParameters]:
        link = TelegramLinkParser.extractLinkFromText(text)
        if link:
            parsed = TelegramLinkParser.parseMessageLink(link)
            if parsed:
                chatId, messageId = parsed
                if isinstance(chatId, str):
                    try:
                        chat = await self.bot.get_chat(f"@{chatId}")
                        chatId = chat.id
                        logger.info(f"[LINK] resolved username '{chatId}' to numeric ID {chat.id}")
                    except Exception as e:
                        logger.error(f"[LINK] failed to resolve username to chat ID: {e}")
                        return None
                
                logger.info(f"[LINK] resolved link: chatId={chatId}, messageId={messageId}")
                return ReplyParameters(message_id=messageId, chat_id=chatId)
        return None
    