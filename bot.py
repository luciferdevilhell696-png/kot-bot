# ====== 🐱 КОТ-БОТ PRO (ПОЛНАЯ ВЕРСИЯ) ======

import telebot
import requests
import re
import time
from collections import defaultdict
import random
import datetime
import os

# ====== 🔐 ТОКЕНЫ ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

MASTER_USER_ID = 5939413307
ALLOWED_CHATS = [5939413307, -1002815261087, -1002102345616]

if not TELEGRAM_TOKEN or not MISTRAL_API_KEY:
    print("❌ ОШИБКА: Токены не найдены!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ====== 📦 ПАМЯТЬ ======
user_memory = defaultdict(list)
user_preferences = defaultdict(list)
MAX_MEMORY = 20
is_sleeping = False

bot_settings = {
    "max_tokens": 4000,
    "temperature": 0.9,
    "mode": "long"
}

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
        print(f"✅ Загружено городов: {sum(len(v) for v in cities_db.values())}")
        return cities_db
    except:
        print(f"❌ Файл {filename} не найден!")
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

print("📚 Загрузка базы городов...")
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
GENRES_LIST = [
    "боевик","экшн","романтика","комедия","фэнтези","драма",
    "ужасы","фантастика","триллер","детектив","меха","киберпанк",
    "школа","спорт","гарем","этти","психология","мистика"
]

GENRE_IDS = {
    "экшн":1,"боевик":1,
    "приключения":2,
    "комедия":4,
    "драма":8,
    "фэнтези":10,"фентези":10,
    "ужасы":14,"хоррор":14,
    "романтика":22,
    "фантастика":24,
    "мистика":7,
    "психология":40,
    "школа":23,
    "спорт":30,
    "гарем":35,
    "этти":9,
    "меха":18,
    "военное":38,
    "детектив":39,
    "триллер":41,
    "киберпанк":43
}

# ====== 🎯 ПАРСИНГ ======
def parse_anime_request(text):
    text = text.lower()
    genres = [g for g in GENRES_LIST if g in text]
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

# ====== 🎬 АНИМЕ API ======
def get_random_anime(genres=None, year=None):
    try:
        url = "https://shikimori.one/api/animes"
        headers = {"User-Agent": "KotBot-Pro"}

        params = {"limit": 100, "order": "random", "status": "released"}

        if genres:
            ids = [str(GENRE_IDS[g]) for g in genres if g in GENRE_IDS]
            if ids:
                params["genre"] = ",".join(ids)

        if year:
            params["season"] = f"{year}_year"

        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            return "Ошибка API 🐱"

        data = r.json()

        if year:
            data = [a for a in data if a.get("released_on","").startswith(str(year))]

        if not data:
            return "Ничего не нашёл 😿 🐱"

        anime = random.choice(data)

        name_ru = anime.get("russian") or anime.get("name","?")
        name_en = anime.get("name","?")
        score = anime.get("score","?")
        genres_list = ", ".join([g["name"] for g in anime.get("genres",[])[:3]])
        episodes = anime.get("episodes","?")
        year_anime = anime.get("released_on","?")[:4] if anime.get("released_on") else "?"

        return f"""🎲 Тебе выпало:

🎬 «{name_ru}» ({name_en})
⭐ {score}/10
🎭 {genres_list}
📺 {episodes} эпизодов
📅 {year_anime} год

Приятного просмотра! 🐱"""

    except Exception as e:
        print(e)
        return "Ошибка 😿 🐱"

def search_anime_by_name(anime_name):
    try:
        url = "https://shikimori.one/api/animes"
        params = {"search": anime_name, "limit": 1}
        headers = {"User-Agent": "KotBot/1.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
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
    except Exception as e:
        print(f"Ошибка поиска аниме: {e}")
        return "Ошибка! Попробуй другое название. 🐱"

def get_top_anime(genre=None, limit=10):
    try:
        url = "https://shikimori.one/api/animes"
        headers = {"User-Agent": "KotBot/1.0"}
        
        params = {"limit": 50, "order": "popularity", "status": "released"}
        
        if genre and genre in GENRE_IDS:
            params["genre"] = str(GENRE_IDS[genre])
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if not data:
                return f"Не нашёл топ аниме в жанре {genre}. 🐱"
            
            result = f"🔥 Топ-{min(limit, len(data))} аниме"
            if genre:
                result += f" в жанре {genre}:\n\n"
            else:
                result += ":\n\n"
            
            for i, anime in enumerate(data[:limit], 1):
                name = anime.get("russian", anime.get("name", "Неизвестно"))
                score = anime.get("score", "?")
                result += f"{i}. «{name}» — {score}/10 ⭐\n"
            return result + "\n🐱"
        
        return "Не могу получить топ. Попробуй позже. 🐱"
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Ошибка! Попробуй ещё раз. 🐱"

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
        print(f"Ошибка поиска: {e}")
        return None

# ====== 🤖 MISTRAL AI ======
def get_current_date():
    now = datetime.datetime.now()
    return now.year, now.month, now.day

CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY = get_current_date()

SYSTEM_PROMPT = f"""Ты — кот-помощник по имени Кот.

ТЕКУЩАЯ ДАТА: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}

ПРАВИЛА:
1. Отвечай на русском языке
2. Добавляй "🐱" в конце
3. Будь кратким и по делу
4. Можешь использовать эмодзи 🎬🎮🌐🔥😴😸
5. НЕ используй звёздочки (*), решётки (#), подчёркивания (_) для украшения текста
6. НЕ давай подсказки в игре в города
7. Названия аниме давай в формате: «Русское название» (Original Name)"""

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
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
            return "Ошибка. Попробуй ещё раз. 🐱"
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Ошибка! Попробуй ещё раз. 🐱"

# ====== 📋 ОСНОВНОЙ ХЕНДЛЕР ======
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global is_sleeping

    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text or ""
    text_lower = text.lower()
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)

    if chat_id not in ALLOWED_CHATS:
        return

    # ====== 🎮 ИГРА В ГОРОДА ======
    if user_id in city_games:
        if text_lower in ["сдаюсь", "выйти", "закончить"]:
            game = city_games.pop(user_id)
            bot.reply_to(message, f"🏆 Игра окончена! Ты назвал {game['user_cities_count']} городов. 🐱")
            return
        if not text.strip():
            game = city_games[user_id]
            bot.reply_to(message, f"Напиши город на букву {game['last_letter'].upper()}! 🐱")
            return
        game = city_games[user_id]
        exists, msg = check_city_in_db(CITIES_DB, text, game["used_cities"])
        if not exists:
            bot.reply_to(message, msg)
            return
        if text[0].lower() != game["last_letter"]:
            bot.reply_to(message, f"Город должен начинаться на букву {game['last_letter'].upper()}! 🐱")
            return
        game["used_cities"].append(text.lower())
        game["user_cities_count"] += 1
        next_letter = get_last_letter(text)
        bot_city = get_city_by_letter(CITIES_DB, next_letter, game["used_cities"])
        if bot_city:
            game["used_cities"].append(bot_city.lower())
            game["last_letter"] = get_last_letter(bot_city)
            reply = f"✅ {text}\n\n🤖 {bot_city}\n🎯 Тебе на {game['last_letter'].upper()}! 🐱"
        else:
            city_games.pop(user_id)
            reply = f"✅ {text}\n\n🏆 Я не нашёл город на {next_letter.upper()}! Ты победил! 🐱"
        bot.reply_to(message, reply)
        return

    if "сыграем в города" in text_lower:
        bot.reply_to(message, start_city_game(user_id))
        return

    # ====== 🎬 АНИМЕ ======
    if "посоветуй аниме" in text_lower:
        genres, year = parse_anime_request(text_lower)
        save_preferences(user_id, genres)
        bot.reply_to(message, get_random_anime(genres, year))
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

    if "найди аниме" in text_lower:
        anime_name = re.sub(r'(?i)найди аниме|найти аниме', '', text).strip()
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
        bot.reply_to(message, get_top_anime(genre=found_genre))
        return

    # ====== 🌐 КОТОПОИСК ======
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        if not query:
            bot.reply_to(message, "Напиши что искать 🐱")
            return
        bot.send_chat_action(chat_id, "typing")
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

    # ====== 💬 ОБЩЕНИЕ ======
    if text_lower in ["привет", "здарова"]:
        bot.reply_to(message, f"Привет, {user_name}! Как настроение? 🐱")
        return

    if text_lower in ["как дела", "как ты"]:
        bot.reply_to(message, f"Мурлычу отлично, {user_name}! А у тебя? 🐱")
        return

    if "спасибо" in text_lower:
        bot.reply_to(message, f"Пожалуйста, {user_name}! 🐱")
        return

    if text_lower in ["пока", "до свидания"]:
        bot.reply_to(message, f"Пока, {user_name}! Заходи ещё 🐱👋")
        return

    if "кто ты" in text_lower:
        bot.reply_to(message, f"Я Кот! Твой пушистый помощник, {user_name}. Напиши «список команд» 🐱")
        return

    if "какой сейчас год" in text_lower:
        bot.reply_to(message, f"Сейчас {CURRENT_YEAR} год! 🐱")
        return

    if "какая сегодня дата" in text_lower or "какое сегодня число" in text_lower:
        bot.reply_to(message, f"Сегодня {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR} 🐱")
        return

    if "забудь всё" in text_lower or "очисти память" in text_lower:
        bot.reply_to(message, clear_memory(user_id))
        return

    if "мой айди" in text_lower or "мой id" in text_lower:
        bot.reply_to(message, f"📌 Твой ID: {user_id}\n📌 Имя: {user_name}\n🐱")
        return

    if "список команд" in text_lower or "команды" in text_lower or "что ты умеешь" in text_lower:
        reply = f"""📋 **КОМАНДЫ КОТА, {user_name}!**

🎬 **АНИМЕ:**
• посоветуй аниме (жанр) — боевик, романтика, комедия, фэнтези, драма, ужасы...
• найди аниме (название)
• топ аниме
• порекомендуй что-нибудь — по твоим любимым жанрам
• мой вкус — показать сохранённые жанры

🎮 **ИГРЫ:**
• сыграем в города
• сдаюсь

🌐 **ПОИСК:**
• котопоиск (запрос)
• котопоиск +ссылка (запрос)

💬 **ОБЩЕНИЕ:**
• привет, как дела, спасибо, пока
• какой сейчас год, какая сегодня дата
• кто ты, забудь всё, мой айди

🐱"""
        bot.reply_to(message, reply)
        return

    # ====== 🤖 УМНЫЙ ОТВЕТ (MISTRAL) ======
    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', text).strip()
        if not user_query:
            bot.reply_to(message, f"Я слушаю, {user_name}! 😸\nНапиши «список команд» 🐱")
            return
        bot.send_chat_action(chat_id, "typing")
        answer = ask_mistral(user_query, user_id, user_name)
        bot.reply_to(message, answer)
        return

    # ====== ЕСЛИ НИЧЕГО НЕ ПОДОШЛО ======
    bot.reply_to(message, f"Не понял, {user_name}. Напиши «список команд» 🐱")

# ====== 🚀 ЗАПУСК ======
if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ PRO ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print(f"Разрешённые чаты: {ALLOWED_CHATS}")
    print(f"База городов: {sum(len(v) for v in CITIES_DB.values()) if CITIES_DB else 0} городов")
    print(f"Доступные жанры: {', '.join(GENRES_LIST[:10])}...")
    print("=" * 50)

    try:
        bot.remove_webhook()
        print("✅ Вебхук удалён")
    except:
        pass

    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
