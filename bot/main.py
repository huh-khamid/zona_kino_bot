import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import db
from bot.handlers import user_handlers, admin_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def start_bot(bot_instance: Bot = None, dp_instance: Dispatcher = None):
    await db.init_db()
    logger.info("Database initialized.")

    if not config.BOT_TOKEN:
        logger.warning("BOT_TOKEN is empty! Please set BOT_TOKEN in .env file.")
        return

    bot = bot_instance or Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = dp_instance or Dispatcher(storage=MemoryStorage())

    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    logger.info("Bot starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(start_bot())
