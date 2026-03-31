import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from db import Base
from config import settings, dbManager, redisManager
from bot import (
    private,
    callback,
    ErrorHandlerMiddleware,
    SessionMiddleware
)
from bot.handlers.settings import router as settingsRouter
from bot.handlers.group import router as groupRouter
from services import (
    RateLimiterService,
    NSFWChecker,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s :: %(name)s :: [%(levelname)s] -- %(message)s'
)
logger = logging.getLogger(__name__)

sep = '='*7

async def setCommands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="settings", description="Manage your settings"),
        BotCommand(command="anon", description="Leave an anonymous comment"),
    ]
    await bot.set_my_commands(commands)
    logger.info(f"{sep} BOT COMMANDS SET {sep}")

async def createTables():
    async with dbManager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"{sep} db tables created {sep}")

async def main():
    try:
        logger.info(f"{sep} DB INIT {sep}")
        dbManager.init()
        await createTables()
        logger.info(f"{sep} REDIS INIT {sep}")
        await redisManager.init()
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        await setCommands(bot)

        # -- singletons :: created once - live on dp - available to all handlers
        dp["nsfwChecker"] = NSFWChecker()
        dp["rateLimiter"] = RateLimiterService(redisManager.client)
        dp["redis"] = redisManager.client

        # -- per-request SessionMiddleware opens a DB session and builds
        # session scoped services each update reading singletons from dp
        dp.message.middleware(SessionMiddleware())
        dp.callback_query.middleware(SessionMiddleware())

        dp.message.middleware(ErrorHandlerMiddleware())
        dp.callback_query.middleware(ErrorHandlerMiddleware())

        dp.include_router(settingsRouter)
        dp.include_router(groupRouter)
        dp.include_router(private.router)
        dp.include_router(callback.router)
        logger.info(f"{sep} BOT STARTED {sep}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"OH SHIT WE FUCKED: {e}", exc_info=True)
        raise
    finally:
        logger.info("shutting down...")
        await dbManager.close()
        await redisManager.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("bot stopped by user")
    except Exception as e:
        logger.error(f"bot crashed: {e}", exc_info=True)
