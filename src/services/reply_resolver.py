from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message, ReplyParameters
from db import MessageMappingRepository
from common import (
    TelegramLinkParser,
    ReplyParametersBuilder,
    LinkMatch,
    ParsedLink,
    classifyOwnLink,
)
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

    def _ownChatIds(self) -> set:
        ids = {settings.CHANNEL_ID}
        if settings.DISCUSSION_GROUP_ID:
            ids.add(settings.DISCUSSION_GROUP_ID)
        return ids

    async def resolve(
        self,
        message: Message,
        targetChatId: int
    ) -> Optional[ReplyParameters]:
        replyParams, _ = await self.resolveWithLink(message, targetChatId)
        return replyParams

    async def resolveWithLink(
        self,
        message: Message,
        targetChatId: int
    ) -> Tuple[Optional[ReplyParameters], Optional[LinkMatch]]:
        """consumedLink is set only when the reply target came from a link in the text"""
        logger.info(
            f"[RESOLVE] message {message.message_id}: "
            f"externalReply={message.external_reply is not None}, "
            f"replyTo={message.reply_to_message is not None}"
        )
        if message.external_reply:
            result = self._resolveExternal(message)
            logger.info(f"[RESOLVE] external reply -> {self._fmt(result)}")
            return result, None

        if message.reply_to_message:
            result = await self._resolveDirect(message, message.reply_to_message, targetChatId)
            logger.info(f"[RESOLVE] direct reply -> {self._fmt(result)}")
            return result, None

        return await self.findOwnLink(message)

    async def findOwnLink(self, message: Message) -> Tuple[Optional[ReplyParameters], Optional[LinkMatch]]:
        text = message.text or message.caption
        entities = message.entities if message.text else message.caption_entities
        for linkMatch in TelegramLinkParser.findLinks(text, entities):
            replyParams = await self._paramsForLink(linkMatch.parsed)
            if replyParams:
                logger.info(f"[RESOLVE] link {linkMatch.url} -> {self._fmt(replyParams)}")
                return replyParams, linkMatch
            logger.info(f"[RESOLVE] link {linkMatch.url} is not ours - leaving it in the text")
        return None, None

    @staticmethod
    def _fmt(replyParams: Optional[ReplyParameters]) -> str:
        if not replyParams:
            return "none"
        return f"messageId={replyParams.message_id}, chatId={replyParams.chat_id}"

    def _resolveExternal(self, message: Message) -> Optional[ReplyParameters]:
        externalReply = message.external_reply
        chatId = None
        if externalReply.chat:
            chatId = externalReply.chat.id
        elif getattr(externalReply, 'origin', None) and getattr(externalReply.origin, 'chat', None):
            chatId = externalReply.origin.chat.id
        if not chatId:
            logger.info("[EXTERNAL] no chatId - skipping reply context")
            return None

        if chatId not in self._ownChatIds():
            logger.info(f"[EXTERNAL] reply to chat {chatId} - skipping, not channel or discussion group")
            return None
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
        mapping = await self.messageMappingRepo.getByUserMessageOrLastEditMessage(
            userChatId=replyToMessage.chat.id,
            userMessageId=replyToMessage.message_id,
            channelChatId=targetChatId,
        )
        if mapping:
            quoteText = originalMessage.quote.text if originalMessage.quote else None
            return ReplyParametersBuilder.buildFromMapping(
                mapping,
                quoteText=quoteText,
                source="DIRECT"
            )
        logger.warning(
            f"[DIRECT] no mapping for user message "
            f"messageId={replyToMessage.message_id} | chatId={replyToMessage.chat.id}"
        )

        origin = replyToMessage.forward_origin
        originChat = getattr(origin, 'chat', None) if origin else None
        originMessageId = getattr(origin, 'message_id', None) if origin else None
        if originChat and originMessageId and originChat.id in self._ownChatIds():
            return ReplyParametersBuilder.build(
                messageId=originMessageId,
                chatId=originChat.id,
                source="DIRECT_FORWARD_ORIGIN"
            )
        return None

    async def _paramsForLink(self, parsed: ParsedLink) -> Optional[ReplyParameters]:
        own = await classifyOwnLink(self.bot, parsed)
        if not own:
            return None
        kind, chatId = own
        if kind == "channel" and parsed.commentId and settings.DISCUSSION_GROUP_ID:
            return ReplyParameters(message_id=parsed.commentId, chat_id=settings.DISCUSSION_GROUP_ID)
        return ReplyParameters(message_id=parsed.messageId, chat_id=chatId)
