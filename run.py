import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import Database
from bot.handlers import user_handlers, admin_handlers
from webapp.server import app as fastapi_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CinemaApp")

async def run_fastapi():
    """Runs FastAPI WebApp Server via Uvicorn."""
    server_config = uvicorn.Config(
        app=fastapi_app,
        host=config.HOST,
        port=config.PORT,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(server_config)
    logger.info(f"🚀 FastAPI WebApp running at http://{config.HOST}:{config.PORT}")
    await server.serve()

async def run_bot():
    """Runs Telegram Bot Polling."""
    db = Database(config.DATABASE_PATH)
    await db.init_db()
    
    if not config.BOT_TOKEN:
        logger.warning("⚠️  BOT_TOKEN is not configured in .env! Telegram Bot will not start polling.")
        logger.info(f"🌐 You can still open and test the WebApp at http://localhost:{config.PORT}")
        # Keep task alive
        while True:
            await asyncio.sleep(3600)
        return

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    logger.info("🤖 Telegram Bot initialized and starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Telegram Bot error: {e}")
    finally:
        await bot.session.close()

async def main():
    logger.info("==========================================")
    logger.info("🎬 Starting Telegram Cinema Bot + WebApp")
    logger.info("==========================================")
    
    # Run both services concurrently in the same asyncio loop
    await asyncio.gather(
        run_fastapi(),
        run_bot()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Cinema application stopped.")
