import telebot
import requests
import re
import time
from collections import defaultdict
import random
import datetime
import json

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
MISTRAL_API_KEY = "I9PvXEOaGCsaAvjfMcPLSF0P5FrdmQJ9"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

MASTER_USER_ID = 5939413307

ALLOWED_CHATS = [
    5939413307,
    -1002815261087,
    -1002102345616,
]

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_memory = defaultdict(list)
MAX_MEMORY = 20

is_sleeping = False

bot_settings = {
    "max_tokens": 4000,
    "temperature": 0.9,
    "mode": "long"
}

city_games = {}

# ========== ДАТА И ВРЕМЯ ==========
def get_current_date():
    now = datetime.datetime.now()
    return now.year, now.month, now.day, now.hour, now.minute

CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY, CURRENT_HOUR, CURRENT_MINUTE = get_current_date()

# ========== ПОГОДА (бесплатно, без ключа) ==========
def get_weather(city_name):
    """Получает погоду через Open-Meteo API (бесплатно, без ключа)"""
    try:
        # Сначала получаем координаты города через Nominatim
        geo_url = "https://nominatim.openstreetmap.org/search"
        geo_params = {
            "q": city_name,
            "format": "json",
            "limit": 1,
            "countrycodes": "ru,by,kz,ua"
        }
        geo_headers = {"User-Agent": "KotBot/1.0"}
        
        geo_response = requests.get(geo_url, params=geo_params, headers=geo_headers, timeout=10)
        
        if geo_response.status_code != 200:
            return None, "Не могу определить координаты города"
        
        geo_data = geo_response.json()
        if not geo_data:
            return None, f"Не нашёл город «{city_name}»"
        
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        city_display = geo_data[0].get("display_name", city_name).split(",")[0]
        
        # Теперь получаем погоду по координатам
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
            "forecast_days": 1
        }
        
        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        
        if weather_response.status_code != 200:
            return None, "Не могу получить данные о погоде"
        
        weather_data = weather_response.json()
        current = weather_data.get("current", {})
        
        # Расшифровка кода погоды
        weather_codes = {
            0: "☀️ Ясно",
            1: "🌤️ Преимущественно ясно",
            2: "⛅ Частично облачно",
            3: "☁️ Облачно",
            45: "🌫️ Туман",
            48: "🌫️ Туман с изморозью",
            51: "🌧️ Легкая морось",
            53: "🌧️ Умеренная морось",
            55: "🌧️ Сильная морось",
            61: "🌧️ Небольшой дождь",
            63: "🌧️ Умеренный дождь",
            65: "🌧️ Сильный дождь",
            71: "🌨️ Небольшой снег",
            73: "🌨️ Умеренный снег",
            75: "🌨️ Сильный снег",
            80: "🌧️ Небольшой ливень",
            81: "🌧️ Умеренный ливень",
            82: "🌧️ Сильный ливень",
            95: "⛈️ Гроза",
            96: "⛈️ Гроза с градом",
            99: "⛈️ Сильная гроза с градом"
        }
        
        weather_code = current.get("weather_code", 0)
        weather_desc = weather_codes.get(weather_code, "❓ Неизвестно")
        temp = current.get("temperature_2m", "?")
        humidity = current.get("relative_humidity_2m", "?")
        wind = current.get("wind_speed_10m", "?")
        
        return {
            "city": city_display,
            "temp": temp,
            "humidity": humidity,
            "wind": wind,
            "condition": weather_desc
        }, None
        
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return None, f"Ошибка: {e}"

def format_weather_message(weather_data):
    """Форматирует данные о погоде в красивое сообщение"""
    if not weather_data:
        return None
    
    return f"""🌍 Погода в {weather_data['city']}:

🌡️ Температура: {weather_data['temp']}°C
💧 Влажность: {weather_data['humidity']}%
🌬️ Ветер: {weather_data['wind']} км/ч
{weather_data['condition']}

🐱"""

