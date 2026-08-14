import os
import aiohttp
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from bot.config import config
from bot.database import Database

app = FastAPI(title="Telegram Cinema WebApp", version="1.0.0")

# Enable CORS for Telegram WebApp environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(config.DATABASE_PATH)

# Path to static folder
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Curated catalog of top trending & popular movies/shows with posters and Kinopoisk/IMDb IDs
CURATED_CATALOG: List[Dict[str, Any]] = [
    {
        "id": 1,
        "kp_id": 505898,
        "title": "Аватар: Путь воды",
        "orig_title": "Avatar: The Way of Water",
        "year": 2022,
        "category": "movie",
        "genres": ["Фантастика", "Боевик", "Приключения"],
        "rating": "7.8",
        "duration": "192 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/6201401/8e44e45d-9fb4-4537-b645-ec757303fef4/600x900",
        "backdrop": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=1200&auto=format&fit=crop",
        "description": "После принятия образа аватара солдат Джейк Салли становится предводителем народа на'ви и берет на себя миссию по защите новых друзей от корыстных бизнесменов с Земли.",
        "featured": True
    },
    {
        "id": 2,
        "kp_id": 435,
        "title": "Зеленая миля",
        "orig_title": "The Green Mile",
        "year": 1999,
        "category": "movie",
        "genres": ["Драма", "Криминал", "Фэнтези"],
        "rating": "9.1",
        "duration": "189 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1599028/4057c4b8-8208-4a0e-800e-b303fb8180da/600x900",
        "backdrop": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=1200&auto=format&fit=crop",
        "description": "Пол Эджкомб — начальник блока смертников в тюрьме «Холодная гора», каждый из узников которого однажды проходит «зеленую милю» по пути к месту казни.",
        "featured": False
    },
    {
        "id": 3,
        "kp_id": 1318972,
        "title": "Дюна: Часть вторая",
        "orig_title": "Dune: Part Two",
        "year": 2024,
        "category": "movie",
        "genres": ["Фантастика", "Приключения", "Драма"],
        "rating": "8.5",
        "duration": "166 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/10893610/b9b008d5-1033-4f90-8abf-47ec167cb4ba/600x900",
        "backdrop": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?q=80&w=1200&auto=format&fit=crop",
        "description": "Герцог Пол Атрейдес присоединяется к фременам, чтобы отомстить заговорщикам, уничтожившим его семью. Между любовью всей своей жизни и судьбой вселенной он выбирает борьбу.",
        "featured": True
    },
    {
        "id": 4,
        "kp_id": 464963,
        "title": "Игра престолов",
        "orig_title": "Game of Thrones",
        "year": 2011,
        "category": "series",
        "genres": ["Фэнтези", "Драма", "Боевик"],
        "rating": "9.0",
        "duration": "8 сезонов",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1777765/dd78edb7-932f-410a-bb48-18e4e94119d6/600x900",
        "backdrop": "https://images.unsplash.com/photo-1534447677768-be436bb09401?q=80&w=1200&auto=format&fit=crop",
        "description": "К концу подходит время благоденствия, и лето, длившееся почти десятилетие, уступает место зиме. Вокруг Железного Трона Семи Королевств зреет заговор.",
        "featured": False
    },
    {
        "id": 5,
        "kp_id": 1100777,
        "title": "Оппенгеймер",
        "orig_title": "Oppenheimer",
        "year": 2023,
        "category": "movie",
        "genres": ["Биография", "Драма", "История"],
        "rating": "8.2",
        "duration": "180 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/10893610/b13a89a0-9759-450f-aaec-4e7894a4c6a4/600x900",
        "backdrop": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1200&auto=format&fit=crop",
        "description": "История жизни американского физика-теоретика Роберта Оппенгеймера, который руководил Манхэттенским проектом — секретной разработкой ядерного оружия.",
        "featured": False
    },
    {
        "id": 6,
        "kp_id": 404900,
        "title": "Во все тяжкие",
        "orig_title": "Breaking Bad",
        "year": 2008,
        "category": "series",
        "genres": ["Криминал", "Триллер", "Драма"],
        "rating": "8.9",
        "duration": "5 сезонов",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/60787e91-7292-4d76-8800-47b29a2886f3/600x900",
        "backdrop": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?q=80&w=1200&auto=format&fit=crop",
        "description": "Школьный учитель химии Уолтер Уайт узнаёт о неизлечимой болезни и решает заняться изготовлением метамфетамина ради финансового будущего своей семьи.",
        "featured": False
    },
    {
        "id": 7,
        "kp_id": 258687,
        "title": "Интерстеллар",
        "orig_title": "Interstellar",
        "year": 2014,
        "category": "movie",
        "genres": ["Фантастика", "Драма", "Приключения"],
        "rating": "8.6",
        "duration": "169 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1600147/43b76634-93be-49e6-a5a8-d0e964b0f856/600x900",
        "backdrop": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?q=80&w=1200&auto=format&fit=crop",
        "description": "Когда засуха, пыльные бури и вымирание растений приводят человечество к продовольственному кризису, коллектив исследователей отправляется сквозь червоточину в поисках нового дома.",
        "featured": False
    },
    {
        "id": 8,
        "kp_id": 841087,
        "title": "Унесённые призраками",
        "orig_title": "Sen to Chihiro no kamikakushi",
        "year": 2001,
        "category": "anime",
        "genres": ["Аниме", "Мультфильм", "Фэнтези"],
        "rating": "8.5",
        "duration": "125 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1900788/e09e13df-b4a8-4228-a53d-2cb962c4c6a6/600x900",
        "backdrop": "https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=1200&auto=format&fit=crop",
        "description": "Девочка Тихиро вместе с родителями попадает в таинственный заброшенный город, где правит могущественная ведьма Юбаба.",
        "featured": False
    },
    {
        "id": 9,
        "kp_id": 447301,
        "title": "Начало",
        "orig_title": "Inception",
        "year": 2010,
        "category": "movie",
        "genres": ["Фантастика", "Боевик", "Триллер"],
        "rating": "8.7",
        "duration": "148 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1629397/8ef91873-1951-4043-b909-fb4d650fb369/600x900",
        "backdrop": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1200&auto=format&fit=crop",
        "description": "Кобб — талантливый вор, лучший из лучших в опасном искусстве извлечения: он крадет ценные секреты из глубин подсознания во время сна.",
        "featured": False
    },
    {
        "id": 10,
        "kp_id": 95230,
        "title": "Король Лев",
        "orig_title": "The Lion King",
        "year": 1994,
        "category": "cartoon",
        "genres": ["Мультфильм", "Мюзикл", "Драма"],
        "rating": "8.8",
        "duration": "88 мин.",
        "poster": "https://avatars.mds.yandex.net/get-kinopoisk-image/1898899/b1a80d44-0b16-43d1-a477-8c44c0bb6f18/600x900",
        "backdrop": "https://images.unsplash.com/photo-1534177616072-ef7dc120449d?q=80&w=1200&auto=format&fit=crop",
        "description": "У величественного Короля-Льва Муфасы рождается наследник по имени Симба. Ему предстоит пройти через предательство, изгнание и познать радость верной дружбы.",
        "featured": False
    }
]

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_file):
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return FileResponse(index_file)

