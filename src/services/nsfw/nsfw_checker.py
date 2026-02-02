import logging
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message, PhotoSize
from nudenet import NudeDetector
from config import settings
import os
import tempfile

logger = logging.getLogger(__name__)

class NSFWChecker:
    """
    check images/videos/gifs for nsfw content using nudenet
    this service is still under developement (enforced check is disabled), 
    as of now there are inits and basic image handling logic implemented
    - TODO -- video censoring(might create cutom go module); handle stickers(YES STICKERS)
    - might make it a small ml project
    """
    def __init__(self):
        self.detector = None
        self._initialized = False
    
    def _lazyInit(self):
        if not self._initialized:
            logger.info("initting nsfw detector...")
            self.detector = NudeDetector()
            self._initialized = True
            logger.info("nsfw detector ready")
    
    async def checkMessage(self, bot: Bot, message: Message) -> Tuple[bool, Optional[str]]:
        self._lazyInit()
        if message.photo:
            return await self._checkPhoto(bot, message.photo[-1])
        elif message.video:
            return await self._checkVideo(bot, message.video.file_id)
        elif message.animation:
            return await self._checkVideo(bot, message.animation.file_id)        
        # text, stickers(FOR NOW), etc are assumed safe | # TODO -- check for stickers as well (if enforced and nsfw - dont send)
        return (True, None)
    
    async def _checkPhoto(self, bot: Bot, photo: PhotoSize) -> Tuple[bool, Optional[str]]:
        tempPath = None
        try:
            file = await bot.get_file(photo.file_id)
            tempPath = os.path.join(tempfile.gettempdir(), f"nsfw_check_{photo.file_id}.jpg")
            await bot.download_file(file.file_path, tempPath)
            results = self.detector.detect(tempPath)
            NSFW_LABELS = ['FEMALE_GENITALIA_EXPOSED', 'MALE_GENITALIA_EXPOSED', 
                          'ANUS_EXPOSED', 'FEMALE_BREAST_EXPOSED', 'BUTTOCKS_EXPOSED']
            
            for detection in results:
                label = detection['class']
                confidence = detection['score']
                if label in NSFW_LABELS and confidence > settings.NSFW_DETECTION_THRESHOLD:
                    logger.warning(f"nsfw content detected: {label} ({confidence:.2%})")
                    return (False, f"nsfw content detected: {label.lower().replace('_', ' ')}")
            return (True, None)
            
        except Exception as e:
            logger.error(f"error checking photo for nsfw: {e}", exc_info=True)
            return (True, None)
        finally:
            if tempPath and os.path.exists(tempPath):
                os.remove(tempPath)
    
    async def _checkVideo(self, bot: Bot, file_id: str) -> Tuple[bool, Optional[str]]:
        tempVideoPath = None
        tempFramePath = None
        try:
            file = await bot.get_file(file_id)
            tempVideoPath = os.path.join(tempfile.gettempdir(), f"nsfw_check_{file_id}.mp4")
            await bot.download_file(file.file_path, tempVideoPath)
            
            # TODO -- work on frame by frame nsfw check; for now disabled enforced check
            logger.info("video nsfw check skipped (not implemented)")
            return (True, None)
            
        except Exception as e:
            logger.error(f"error checking video for nsfw: {e}", exc_info=True)
            return (True, None)
        finally:
            if tempVideoPath and os.path.exists(tempVideoPath):
                os.remove(tempVideoPath)
            if tempFramePath and os.path.exists(tempFramePath):
                os.remove(tempFramePath)