def start_city_game(user_id):
    start_cities = ["Москва", "Казань", "Сочи", "Омск", "Уфа", "Псков", "Волгоград"]
    start_city = random.choice(start_cities)
    last_letter = get_last_letter(start_city)
    
    city_games[user_id] = {
        "current_city": start_city,
        "last_letter": last_letter,
        "used_cities": [start_city.lower()]
    }
    
    return f"🎮 Играем в города! Я называю {start_city}. Тебе на букву {last_letter.upper()}. Твой ход! 🐱"

def get_last_letter(city):
    last = city[-1].lower()
    if last in ['ь', 'ъ'] and len(city) > 1:
        return city[-2].lower()
    return last

def check_city_exists(city_name):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": city_name,
            "format": "json",
            "limit": 1,
            "countrycodes": "ru,by,kz,ua"
        }
        headers = {"User-Agent": "KotBot/1.0"}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200 and response.json():
            return True, "OK"
        return False, "Не знаю такого города"
    except:
        return True, "OK"

SYSTEM_PROMPT = f"""Ты — кот-помощник по имени Кот.

ТЕКУЩАЯ ДАТА: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}

ПРАВИЛА:
1. Отвечай на русском языке
2. Добавляй "🐱" в конце
3. Будь кратким и по делу
4. Можешь использовать эмодзи 🎬🎮🌐🔥😴😸
5. НЕ используй звёздочки (*), решётки (#), подчёркивания (_) для украшения текста

ВАЖНО: Ты знаешь текущую дату. Можешь отвечать на вопросы о сегодняшней дате и текущем годе."""

def is_allowed_chat(chat_id):
    return chat_id in ALLOWED_CHATS

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    return "Забыл всё! Начинаем заново. 🐱"

def get_user_memory(user_id):
    return user_memory[user_id]

def is_master(user_id):
    return user_id == MASTER_USER_ID

def handle_settings(user_id, command):
    global bot_settings
    
    if user_id != MASTER_USER_ID:
        return None
    
    cmd_lower = command.lower()
    
    if "макс токенов" in cmd_lower or "max_tokens" in cmd_lower:
        numbers = re.findall(r'\d+', cmd_lower)
        if numbers:
            new_value = int(numbers[0])
            if 100 <= new_value <= 33000:
                bot_settings["max_tokens"] = new_value
                return f"✅ Максимум токенов установлен на {new_value}. 🐱"
            else:
                return f"❌ Значение от 100 до 33000. Сейчас: {bot_settings['max_tokens']} 🐱"
        return f"📝 Пример: кот макс токенов 3000. Сейчас: {bot_settings['max_tokens']} 🐱"
    
    if "температура" in cmd_lower or "temp" in cmd_lower:
        numbers = re.findall(r'\d+\.?\d*', cmd_lower)
        if numbers:
            new_value = float(numbers[0])
            if 0.1 <= new_value <= 1.5:
                bot_settings["temperature"] = new_value
                return f"✅ Температура установлена на {new_value}. 🐱"
            else:
                return f"❌ Значение от 0.1 до 1.5. Сейчас: {bot_settings['temperature']} 🐱"
        return f"📝 Пример: кот температура 0.9. Сейчас: {bot_settings['temperature']} 🐱"
    
    if "режим краткий" in cmd_lower or "короткий" in cmd_lower:
        bot_settings["mode"] = "short"
        bot_settings["max_tokens"] = 500
        bot_settings["temperature"] = 0.5
        return f"✅ Включён краткий режим. Ответы короткие. 🐱"
    
    if "режим подробный" in cmd_lower or "длинный" in cmd_lower:
        bot_settings["mode"] = "long"
        bot_settings["max_tokens"] = 4000
        bot_settings["temperature"] = 0.9
        return f"✅ Включён подробный режим. Ответы длинные. 🐱"
    
    if "режим нормальный" in cmd_lower or "обычный" in cmd_lower:
        bot_settings["mode"] = "normal"
        bot_settings["max_tokens"] = 2000
        bot_settings["temperature"] = 0.8
        return f"✅ Включён обычный режим. 🐱"
    
    if "показать настройки" in cmd_lower or "настройки" in cmd_lower:
        return f"""⚙️ НАСТРОЙКИ КОТА:

🎛️ Максимум токенов: {bot_settings['max_tokens']}
🌡️ Температура: {bot_settings['temperature']}
📝 Режим: {bot_settings['mode']}

🔧 КОМАНДЫ (только для хозяина):
• кот макс токенов (число) — от 100 до 33000
• кот температура (число) — от 0.1 до 1.5
• кот режим краткий — короткие ответы
• кот режим подробный — длинные ответы
• кот режим нормальный — сбросить

🐱"""
    
    return None