@app.get("/api/user/status")
async def get_user_status(user_id: Optional[int] = None):
    if not user_id:
        return {"is_subscribed": False, "guest": True}
    
    user = await db.get_user(user_id)
    is_sub = await db.is_user_subscribed(user_id)
    
    return {
        "user_id": user_id,
        "is_subscribed": is_sub,
        "user": user
    }

@app.get("/api/movies/catalog")
async def get_catalog(category: Optional[str] = None):
    """Returns the catalog with optional category filtering."""
    if not category or category == "all":
        return {"movies": CURATED_CATALOG}
    
    filtered = [m for m in CURATED_CATALOG if m.get("category") == category]
    return {"movies": filtered}

@app.get("/api/movies/search")
async def search_movies(q: str = Query(..., min_length=1)):
    """Search locally in catalog, or query public online movie index."""
    query_lower = q.lower().strip()
    
    # 1. Search in local curated catalog
    results = [
        m for m in CURATED_CATALOG
        if query_lower in m["title"].lower() or query_lower in m["orig_title"].lower() or any(query_lower in g.lower() for g in m["genres"])
    ]
    
    # 2. If nothing or few results, also perform a live search query via Kinobox / KP public metadata search if network is available
    if len(results) < 3:
        try:
            # We query Kinobox search endpoint for fast accurate results
            async with aiohttp.ClientSession() as session:
                url = f"https://kinobox.tv/api/search?title={query_lower}"
                headers = {"User-Agent": "TelegramCinemaBot/1.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("results", [])[:6]:
                            kp_id = item.get("kinopoisk_id") or item.get("id")
                            # Avoid duplicates
                            if not any(r.get("kp_id") == kp_id for r in results):
                                results.append({
                                    "id": kp_id or (1000 + len(results)),
                                    "kp_id": kp_id,
                                    "title": item.get("title") or item.get("title_ru") or q,
                                    "orig_title": item.get("title_en") or "",
                                    "year": item.get("year") or 2024,
                                    "category": "movie" if not item.get("is_serial") else "series",
                                    "genres": item.get("genres", ["Кино"]),
                                    "rating": str(item.get("rating_kinopoisk") or item.get("rating_imdb") or "7.5"),
                                    "duration": f"{item.get('duration', 110)} мин.",
                                    "poster": item.get("poster") or "https://avatars.mds.yandex.net/get-kinopoisk-image/1599028/4057c4b8-8208-4a0e-800e-b303fb8180da/600x900",
                                    "backdrop": item.get("poster") or "",
                                    "description": item.get("description") or f"Смотреть «{item.get('title')}» в высоком качестве онлайн.",
                                    "featured": False
                                })
        except Exception:
            # Fallback to local match if remote API fails or times out
            pass
            
    return {"results": results}
