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
    
    # Payment details
    CARD_NUMBER: str = os.getenv("CARD_NUMBER", "2202 2000 0000 0000")
    CARD_BANK: str = os.getenv("CARD_BANK", "Т-Банк / Сбербанк")
    CARD_HOLDER: str = os.getenv("CARD_HOLDER", "Иван Иванов")
    SUBSCRIPTION_PRICE: int = int(os.getenv("SUBSCRIPTION_PRICE", "299")) # RUB
    SUBSCRIPTION_DAYS: int = int(os.getenv("SUBSCRIPTION_DAYS", "30")) # 30 days
    
    # WebApp URL (URL where FastAPI server is hosted or tunneled via ngrok/Cloudflare)
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "http://127.0.0.1:8000")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/cinema_bot.db")
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

config = Config()
