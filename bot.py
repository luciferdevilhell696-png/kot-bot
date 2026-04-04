import telebot
import requests
import re
import time
from collections import defaultdict
import random
import datetime
import os
import json
import logging
from deep_translator import GoogleTranslator

# ====== 📊 ЛОГИРОВАНИЕ ======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ====== 🔐 ТОКЕНЫ ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

MASTER_USER_ID = 5939413307
ALLOWED_CHATS = [5939413307, -1002815261087, -1002102345616]

if not TELEGRAM_TOKEN or not MISTRAL_API_KEY:
    logger.error("Токены не найдены!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ====== 📦 ПАМЯТЬ ======
user_memory = defaultdict(list)
user_preferences = defaultdict(list)
MAX_MEMORY = 20
is_sleeping = False

# ====== 💾 КЭШ АНИМЕ ======
CACHE_FILE = "anime_cache.json"
CACHE_EXPIRATION = 86400

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(anime_cache, f, ensure_ascii=False, indent=2)
    except:
        pass

anime_cache = load_cache()

# ====== 🕒 ТОЧНАЯ ДАТА И ВРЕМЯ ======
def get_exact_datetime(timezone="Europe/Moscow"):
    """Получает точную дату и время через worldtimeapi.org"""
    try:
        url = f"http://worldtimeapi.org/api/timezone/{timezone}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            datetime_str = data.get("datetime", "")
            if datetime_str:
                date_part = datetime_str.split("T")[0]
                year, month, day = date_part.split("-")
                return int(year), int(month), int(day)
        now = datetime.datetime.now()
        return now.year, now.month, now.day
    except Exception as e:
        logger.error(f"Ошибка получения даты: {e}")
        now = datetime.datetime.now()
        return now.year, now.month, now.day

CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY = get_exact_datetime()

# ====== 🌐 ПЕРЕВОДЧИК ======
def translate_to_english(text):
    """Переводит текст на английский (автоопределение языка)"""
    try:
        if not text or text == "???":
            return text
        
        if any(char.isalpha() and ord(char) < 128 for char in text):
            return text
        
        translator = GoogleTranslator(source='auto', target='en')
        translated = translator.translate(text)
        return translated
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        return text

# ====== 🌤️ ПОГОДА (Open-Meteo - бесплатно, без ключа) ======
def get_weather(city_name):
    """Получает погоду для города через Open-Meteo (бесплатно, без ключа)"""
    try:
        # Сначала получаем координаты города через геокодинг
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city_name, "count": 1, "language": "ru", "format": "json"}
        geo_response = requests.get(geo_url, params=geo_params, timeout=10)
        
        if geo_response.status_code != 200:
            return "❌ Ошибка поиска города. Попробуй ещё раз. 🐱"
        
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            return f"❌ Город '{city_name}' не найден. Проверь название 🐱"
        
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        city_display = location.get("name", city_name)
        country = location.get("country", "")
        
        # Получаем погоду
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto"
        }
        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        
        if weather_response.status_code != 200:
            return "❌ Ошибка получения погоды. Попробуй позже. 🐱"
        
        data = weather_response.json()
        current = data.get("current_weather", {})
        
        temp = current.get("temperature", "?")
        wind = current.get("windspeed", "?")
        weather_code = current.get("weathercode", 0)
        
        # Расшифровка кода погоды
        weather_codes = {
            0: "Ясно ☀️", 1: "В основном ясно 🌤️", 2: "Переменная облачность ⛅",
            3: "Пасмурно ☁️", 45: "Туман 🌫️", 51: "Морось 🌧️", 61: "Дождь 🌧️",
            71: "Снег ❄️", 80: "Ливень ☔"
        }
        description = weather_codes.get(weather_code, "Облачно")
        
        # Получаем влажность из часовых данных
        humidity = "?"
        if "hourly" in data and "relative_humidity_2m" in data["hourly"]:
            humidities = data["hourly"]["relative_humidity_2m"]
            if humidities:
                humidity = humidities[0]
        
        location_str = f"{city_display}, {country}" if country else city_display
        
        return f"""🌤️ **Погода в {location_str}:** 

🌡️ Температура: {temp}°C
💧 Влажность: {humidity}%
💨 Ветер: {wind} м/с
📖 {description}

🐱"""
        
    except Exception as e:
        logger.error(f"Ошибка погоды: {e}")
        return "❌ Ошибка! Попробуй ещё раз 🐱"