def search_web(query):
    try:
        print(f"🔍 Поиск: {query}")
        response = requests.get(SEARXNG_URL, params={
            "q": query,
            "format": "json",
            "language": "ru",
            "limit": 5
        }, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                print(f"✅ Найдено {len(results)} результатов")
                return [{
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:800]
                } for r in results[:5]]
        return None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None

def search_anime_by_name(anime_name):
    try:
        url = "https://shikimori.one/api/animes"
        params = {"search": anime_name, "limit": 1}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                anime = data[0]
                russian_name = anime.get("russian", anime.get("name", "Неизвестно"))
                english_name = anime.get("name", "Неизвестно")
                score = anime.get("score", "Нет")
                episodes = anime.get("episodes", "Неизвестно")
                year = anime.get("released_on", "Неизвестно")[:4] if anime.get("released_on") else "Неизвестно"
                genres = ', '.join([g['name'] for g in anime.get('genres', [])[:5]])
                description = anime.get("description", "Описание отсутствует")[:200]
                
                return f"""🎬 «{russian_name}» ({english_name})

📅 Год: {year}
⭐ Рейтинг: {score}/10
🎭 Жанры: {genres}
📺 Эпизодов: {episodes}
📖 {description}...

🔗 Подробнее: https://shikimori.one/animes/{anime['id']}
🐱"""
        return f"Не нашёл аниме «{anime_name}». Попробуй иначе. 🐱"
    except:
        return "Ошибка! Попробуй другое название. 🐱"

# Локальный список аниме на случай ошибки API
FALLBACK_ANIME = [
    ("Киберпанк: Бегущие по краю", "Cyberpunk Edgerunners", 2022, 8.5, "киберпанк, драма"),
    ("Фрирен", "Frieren", 2023, 9.0, "фэнтези, драма"),
    ("Дандадан", "Dandadan", 2024, 8.4, "комедия, экшн"),
    ("Атака Титанов", "Attack on Titan", 2013, 8.8, "экшн, драма"),
    ("Клинок, рассекающий демонов", "Demon Slayer", 2019, 8.7, "экшн, фэнтези"),
]

def get_random_anime(genre=None, year=None):
    try:
        url = "https://shikimori.one/api/animes"
        params = {"limit": 50, "order": "random"}
        
        if genre:
            genre_map = {
                "боевик": "action", "экшн": "action",
                "романтика": "romance",
                "комедия": "comedy",
                "фэнтези": "fantasy", "фентези": "fantasy",
                "драма": "drama",
                "ужасы": "horror", "хоррор": "horror",
                "фантастика": "sci-fi",
                "триллер": "thriller",
                "детектив": "detective",
                "меха": "mecha",
                "повседневность": "slice of life",
                "психологическое": "psychological",
                "историческое": "historical",
                "приключения": "adventure",
                "мистика": "mystery",
                "спорт": "sports",
                "гарем": "harem",
                "этти": "ecchi",
                "школа": "school",
                "киберпанк": "cyberpunk",
                "военное": "military"
            }
            params["genre"] = genre_map.get(genre.lower(), genre.lower())
        
        if year:
            params["season"] = f"{year}_year"
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                anime = random.choice(data)
                russian_name = anime.get("russian", anime.get("name", "Неизвестно"))
                english_name = anime.get("name", "Неизвестно")
                score = anime.get("score", "Нет")
                episodes = anime.get("episodes", "Неизвестно")
                year_anime = anime.get("released_on", "Неизвестно")[:4] if anime.get("released_on") else "Неизвестно"
                genres = ', '.join([g['name'] for g in anime.get('genres', [])[:3]])
                
                return f"""🎲 Тебе выпало:

🎬 «{russian_name}» ({english_name})
📅 {year_anime} год
⭐ {score}/10
🎭 {genres}
📺 {episodes} эпизодов

Приятного просмотра! 🐱"""
        
        # Если API не работает, используем локальный список
        anime = random.choice(FALLBACK_ANIME)
        return f"""🎲 Тебе выпало:

🎬 «{anime[0]}» ({anime[1]})
📅 {anime[2]} год
⭐ {anime[3]}/10
🎭 {anime[4]}

Приятного просмотра! 🐱"""
        
    except Exception as e:
        print(f"Ошибка: {e}")
        anime = random.choice(FALLBACK_ANIME)
        return f"""🎲 Тебе выпало:

🎬 «{anime[0]}» ({anime[1]})
📅 {anime[2]} год
⭐ {anime[3]}/10
🎭 {anime[4]}

Приятного просмотра! 🐱"""

