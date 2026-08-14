import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # List of admin telegram IDs (comma separated string in .env -> list of ints)
    _admin_ids_raw: str = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS: List[int] = [
        int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
    ]
    
    # Payment & Currency details (Uzbek Sums)
    CURRENCY_SYMBOL: str = os.getenv("CURRENCY_SYMBOL", "сум")
    SUBSCRIPTION_PRICE: int = int(os.getenv("SUBSCRIPTION_PRICE", "25000")) # 25,000 UZS
    SUBSCRIPTION_DAYS: int = int(os.getenv("SUBSCRIPTION_DAYS", "30")) # 30 days
    CARD_NUMBER: str = os.getenv("CARD_NUMBER", "8600 0000 0000 0000")
    CARD_BANK: str = os.getenv("CARD_BANK", "Uzcard / Humo")
    CARD_HOLDER: str = os.getenv("CARD_HOLDER", "Имя Получателя")
    
    # WebApp URL (Auto-detected on Render.com or configured manually in .env)
    WEBAPP_URL: str = os.getenv("RENDER_EXTERNAL_URL", os.getenv("WEBAPP_URL", "http://127.0.0.1:8000"))
    
    # Cinema destination WebApp URL (Direct link to msx.zona.ms)
    CINEMA_URL: str = os.getenv("CINEMA_URL", "https://msx.zona.ms/")
    
    # Render Keep-Alive / Anti-Sleep settings
    KEEP_ALIVE: bool = os.getenv("KEEP_ALIVE", "true").lower() in ("true", "1", "yes")
    PING_INTERVAL: int = int(os.getenv("PING_INTERVAL", "600")) # 10 minutes in seconds
    
    # Database (PostgreSQL URL for Render/Supabase/Neon OR local SQLite fallback)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/cinema_bot.db")
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

config = Config()