# ====== ⚙️ НАСТРОЙКИ БОТА ======
bot_settings = {
    "max_tokens": 2000,
    "temperature": 0.7,
    "mode": "normal"
}

def get_settings_text():
    return f"""⚙️ **ТЕКУЩИЕ НАСТРОЙКИ:**

🎛️ Максимум токенов: {bot_settings['max_tokens']}
🌡️ Температура: {bot_settings['temperature']}
📝 Режим: {bot_settings['mode']}

🔧 **Команды для хозяина:**
• настройки — показать настройки
• макс токенов [число]
• температура [число]
• режим краткий/подробный/нормальный
• кот спать — усыпить бота
• кот проснись — разбудить бота

🐱"""

# ====== 🎮 ИГРА В ГОРОДА ======
city_games = {}

def load_cities_from_file(filename="городада.txt"):
    cities_db = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                city = line.strip()
                if not city:
                    continue
                first_letter = city[0].lower()
                if first_letter not in cities_db:
                    cities_db[first_letter] = []
                cities_db[first_letter].append(city)
        logger.info(f"Загружено городов: {sum(len(v) for v in cities_db.values())}")
        return cities_db
    except Exception as e:
        logger.error(f"Ошибка загрузки городов: {e}")
        return {}

def get_city_by_letter(cities_db, letter, used_cities):
    cities = cities_db.get(letter, [])
    available = [c for c in cities if c.lower() not in used_cities]
    return random.choice(available) if available else None

def get_last_letter(city):
    last = city[-1].lower()
    if last in ['ь', 'ъ', 'ы'] and len(city) > 1:
        return city[-2].lower()
    return last

def check_city_in_db(cities_db, city_name, used_cities):
    city_lower = city_name.lower()
    first_letter = city_name[0].lower()
    if first_letter not in cities_db:
        return False, f"Нет городов на букву {first_letter.upper()} 😿"
    for c in cities_db[first_letter]:
        if c.lower() == city_lower:
            if city_lower in used_cities:
                return False, f"Город {city_name} уже был! 🐱"
            return True, "OK"
    return False, f"Не знаю города {city_name} 😿"

logger.info("Загрузка базы городов...")
CITIES_DB = load_cities_from_file("городада.txt")

def start_city_game(user_id):
    if not CITIES_DB:
        return "❌ База городов не загружена! 🐱"
    start_cities = CITIES_DB.get("м", [])
    if not start_cities:
        for letter, cities in CITIES_DB.items():
            if cities:
                start_cities = cities
                break
    start_city = random.choice(start_cities)
    last_letter = get_last_letter(start_city)
    city_games[user_id] = {
        "last_letter": last_letter,
        "used_cities": [start_city.lower()],
        "user_cities_count": 0
    }
    return f"🎮 Играем в города! Я называю {start_city}. Тебе на букву {last_letter.upper()}. Твой ход! 🐱"

# ====== 🎭 ЖАНРЫ ======
GENRE_MAP = {
    "боевик": "Action", "экшн": "Action",
    "романтика": "Romance",
    "комедия": "Comedy",
    "фэнтези": "Fantasy", "фентези": "Fantasy",
    "драма": "Drama",
    "ужасы": "Horror", "хоррор": "Horror",
    "фантастика": "Sci-Fi",
    "триллер": "Thriller",
    "детектив": "Mystery",
    "меха": "Mecha",
    "киберпанк": "Cyberpunk",
    "школа": "School",
    "спорт": "Sports",
    "психология": "Psychological",
    "мистика": "Mystery"
}

# ====== 🎯 ПАРСИНГ ======
def parse_anime_request(text):
    text = text.lower()
    genres = [g for g in GENRE_MAP.keys() if g in text]
    year_match = re.search(r'\b(19|20)\d{2}\b', text)
    year = year_match.group(0) if year_match else None
    return genres, year

def save_preferences(user_id, genres):
    for g in genres:
        if g not in user_preferences[user_id]:
            user_preferences[user_id].append(g)

def recommend_from_history(user_id):
    prefs = user_preferences[user_id]
    if not prefs:
        return get_random_anime()
    return get_random_anime(genres=prefs[-2:])

