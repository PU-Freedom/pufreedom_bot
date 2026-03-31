from typing import Optional, Dict, Any
from aiogram.types import Message, ReplyParameters

class MessageParamsBuilder:
    """
    centralized util for building params for tg-bot api methods
    each builder method corresponds to a specific message type

    !NOTE for params: using snaking casing (variable_name)
    instead of camel casing (variableName)
    because these are passed to aiogram which uses snake casing
    naming convention
    """
    @staticmethod
    def buildBaseParams(
        chatId: int,
        replyParams: Optional[ReplyParameters] = None
    ) -> Dict[str, Any]:
        params = { "chat_id": chatId}
        if replyParams:
            params["reply_parameters"] = replyParams
        return params
    
    @staticmethod
    def addCaption(
        params: Dict[str, Any],
        message: Message,
        overrideCaption: Optional[str] = None
    ) -> None:
        if overrideCaption:
            params["caption"] = overrideCaption
            params["parse_mode"] = "HTML"
        elif message.caption:
            params["caption"] = message.caption
            params["caption_entities"] = message.caption_entities
    
    @staticmethod
    def buildPhotoParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["photo"] = message.photo[-1].file_id
        if hasSpoiler:
            params["has_spoiler"] = True
        MessageParamsBuilder.addCaption(params, message, overrideCaption)
        return params
    
    @staticmethod
    def buildVideoParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["video"] = message.video.file_id
        if hasSpoiler:
            params["has_spoiler"] = True
        MessageParamsBuilder.addCaption(params, message, overrideCaption)
        return params
    
    @staticmethod
    def buildAudioParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["audio"] = message.audio.file_id
        MessageParamsBuilder.addCaption(params, message, overrideCaption)
        return params
    
    @staticmethod
    def buildVoiceParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["voice"] = message.voice.file_id
        MessageParamsBuilder.addCaption(params, message, overrideCaption)
        return params
    
    @staticmethod
    def buildDocumentParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["document"] = message.document.file_id
        MessageParamsBuilder.addCaption(params, message, overrideCaption)
        return params
    
    @staticmethod
    def buildAnimationParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        hasSpoiler: bool = False,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["animation"] = message.animation.file_id
        if hasSpoiler:
            params["has_spoiler"] = True
        MessageParamsBuilder.addCaption(params, message, overrideCaption)
        return params
    
    @staticmethod
    def buildVideoNoteParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["video_note"] = message.video_note.file_id
        return params
    
    @staticmethod
    def buildContactParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        contact = message.contact
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["phone_number"] = contact.phone_number
        params["first_name"] = contact.first_name
        if contact.last_name:
            params["last_name"] = contact.last_name
        if contact.vcard:
            params["vcard"] = contact.vcard
        return params
    
    @staticmethod
    def buildLocationParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        location = message.location
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["latitude"] = location.latitude
        params["longitude"] = location.longitude
        if location.horizontal_accuracy is not None:
            params["horizontal_accuracy"] = location.horizontal_accuracy
        if location.live_period is not None:
            params["live_period"] = location.live_period
        if location.heading is not None:
            params["heading"] = location.heading
        if location.proximity_alert_radius is not None:
            params["proximity_alert_radius"] = location.proximity_alert_radius        
        return params
    
    @staticmethod
    def buildVenueParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        venue = message.venue
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["latitude"] = venue.location.latitude
        params["longitude"] = venue.location.longitude
        params["title"] = venue.title
        params["address"] = venue.address
        if venue.foursquare_id:
            params["foursquare_id"] = venue.foursquare_id
        if venue.foursquare_type:
            params["foursquare_type"] = venue.foursquare_type
        if venue.google_place_id:
            params["google_place_id"] = venue.google_place_id
        if venue.google_place_type:
            params["google_place_type"] = venue.google_place_type    
        return params
    
    @staticmethod
    def buildDiceParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["emoji"] = message.dice.emoji
        return params
    
    @staticmethod
    def buildGameParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["game_short_name"] = message.game.short_name
        return params
    
    @staticmethod
    def buildStickerParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["sticker"] = message.sticker.file_id
        return params
    
    @staticmethod
    def buildPollParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        **kwargs
    ) -> Dict[str, Any]:
        poll = message.poll
        params = MessageParamsBuilder.buildBaseParams(chatId, replyParams)
        params["question"] = poll.question
        params["options"] = [option.text for option in poll.options]
        params["is_anonymous"] = poll.is_anonymous
        params["allows_multiple_answers"] = poll.allows_multiple_answers
        if poll.type:
            params["type"] = poll.type
        if poll.correct_option_id is not None:
            params["correct_option_id"] = poll.correct_option_id
        if poll.explanation:
            params["explanation"] = poll.explanation
        if poll.explanation_entities:
            params["explanation_entities"] = poll.explanation_entities
        if poll.open_period is not None:
            params["open_period"] = poll.open_period
        if poll.close_date is not None:
            params["close_date"] = poll.close_date
        if poll.is_closed:
            params["is_closed"] = True
        return params
    
    @staticmethod
    def buildCopyMessageParams(
        message: Message,
        chatId: int,
        replyParams: Optional[ReplyParameters] = None,
        overrideCaption: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if message.text and overrideCaption:
            params = {
                "chat_id": chatId,
                "text": overrideCaption,
                "parse_mode": "HTML"
            }
            if replyParams:
                params["reply_parameters"] = replyParams
            return params
    
        params = {
            "chat_id": chatId,
            "from_chat_id": message.chat.id,
            "message_id": message.message_id
        }
        if replyParams:
            params["reply_parameters"] = replyParams
        return params
    