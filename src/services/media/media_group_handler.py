import asyncio
import json
import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    Message,
    MessageEntity,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio,
    ReplyParameters,
)
from db import UserRepository, MessageMappingRepository
from services.moderation import NSFWChecker, NSFWDataManager
from services.reply_resolver import ReplyResolverService
from common import (
    buildNSFWPromptKeyboard,
    buildMessageActionsKeyboard,
    MappingUtil,
    TextContent,
    originalText,
    buildTextOverride,
    joinText,
    utf16Len,
)
from config import settings, dbManager
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

COLLECT_SECONDS = 2

class MediaGroupHandler:
    """
    album items arrive as separate updates: they are buffered in redis (atomic RPUSH of the
    full message json), then one coordinator task sends the whole album after COLLECT_SECONDS
    """
    def __init__(
        self,
        bot: Bot,
        messageMappingRepo: MessageMappingRepository,
        nsfwChecker: NSFWChecker,
        redis: Redis
    ):
        self.bot = bot
        self.messageMappingRepo = messageMappingRepo
        self.nsfwChecker = nsfwChecker
        self.redis = redis

    async def handleMediaGroupMessage(self, message: Message, user) -> None:
        key = f"media_group:{message.media_group_id}"
        async with self.redis.pipeline(transaction=True) as pipe:
            count, _ = await pipe.rpush(key, message.model_dump_json(exclude_none=True)).expire(key, 60).execute()
        if count == 1:
            asyncio.create_task(self._coordinateGroup(message.media_group_id, user.id))

    async def _coordinateGroup(self, groupId: str, userId: int) -> None:
        key = f"media_group:{groupId}"
        messages: List[Message] = []
        try:
            await asyncio.sleep(COLLECT_SECONDS)
            async with self.redis.pipeline(transaction=True) as pipe:
                raw, _ = await pipe.lrange(key, 0, -1).delete(key).execute()
            messages = sorted((Message.model_validate_json(item) for item in raw), key=lambda m: m.message_id)
            logger.info(f"[MEDIA_GROUP] {groupId}: {len(messages)} items collected")

            if settings.ENABLE_NSFW_CHECK and not settings.ENFORCED_NSFW_CHECK:
                await self._promptUser(messages, userId)
                return

            # runs after the request's db session is closed -> needs its own
            async with dbManager.session() as session:
                user = await UserRepository(session).getById(userId)
                isNSFW = settings.ENABLE_NSFW_CHECK and await self._detectNSFW(messages[0])
                await self.sendToChannel(
                    messages, user, hasSpoiler=isNSFW, addWarning=isNSFW,
                    mappingRepo=MessageMappingRepository(session),
                )
        except Exception as e:
            logger.error(f"[MEDIA_GROUP] failed to process group {groupId}: {e}", exc_info=True)
            if messages:
                try:
                    await self.bot.send_message(messages[0].chat.id, "❌ Failed to post your album. Try again later")
                except Exception:
                    pass

    async def _detectNSFW(self, message: Message) -> bool:
        isSafe, reason = await self.nsfwChecker.checkMessage(self.bot, message)
        if not isSafe:
            logger.warning(f"[MEDIA_GROUP] nsfw album detected from user {message.from_user.id}")
            await self.bot.send_message(
                chat_id=message.chat.id,
                text=f"<b>🔞 NSFW content detected</b>\n\nReason: {reason}\nYour post will be sent with spoilers",
                parse_mode="HTML"
            )
        return not isSafe

    async def _promptUser(self, messages: List[Message], userId: int) -> None:
        chatId, firstId = messages[0].chat.id, messages[0].message_id
        await NSFWDataManager(self.redis).store(chatId, firstId, userId, messages)
        await self.bot.send_message(
            chat_id=chatId,
            text=(
                "<b>📸 Media detected</b>\n\n"
                "Do these media files contain NSFW/Sensitive content?\n"
                "Marking as NSFW will add spoiler to all images"
            ),
            parse_mode="HTML",
            reply_markup=buildNSFWPromptKeyboard(firstId)
        )

    async def sendToChannel(
        self,
        messages: List[Message],
        user,
        hasSpoiler: bool = False,
        addWarning: bool = False,
        mappingRepo: Optional[MessageMappingRepository] = None,
    ) -> None:
        mappingRepo = mappingRepo or self.messageMappingRepo
        first = messages[0]
        replyParams, consumedLink = await ReplyResolverService(self.bot, mappingRepo).resolveWithLink(
            first, settings.CHANNEL_ID
        )

        firstText = buildTextOverride(first, consumedLink, addWarning) or originalText(first)
        if user.alias:
            separator = "\n✍️ " if firstText.text else "✍️ "
            aliasEntity = MessageEntity(type="italic", offset=0, length=utf16Len(user.alias))
            firstText = TextContent(*joinText(
                (firstText.text, firstText.entities), (separator, None), (user.alias, [aliasEntity])
            ))

        media = [
            self._toInputMedia(message, firstText if idx == 0 else originalText(message), hasSpoiler)
            for idx, message in enumerate(messages)
        ]
        media = [item for item in media if item]
        if not media:
            raise ValueError("no valid media items found to send in group")

        params = {"chat_id": settings.CHANNEL_ID, "media": media}
        if replyParams:
            params["reply_parameters"] = replyParams
        try:
            sentMessages = await self.bot.send_media_group(**params)
        except TelegramAPIError as e:
            if not replyParams:
                raise
            logger.warning(f"[MEDIA_GROUP] send failed with reply params ({e}), retrying without")
            params.pop("reply_parameters")
            sentMessages = await self.bot.send_media_group(**params)
        logger.info(f"[MEDIA_GROUP] sent {len(sentMessages)} items")

        for message, sentMessage in zip(messages, sentMessages):
            await MappingUtil.createAndLog(
                mappingRepo,
                userId=user.id,
                userChatId=message.chat.id,
                userMessageId=message.message_id,
                channelChatId=sentMessage.chat.id,
                channelMessageId=sentMessage.message_id
            )

        keyboard = buildMessageActionsKeyboard(sentMessages[0].message_id, canEdit=False)
        confirmText = "😘😍 Message sent"
        confirmText += " with 😍NSFW😍 spoilers 🔞" if hasSpoiler else " to the channel 😚☺️😽"
        try:
            await self.bot.send_message(
                chat_id=first.chat.id,
                text=confirmText,
                reply_parameters=ReplyParameters(message_id=sentMessages[0].message_id, chat_id=settings.CHANNEL_ID),
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"[MEDIA_GROUP] cross-chat reply failed: {e}, sending without")
            await self.bot.send_message(chat_id=first.chat.id, text=confirmText, reply_markup=keyboard)

        if len(sentMessages) > 1:
            siblingIds = [message.message_id for message in sentMessages[1:]]
            await self.redis.setex(
                f"media_group_siblings:{sentMessages[0].message_id}",
                604800,  # 7 days
                json.dumps(siblingIds)
            )

    @staticmethod
    def _toInputMedia(message: Message, text: TextContent, forceSpoiler: bool):
        caption = {"caption": text.text or None, "caption_entities": text.entities, "parse_mode": None}
        spoiler = forceSpoiler or bool(message.has_media_spoiler)
        if message.photo:
            return InputMediaPhoto(
                media=message.photo[-1].file_id, has_spoiler=spoiler,
                show_caption_above_media=message.show_caption_above_media, **caption
            )
        if message.video:
            return InputMediaVideo(
                media=message.video.file_id, has_spoiler=spoiler,
                show_caption_above_media=message.show_caption_above_media, **caption
            )
        if message.document:
            return InputMediaDocument(media=message.document.file_id, **caption)
        if message.audio:
            return InputMediaAudio(media=message.audio.file_id, **caption)
        logger.warning(f"[MEDIA_GROUP] message {message.message_id} has no album-compatible media, skipping")
        return None