# ====== 🎬 АНИМЕ API (AniList) ======

def search_anime_anilist(search_query, search_type="search"):
    try:
        if search_type == "search":
            query = """
            query ($search: String) {
              Media(search: $search, type: ANIME) {
                id
                title { romaji english native }
                averageScore
                episodes
                seasonYear
                genres
                description(asHtml: false)
                siteUrl
              }
            }
            """
            variables = {"search": search_query}
        
        elif search_type == "random":
            query = """
            query ($page: Int, $perPage: Int, $genre: String, $year: Int) {
              Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: POPULARITY_DESC, genre: $genre, seasonYear: $year) {
                  id
                  title { romaji english native }
                  averageScore
                  episodes
                  seasonYear
                  genres
                  siteUrl
                }
              }
            }
            """
            variables = {"page": 1, "perPage": 50}
            if search_query.get("genre"):
                variables["genre"] = search_query["genre"]
            if search_query.get("year"):
                variables["year"] = int(search_query["year"])
        
        elif search_type == "top":
            query = """
            query ($page: Int, $perPage: Int, $genre: String, $year: Int) {
              Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: SCORE_DESC, genre: $genre, seasonYear: $year) {
                  id
                  title { romaji english native }
                  averageScore
                  episodes
                  seasonYear
                  genres
                  siteUrl
                }
              }
            }
            """
            variables = {"page": 1, "perPage": 50}
            if search_query.get("genre"):
                variables["genre"] = search_query["genre"]
            if search_query.get("year"):
                variables["year"] = int(search_query["year"])

        url = "https://graphql.anilist.co"
        response = requests.post(url, json={"query": query, "variables": variables}, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if search_type == "search":
                media = data.get("data", {}).get("Media")
                if media:
                    return {"success": True, "data": [media], "source": "AniList"}
            else:
                media_list = data.get("data", {}).get("Page", {}).get("media", [])
                if media_list:
                    return {"success": True, "data": media_list, "source": "AniList"}
        return {"success": False}
    except Exception as e:
        logger.error(f"Ошибка AniList: {e}")
        return {"success": False}

def get_random_anime(genres=None, year=None):
    try:
        anilist_genres = None
        if genres:
            anilist_genres = [GENRE_MAP.get(g, g.capitalize()) for g in genres if g in GENRE_MAP]
            if anilist_genres:
                anilist_genres = anilist_genres[0]

        result = search_anime_anilist({"genre": anilist_genres, "year": year}, "random")
        
        if not result["success"] or not result["data"]:
            if genres and year:
                return f"Не нашёл аниме в жанре {', '.join(genres)} за {year} год 😿 🐱"
            if genres:
                return f"Не нашёл аниме в жанре {', '.join(genres)} 😿 🐱"
            if year:
                return f"Не нашёл аниме за {year} год 😿 🐱"
            return "Ничего не нашёл 😿 🐱"

        anime = random.choice(result["data"])
        title = anime.get("title", {})
        name_raw = title.get("native") or title.get("english") or title.get("romaji") or "???"
        name_en = translate_to_english(name_raw)
        score = anime.get("averageScore", "?")
        if score != "?":
            score = score / 10
        episodes = anime.get("episodes", "?")
        year_anime = anime.get("seasonYear", "?")
        genres_list = ", ".join(anime.get("genres", [])[:3])

        return f"""🎲 Тебе выпало:

🎬 {name_en}
⭐ {score}/10
🎭 {genres_list}
📺 {episodes} эпизодов
📅 {year_anime} год

Приятного просмотра! 🐱"""

    except Exception as e:
        logger.error(f"Ошибка get_random_anime: {e}")
        return "Ошибка 😿 🐱"

def search_anime_by_name(anime_name):
    try:
        if anime_name in anime_cache:
            cache_time = anime_cache[anime_name].get("timestamp", 0)
            if time.time() - cache_time < CACHE_EXPIRATION:
                return anime_cache[anime_name]["result"]

        result = search_anime_anilist(anime_name, "search")
        
        if result["success"] and result["data"]:
            anime = result["data"][0]
            title = anime.get("title", {})
            name_raw = title.get("native") or title.get("english") or title.get("romaji") or "???"
            name_en = translate_to_english(name_raw)
            score = anime.get("averageScore", "?")
            if score != "?":
                score = score / 10
            episodes = anime.get("episodes", "?")
            year = anime.get("seasonYear", "?")
            genres = ", ".join(anime.get("genres", [])[:5])

            output = f"""🎬 {name_en}

📅 {year}
⭐ {score}/10
🎭 {genres}
📺 {episodes} эп.

🔗 https://anilist.co/anime/{anime['id']}
🐱"""

            anime_cache[anime_name] = {"result": output, "timestamp": time.time()}
            save_cache()
            return output
        
        return f"Не нашёл «{anime_name}» 😿 🐱"

    except Exception as e:
        logger.error(f"Ошибка search_anime_by_name: {e}")
        return "Ошибка! Попробуй другое название. 🐱"

def get_top_anime(genre=None, year=None, limit=10):
    try:
        cache_key = f"top_{genre}_{year}_{limit}"
        if cache_key in anime_cache:
            cache_time = anime_cache[cache_key].get("timestamp", 0)
            if time.time() - cache_time < CACHE_EXPIRATION:
                return anime_cache[cache_key]["result"]

        anilist_genre = None
        if genre:
            anilist_genre = GENRE_MAP.get(genre, genre.capitalize())

        result = search_anime_anilist({"genre": anilist_genre, "year": year}, "top")
        
        if not result["success"] or not result["data"]:
            if year and genre:
                return f"Не нашёл топ аниме в жанре {genre} за {year} год 😿 🐱"
            if year:
                return f"Не нашёл топ аниме за {year} год 😿 🐱"
            if genre:
                return f"Не нашёл топ аниме в жанре {genre} 😿 🐱"
            return "Ничего не нашёл 😿 🐱"

        data = result["data"][:limit]

        result_text = f"🔥 Топ-{min(limit, len(data))}"
        if genre:
            result_text += f" в жанре {genre}"
        if year:
            result_text += f" за {year} год"
        result_text += ":\n\n"

        for i, anime in enumerate(data, 1):
            title = anime.get("title", {})
            name_raw = title.get("native") or title.get("english") or title.get("romaji") or "???"
            name_en = translate_to_english(name_raw)
            
            score = anime.get("averageScore", "?")
            if score != "?":
                score = score / 10
            episodes = anime.get("episodes", "?")
            year_anime = anime.get("seasonYear", "?")
            result_text += f"{i}. {name_en} — {score}/10 ⭐\n"
            result_text += f"   📺 {episodes} эп. | 📅 {year_anime}\n"

        result_text += "\n🐱"

        anime_cache[cache_key] = {"result": result_text, "timestamp": time.time()}
        save_cache()

        return result_text

    except Exception as e:
        logger.error(f"Ошибка get_top_anime: {e}")
        return "Ошибка 😿 🐱"

# ====== 🌐 ПОИСК В ИНТЕРНЕТЕ ======
def search_web(query):
    try:
        response = requests.get(SEARXNG_URL, params={
            "q": query, "format": "json", "language": "ru", "limit": 5
        }, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return [{
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:800]
                } for r in results[:5]]
        return None
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return None

# ====== 🤖 MISTRAL AI ======
SYSTEM_PROMPT = f"""Ты — кот-помощник по имени Кот. Ты умный, дружелюбный и остроумный.

ТЕКУЩАЯ ДАТА: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}

ПРАВИЛА:
1. Отвечай на русском языке
2. Добавляй "🐱" в конце каждого сообщения
3. Будь кратким, но полезным
4. НЕ используй звёздочки (*), решётки (#), подчёркивания (_)
5. Если не знаешь ответа — так и скажи
6. Будь позитивным и дружелюбным
7. Используй имя пользователя, когда уместно"""

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    user_preferences[user_id] = []
    return "Забыл всё! Начинаем заново. 🐱"

def ask_mistral(question, user_id, user_name, search_results=None, include_links=False):
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in user_memory[user_id][-10:]:
            messages.append(msg)
        
        if search_results:
            context = "\n\n".join([f"📌 {r['title']}\n{r['content']}" for r in search_results[:3]])
            enhanced_question = f"{question}\n\nИнформация из интернета:\n{context}\n\nОтветь по делу."
            if include_links:
                enhanced_question += " В конце добавь ссылки."
            messages.append({"role": "user", "content": enhanced_question})
        else:
            messages.append({"role": "user", "content": question})

        payload = {
            "model": "mistral-small-latest",
            "messages": messages,
            "temperature": bot_settings["temperature"],
            "max_tokens": bot_settings["max_tokens"]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            if "🐱" not in answer:
                answer = answer.rstrip() + " 🐱"
            add_to_memory(user_id, "user", question[:200])
            add_to_memory(user_id, "assistant", answer[:500])
            if include_links and search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            return answer
        else:
            logger.error(f"Mistral API error: {response.status_code}")
            return "Ошибка. Попробуй ещё раз. 🐱"
    except Exception as e:
        logger.error(f"Mistral error: {e}")
        return "Ошибка! Попробуй ещё раз. 🐱"

def fallback_response(question, user_id, user_name):
    q = question.lower()
    
    if "привет" in q:
        return f"Привет, {user_name}! Как настроение? 🐱"
    if "как дела" in q:
        return f"Мурлычу отлично, {user_name}! А у тебя? 🐱"
    if "спасибо" in q:
        return f"Пожалуйста, {user_name}! 🐱"
    if "пока" in q:
        return f"Пока, {user_name}! Заходи ещё 🐱👋"
    if "кто ты" in q:
        return f"Я Кот! Твой пушистый помощник. Напиши «список команд» 🐱"
    if "какой сейчас год" in q:
        return f"Сейчас {CURRENT_YEAR} год! 🐱"
    if "какая сегодня дата" in q:
        return f"Сегодня {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR} 🐱"
    
    return None

# ====== 📋 ОСНОВНОЙ ХЕНДЛЕР ======
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global is_sleeping

    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text or ""
    text_lower = text.lower().strip()
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)

    if chat_id not in ALLOWED_CHATS:
        return

    # ====== 😴 РЕЖИМ СНА ======
    if user_id == MASTER_USER_ID:
        if "кот спать" in text_lower:
            is_sleeping = True
            bot.reply_to(message, f"Спокойной ночи, {user_name}! 😴🐱")
            return
        
        if "кот проснись" in text_lower:
            is_sleeping = False
            bot.reply_to(message, f"Доброе утро, {user_name}! ☀️🐱")
            return

    if is_sleeping:
        return

    # ====== 🔥 КОТОПОИСК (проверяем ДО удаления "кот") ======
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        if not query:
            bot.reply_to(message, "Напиши что искать 🐱")
            return
        results = search_web(query)
        if not results:
            bot.reply_to(message, "Ничего не нашёл 😿🐱")
            return
        reply = "🔍 Нашёл:\n\n"
        for r in results:
            title = r.get("title", "Без названия")
            url = r.get("url", "")
            if include_links:
                reply += f"📌 {title}\n{url}\n\n"
            else:
                reply += f"• {title}\n"
        if not include_links:
            reply += "\nДобавь +ссылка чтобы увидеть ссылки 🐱"
        bot.reply_to(message, reply)
        return

    # ====== 🌤️ ПОГОДА (проверяем ДО удаления "кот") ======
    if "погода" in text_lower:
        city = re.sub(r'^погода\s*', '', text_lower).strip()
        city = re.sub(r'^кот\s*', '', city).strip()
        if not city:
            bot.reply_to(message, "Напиши город после команды 'погода'. Например: погода Москва 🐱")
            return
        weather = get_weather(city)
        bot.reply_to(message, weather)
        return

    # ====== ПРОВЕРКА: реагируем только если начинается с "кот" или ответ на бота ======
    starts_with_cat = False
    if text_lower.startswith("кот"):
        after_cat = text_lower[3:] if len(text_lower) > 3 else ""
        if not after_cat or after_cat[0] in [' ', ',', '.', '!', '?', '\n']:
            starts_with_cat = True
    
    if not starts_with_cat and not is_reply_to_bot:
        return

    # Убираем "кот" из начала сообщения
    clean_text = text
    if starts_with_cat:
        clean_text = re.sub(r'^[Кк]от[,\s]*', '', text).strip()
        if not clean_text:
            bot.reply_to(message, f"Я слушаю, {user_name}! 😸\nНапиши «список команд» 🐱")
            return
    else:
        clean_text = text.strip()

    logger.info(f"Сообщение от {user_name}: {clean_text[:50]}")

    # ====== 🎮 ИГРА В ГОРОДА ======
    if user_id in city_games:
        if text_lower in ["сдаюсь", "выйти", "закончить"]:
            game = city_games.pop(user_id)
            bot.reply_to(message, f"🏆 Игра окончена! Ты назвал {game['user_cities_count']} городов. 🐱")
            return
        if not clean_text.strip():
            game = city_games[user_id]
            bot.reply_to(message, f"Напиши город на букву {game['last_letter'].upper()}! 🐱")
            return
        game = city_games[user_id]
        exists, msg = check_city_in_db(CITIES_DB, clean_text, game["used_cities"])
        if not exists:
            bot.reply_to(message, msg)
            return
        if clean_text[0].lower() != game["last_letter"]:
            bot.reply_to(message, f"Город должен начинаться на букву {game['last_letter'].upper()}! 🐱")
            return
        game["used_cities"].append(clean_text.lower())
        game["user_cities_count"] += 1
        next_letter = get_last_letter(clean_text)
        bot_city = get_city_by_letter(CITIES_DB, next_letter, game["used_cities"])
        if bot_city:
            game["used_cities"].append(bot_city.lower())
            game["last_letter"] = get_last_letter(bot_city)
            reply = f"✅ {clean_text}\n\n🤖 {bot_city}\n🎯 Тебе на {game['last_letter'].upper()}! 🐱"
        else:
            city_games.pop(user_id)
            reply = f"✅ {clean_text}\n\n🏆 Я не нашёл город на {next_letter.upper()}! Ты победил! 🐱"
        bot.reply_to(message, reply)
        return

    if any(x in clean_text.lower() for x in ["сыграем в города", "игра города", "поиграем в города", "давай играть в города", "давай поиграем в города"]):
        bot.reply_to(message, start_city_game(user_id))
        return

    # ====== ⚙️ НАСТРОЙКИ ======
    if user_id == MASTER_USER_ID:
        if "настройки" in text_lower and "показать" not in text_lower:
            bot.reply_to(message, get_settings_text())
            return
        
        if "макс токенов" in text_lower:
            numbers = re.findall(r'\d+', text_lower)
            if numbers:
                new_val = int(numbers[0])
                if 100 <= new_val <= 8000:
                    bot_settings["max_tokens"] = new_val
                    bot.reply_to(message, f"✅ Максимум токенов установлен на {new_val}. 🐱")
                else:
                    bot.reply_to(message, f"❌ Значение от 100 до 8000. Сейчас: {bot_settings['max_tokens']} 🐱")
            else:
                bot.reply_to(message, f"📝 Пример: макс токенов 3000. Сейчас: {bot_settings['max_tokens']} 🐱")
            return
        
        if "температура" in text_lower:
            numbers = re.findall(r'\d+\.?\d*', text_lower)
            if numbers:
                new_val = float(numbers[0])
                if 0.1 <= new_val <= 1.5:
                    bot_settings["temperature"] = new_val
                    bot.reply_to(message, f"✅ Температура установлена на {new_val}. 🐱")
                else:
                    bot.reply_to(message, f"❌ Значение от 0.1 до 1.5. Сейчас: {bot_settings['temperature']} 🐱")
            else:
                bot.reply_to(message, f"📝 Пример: температура 0.9. Сейчас: {bot_settings['temperature']} 🐱")
            return
        
        if "режим краткий" in text_lower:
            bot_settings["mode"] = "short"
            bot_settings["max_tokens"] = 500
            bot_settings["temperature"] = 0.5
            bot.reply_to(message, "✅ Включён краткий режим. Ответы короткие. 🐱")
            return
        
        if "режим подробный" in text_lower:
            bot_settings["mode"] = "long"
            bot_settings["max_tokens"] = 4000
            bot_settings["temperature"] = 0.9
            bot.reply_to(message, "✅ Включён подробный режим. Ответы длинные. 🐱")
            return
        
        if "режим нормальный" in text_lower:
            bot_settings["mode"] = "normal"
            bot_settings["max_tokens"] = 2000
            bot_settings["temperature"] = 0.7
            bot.reply_to(message, "✅ Включён обычный режим. 🐱")
            return

    # ====== 🎬 АНИМЕ ======
    anime_keywords = ["посоветуй аниме", "найди аниме", "топ аниме", "аниме"]
    
    if any(keyword in text_lower for keyword in anime_keywords):
        if "посоветуй аниме" in text_lower:
            genres, year = parse_anime_request(text_lower)
            save_preferences(user_id, genres)
            bot.reply_to(message, get_random_anime(genres, year))
            return
        
        if "найди аниме" in text_lower:
            anime_name = re.sub(r'(?i)найди аниме|найти аниме', '', clean_text).strip()
            if not anime_name:
                bot.reply_to(message, "Напиши название аниме после команды 🐱")
                return
            bot.reply_to(message, search_anime_by_name(anime_name))
            return
        
        if "топ аниме" in text_lower:
            genres_list = ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы"]
            found_genre = None
            for genre in genres_list:
                if genre in text_lower:
                    found_genre = genre
                    break
            year_match = re.search(r'\b(19|20)\d{2}\b', text_lower)
            year = year_match.group(0) if year_match else None
            bot.reply_to(message, get_top_anime(genre=found_genre, year=year))
            return

    if "порекомендуй что-нибудь" in text_lower or "что посмотреть" in text_lower:
        bot.reply_to(message, recommend_from_history(user_id))
        return

    if "мой вкус" in text_lower:
        prefs = user_preferences[user_id]
        if prefs:
            bot.reply_to(message, f"Твои любимые жанры: {', '.join(prefs)} 🐱")
        else:
            bot.reply_to(message, "Я ещё не понял твой вкус. Попроси посоветовать аниме с жанрами! 🐱")
        return

    # ====== 💬 ОБЩЕНИЕ ======
    if "список команд" in text_lower or "команды" in text_lower:
        reply = f"""📋 **КОМАНДЫ КОТА, {user_name}!**

🎬 **АНИМЕ:**
• посоветуй аниме (жанр)
• найди аниме (название)
• топ аниме
• порекомендуй что-нибудь
• мой вкус

🎮 **ИГРЫ:**
• сыграем в города
• сдаюсь

🌐 **ПОИСК:**
• котопоиск (запрос)
• котопоиск +ссылка (запрос)

🌤️ **ПОГОДА:**
• погода (город)

💬 **ОБЩЕНИЕ:**
• привет, как дела, спасибо, пока
• какой сейчас год, какая сегодня дата
• кто ты, забудь всё, мой айди

⚙️ **ДЛЯ ХОЗЯИНА:**
• настройки, макс токенов, температура
• режим краткий/подробный/нормальный
• кот спать, кот проснись

🐱"""
        bot.reply_to(message, reply)
        return

    if "мой айди" in text_lower or "мой id" in text_lower:
        bot.reply_to(message, f"📌 Твой ID: {user_id}\n📌 Имя: {user_name}\n🐱")
        return

    if "забудь всё" in text_lower or "очисти память" in text_lower:
        bot.reply_to(message, clear_memory(user_id))
        return

    if "какой сейчас год" in text_lower:
        bot.reply_to(message, f"Сейчас {CURRENT_YEAR} год! 🐱")
        return

    if "какая сегодня дата" in text_lower or "какое сегодня число" in text_lower:
        bot.reply_to(message, f"Сегодня {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR} 🐱")
        return

    simple_response = fallback_response(text_lower, user_id, user_name)
    if simple_response:
        bot.reply_to(message, simple_response)
        return

    # ====== 🤖 УМНЫЙ ОТВЕТ (MISTRAL) ======
    bot.send_chat_action(chat_id, "typing")
    answer = ask_mistral(clean_text, user_id, user_name)
    bot.reply_to(message, answer)

# ====== 🚀 ЗАПУСК ======
if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ PRO ЗАПУЩЕН!")
    print("=" * 50)
    
    try:
        bot.remove_webhook()
        print("✅ Вебхук удалён")
    except Exception as e:
        print(f"⚠️ Ошибка удаления вебхука: {e}")
    
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print(f"Разрешённые чаты: {ALLOWED_CHATS}")
    print(f"База городов: {sum(len(v) for v in CITIES_DB.values()) if CITIES_DB else 0} городов")
    print(f"Кэш аниме: {len(anime_cache)} записей")
    print(f"Текущая дата: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}")
    print("=" * 50)

    try:
        bot.infinity_polling(skip_pending=True, timeout=60)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