def get_top_anime(genre=None, limit=10):
    try:
        url = "https://shikimori.one/api/animes"
        params = {"limit": limit, "order": "popularity", "status": "released"}
        
        if genre:
            genre_map = {
                "боевик": "action", "экшн": "action",
                "романтика": "romance",
                "комедия": "comedy",
                "фэнтези": "fantasy",
                "драма": "drama",
                "ужасы": "horror",
                "фантастика": "sci-fi",
                "триллер": "thriller",
                "детектив": "detective",
                "меха": "mecha",
                "повседневность": "slice of life",
                "психологическое": "psychological",
                "историческое": "historical",
                "приключения": "adventure",
                "мистика": "mystery",
                "спорт": "sports",
                "гарем": "harem",
                "этти": "ecchi",
                "школа": "school",
                "киберпанк": "cyberpunk",
                "военное": "military"
            }
            params["genre"] = genre_map.get(genre.lower(), genre.lower())
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                result = f"🔥 Топ-{limit} аниме"
                if genre:
                    result += f" в жанре {genre}:\n\n"
                else:
                    result += ":\n\n"
                
                for i, anime in enumerate(data[:limit], 1):
                    name = anime.get("russian", anime.get("name", "Неизвестно"))
                    score = anime.get("score", "?")
                    result += f"{i}. «{name}» — {score}/10 ⭐\n"
                return result + "\n🐱"
        
        # Если API не работает, используем локальный топ
        top = FALLBACK_ANIME[:limit]
        result = f"🔥 Топ-{limit} аниме:\n\n"
        for i, anime in enumerate(top, 1):
            result += f"{i}. «{anime[0]}» — {anime[3]}/10 ⭐\n"
        return result + "\n🐱"
        
    except Exception as e:
        print(f"Ошибка: {e}")
        top = FALLBACK_ANIME[:limit]
        result = f"🔥 Топ-{limit} аниме:\n\n"
        for i, anime in enumerate(top, 1):
            result += f"{i}. «{anime[0]}» — {anime[3]}/10 ⭐\n"
        return result + "\n🐱"

