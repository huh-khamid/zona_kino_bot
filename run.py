import asyncio
import logging
import aiohttp
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
    db = Database(config.DATABASE_PATH, config.DATABASE_URL)
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

async def run_self_ping():
    """Background task to prevent Render.com free tier from sleeping."""
    if not config.KEEP_ALIVE:
        return
        
    await asyncio.sleep(20) # Wait for FastAPI to spin up
    
    url = config.WEBAPP_URL.rstrip('/')
    if not url.startswith("http") or "localhost" in url or "127.0.0.1" in url:
        logger.info("ℹ️ Anti-Sleep ping disabled for local environment (localhost).")
        return
        
    ping_url = f"{url}/health"
    logger.info(f"🔄 Render Anti-Sleep Keep-Alive active! Target: {ping_url} (every {config.PING_INTERVAL}s)")
    
    while True:
        try:
            await asyncio.sleep(config.PING_INTERVAL)
            async with aiohttp.ClientSession() as session:
                async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info("💓 Anti-Sleep ping sent successfully.")
                    else:
                        logger.warning(f"⚠️ Anti-Sleep ping returned HTTP {resp.status}")
        except Exception as e:
            logger.debug(f"Anti-Sleep ping exception: {e}")

async def main():
    logger.info("==========================================")
    logger.info("🎬 Starting Telegram Cinema Bot + WebApp")
    logger.info("==========================================")
    
    # Run FastAPI server, Telegram Bot and Anti-Sleep pinger concurrently
    await asyncio.gather(
        run_fastapi(),
        run_bot(),
        run_self_ping()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Cinema application stopped.")