def ask_mistral(question, user_id, user_name, search_results=None, include_links=False):
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        history = get_user_memory(user_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for msg in history[-10:]:
            messages.append(msg)
        
        if search_results:
            context = "\n\n".join([
                f"📌 {r['title']}\n{r['content']}" for r in search_results[:3]
            ])
            if include_links:
                enhanced_question = f"{question}\n\nИнформация из интернета:\n{context}\n\nОтветь по делу. В конце добавь ссылки."
            else:
                enhanced_question = f"{question}\n\nИнформация из интернета:\n{context}\n\nОтветь по делу."
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
            return fallback_response(question, user_id, user_name, search_results, include_links)
    except Exception as e:
        print(f"Ошибка: {e}")
        return fallback_response(question, user_id, user_name, search_results, include_links)

def fallback_response(question, user_id, user_name, search_results=None, include_links=False):
    q = question.lower()
    add_to_memory(user_id, "user", question[:200])

    if "сыграем в города" in q or "игра города" in q or "города игра" in q:
        return start_city_game(user_id)

    if user_id in city_games:
        if "сдаюсь" in q or "выйти" in q or "закончить" in q:
            game = city_games.pop(user_id)
            return f"🏆 Игра окончена! Ты назвал {len(game['used_cities'])} городов. Отличная игра! 🐱"
        
        city_name = q.strip()
        game = city_games[user_id]
        
        exists, msg = check_city_exists(city_name)
        if not exists:
            return f"{msg} Попробуй другой город. 🐱"
        
        if city_name[0].lower() != game["last_letter"]:
            return f"Город должен начинаться на букву {game['last_letter'].upper()}. 🐱"
        
        if city_name.lower() in game["used_cities"]:
            return f"Город {city_name} уже был! Назови другой. 🐱"
        
        game["used_cities"].append(city_name.lower())
        next_letter = get_last_letter(city_name)
        
        if not next_letter and len(city_name) > 1:
            next_letter = city_name[-2].lower()
        
        game["last_letter"] = next_letter
        
        return f"✅ Принято! {city_name}. Теперь тебе на букву {next_letter.upper()}. Твой ход! 🐱"

    if search_results:
        if include_links:
            reply = "🔍 Вот что нашёл:\n\n"
            for r in search_results[:3]:
                reply += f"📌 {r['title']}\n{r['url']}\n\n"
            return reply + "🐱"
        else:
            reply = "🔍 Вот что нашёл:\n\n"
            for r in search_results[:3]:
                reply += f"• {r['title']}\n"
            return reply + "\nХочешь ссылки? Добавь +ссылка. 🐱"

    # ========== КОМАНДЫ ДАТЫ ==========
    if "какой сейчас год" in q or "какой год" in q or "текущий год" in q:
        return f"Сейчас {CURRENT_YEAR} год! 🐱"

    if "какая сегодня дата" in q or "сегодняшняя дата" in q or "какое сегодня число" in q:
        return f"Сегодня {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR} 🐱"

    if "какой сегодня день" in q or "день недели" in q:
        weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        weekday_num = datetime.datetime.now().weekday()
        return f"Сегодня {weekdays[weekday_num]}! 🐱"

    if "который час" in q or "сколько время" in q or "текущее время" in q or "время" in q:
        return f"Сейчас {CURRENT_HOUR:02d}:{CURRENT_MINUTE:02d} 🐱"

    # ========== КОМАНДА ПОГОДЫ ==========
    if "погода" in q:
        # Извлекаем название города
        city_match = re.search(r'погода\s+в\s+([а-яё\s-]+)', q)
        if not city_match:
            city_match = re.search(r'погода\s+([а-яё\s-]+)', q)
        
        if city_match:
            city_name = city_match.group(1).strip()
            if len(city_name) > 30:
                city_name = city_name[:30]
        else:
            return f"Напиши город, например: «Кот погода в Москве» 🐱"
        
        weather_data, error = get_weather(city_name)
        if weather_data:
            return format_weather_message(weather_data)
        else:
            return f"😿 {error} 🐱"

    if "список команд" in q or "команды" in q or "что ты умеешь" in q:
        return f"""📋 КОМАНДЫ КОТА, {user_name}:

🎬 АНИМЕ:
• Кот посоветуй (жанр) — боевик, романтика, комедия, фэнтези, драма, ужасы, триллер, детектив, меха, киберпанк и другие
• Кот посоветуй (год) — например: Кот посоветуй аниме 2010
• Кот посоветуй (жанр) (год) — например: Кот посоветуй боевик 2005
• Кот найди аниме (название) — поиск по названию
• Кот топ аниме — топ-10 популярных
• Кот топ (жанр) — топ-10 по жанру

🎮 ИГРЫ:
• Кот сыграем в города — начать игру
• (название города) — ход в игре
• сдаюсь — закончить игру

🌐 ПОИСК:
• Котопоиск (запрос) — поиск без ссылок
• Котопоиск +ссылка (запрос) — поиск со ссылками

🌤️ ПОГОДА И ДАТА:
• Кот погода в (город) — узнать погоду
• Кот какой сейчас год — текущий год
• Кот какая сегодня дата — сегодняшняя дата
• Кот который час — текущее время

💬 ОБЩЕНИЕ:
• Кот привет — поздороваться
• Кот как дела? — спросить как дела
• Кот что я говорил — показать историю
• Кот забудь всё — очистить память

Просто напиши команду! 🐱"""
    
    if "посоветуй аниме" in q:
        years = re.findall(r'\b(19|20)\d{2}\b', q)
        year = years[0] if years else None
        
        genres_list = ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы", 
                       "фантастика", "триллер", "детектив", "меха", "повседневность", 
                       "психологическое", "историческое", "приключения", "мистика", 
                       "спорт", "гарем", "этти", "школа", "киберпанк", "военное"]
        
        for genre in genres_list:
            if genre in q:
                return get_random_anime(genre=genre, year=year)
        return get_random_anime(year=year)
    
    elif "топ" in q and "аниме" in q:
        genres_list = ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы", 
                       "фантастика", "триллер", "детектив", "меха", "повседневность", 
                       "психологическое", "историческое", "приключения", "мистика", 
                       "спорт", "гарем", "этти", "школа", "киберпанк", "военное"]
        for genre in genres_list:
            if genre in q:
                return get_top_anime(genre=genre)
        return get_top_anime()
    
    elif "найди аниме" in q:
        anime_name = re.sub(r'найди аниме|найти аниме', '', q).strip()
        if anime_name:
            return search_anime_by_name(anime_name)
        return "Напиши название аниме после команды. 🐱"
    
    elif "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    
    elif "что я говорил" in q or "что я спрашивал" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мы ещё не разговаривали! Напиши что-нибудь. 🐱"
        result = "📝 Недавно ты спрашивал:\n"
        for msg in history[-5:]:
            if msg["role"] == "user":
                result += f"• {msg['content'][:80]}...\n"
        return result + "🐱"
    
    elif "привет" in q or "здарова" in q:
        return f"Привет, {user_name}! Как настроение? 🐱"
    
    elif "как дела" in q or "как ты" in q:
        return f"Мурлычу отлично, {user_name}! Греюсь на солнышке ☀️ А у тебя? 🐱"
    
    elif "кто ты" in q:
        return f"Я Кот! Твой пушистый друг, {user_name}. Напиши «список команд» чтобы узнать, что я умею. 🐱"
    
    elif "спасибо" in q:
        return f"Пожалуйста, {user_name}! 🐱"
    
    elif "пока" in q or "до свидания" in q:
        return f"Пока, {user_name}! Заходи ещё. 🐱👋"
    
    else:
        return f"Не совсем понял, {user_name}. Напиши «список команд» чтобы увидеть, что я умею. 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global is_sleeping

    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text or ""
    text_lower = text.lower()
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)

    if not is_allowed_chat(chat_id):
        print(f"❌ Заблокирован чат: {chat_id}")
        return

    # 👇 САМАЯ ПЕРВАЯ ПРОВЕРКА — ИГРА В ГОРОДА 👇
    if user_id in city_games:
        answer = fallback_response(text, user_id, user_name, None, False)
        bot.reply_to(message, answer)
        return

    if "мой айди" in text_lower or "мой id" in text_lower:
        username = message.from_user.username if message.from_user.username else "нет"
        bot.reply_to(message, f"📌 Твой ID: {user_id}\n📌 Имя: {user_name}\n📌 Чат ID: {chat_id}\n🐱")
        return

    if any(x in text_lower for x in ["макс токенов", "max_tokens", "температура", "temp",
                                      "режим краткий", "режим подробный", "режим нормальный",
                                      "показать настройки", "настройки"]):
        result = handle_settings(user_id, text_lower)
        if result:
            bot.reply_to(message, result)
            return

    if "кот спать" in text_lower:
        if is_master(user_id):
            is_sleeping = True
            bot.reply_to(message, f"Спокойной ночи, {user_name}! 😴🐱")
        else:
            bot.reply_to(message, f"Только хозяин может меня усыплять. 🐱")
        return

    if "кот проснись" in text_lower:
        if is_master(user_id):
            is_sleeping = False
            bot.reply_to(message, f"Доброе утро, {user_name}! ☀️🐱")
        else:
            bot.reply_to(message, f"Только хозяин может меня будить. 🐱")
        return

    if is_sleeping:
        if random.random() < 0.1:
            bot.reply_to(message, random.choice([
                f"Мур... сплю, {user_name}... 😴🐱",
                f"Ззз... 🐱",
                f"Утром приходи... 🐱"
            ]))
        return

    # 👇 КОТОПОИСК РАБОТАЕТ БЕЗ ОТВЕТА НА СООБЩЕНИЕ 👇
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()

        if not user_query:
            bot.reply_to(message, f"Напиши что искать, {user_name}! Например: Котопоиск новости 🐱")
            return

        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Ищу...")
        search_results = search_web(user_query)

        if search_results:
            bot.edit_message_text("💭 Думаю...", message.chat.id, status_msg.message_id)
            answer = ask_mistral(user_query, user_id, user_name, search_results, include_links)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("😿 Ничего не нашёл...", message.chat.id, status_msg.message_id)
            time.sleep(2)
            bot.delete_message(message.chat.id, status_msg.message_id)
            answer = f"Ничего не нашёл по запросу, {user_name}. Попробуй переформулировать. 🐱"

        bot.reply_to(message, answer)
        return

    # Проверка на команды аниме
    anime_keywords = ["посоветуй аниме", "найди аниме", "топ аниме", "топ боевиков", "топ романтики", "топ комедии", "топ фэнтези", "топ драмы", "топ ужасов", "топ фантастики", "топ триллеров", "топ детективов", "топ меха"]
    
    if any(keyword in text_lower for keyword in anime_keywords):
        answer = fallback_response(text_lower, user_id, user_name, None, False)
        bot.reply_to(message, answer)
        return

    # Проверка на команды даты и погоды
    if "какой сейчас год" in text_lower or "какая сегодня дата" in text_lower or "какой сегодня день" in text_lower or "какое сегодня число" in text_lower or "который час" in text_lower or "сколько время" in text_lower or "погода" in text_lower:
        answer = fallback_response(text_lower, user_id, user_name, None, False)
        bot.reply_to(message, answer)
        return

    # Проверка на список команд
    if "список команд" in text_lower or "команды" in text_lower or "что ты умеешь" in text_lower:
        answer = fallback_response(text_lower, user_id, user_name, None, False)
        bot.reply_to(message, answer)
        return

    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', text).strip()

        if not user_query:
            bot.reply_to(message, f"Я слушаю, {user_name}! 😸\n\nНапиши «список команд» чтобы увидеть, что я умею. 🐱")
            return

        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_mistral(user_query, user_id, user_name, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print(f"Разрешённые чаты: {ALLOWED_CHATS}")
    print(f"Режим: подробный | Токены: 4000 | Температура: 0.9")
    print(f"Текущая дата: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}")
    print("\nКоманды для всех:")
    print("- Аниме: посоветуй, найди, топ (можно по году и жанру)")
    print("- Игры: сыграем в города (сдаюсь - закончить)")
    print("- Поиск: Котопоиск (работает без ответа на сообщение)")
    print("- Погода: Кот погода в Москве")
    print("- Дата и время: какой сейчас год, какая сегодня дата, который час")
    print("- Общение: привет, как дела, что я говорил")
    print("\nСкрытые команды (только для хозяина):")
    print("- настройки, макс токенов, температура, режим")
    print("- кот спать, кот проснись, мой айди")
    print("=" * 50)

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
