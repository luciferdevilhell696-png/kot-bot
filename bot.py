import telebot
import requests
import re
import time
import random
import datetime
import json
import os
from collections import defaultdict
from dotenv import load_dotenv

# ====== 🔐 ЗАГРУЗКА ТОКЕНОВ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SEARXNG_URL = os.getenv("SEARXNG_URL", "https://searxng-railway-production-6f14.up.railway.app/search")

MASTER_USER_ID = 5939413307
ALLOWED_CHATS = [5939413307, -1002815261087, -1002102345616]

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден!")
    exit(1)
if not MISTRAL_API_KEY:
    print("❌ ОШИБКА: MISTRAL_API_KEY не найден!")
    exit(1)

print("✅ Токены загружены")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ====== 📦 КЭШ АНИМЕ ======
CACHE_FILE = "anime_cache.json"
CACHE_TTL = 86400

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        anime_cache = json.load(f)
else:
    anime_cache = {}

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(anime_cache, f, ensure_ascii=False, indent=2)

# ====== 🧠 ПАМЯТЬ ======
user_memory = defaultdict(list)
MAX_MEMORY = 20
is_sleeping = False

bot_settings = {
    "max_tokens": 4000,
    "temperature": 0.9,
    "mode": "long"
}

# ====== 🎮 ЗАГРУЗЧИК ГОРОДОВ ======
def load_cities_from_file(filename="городада.txt"):
    cities_db = {}
    
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

def get_city_by_letter(cities_db, letter, used_cities):
    cities = cities_db.get(letter, [])
    available = [c for c in cities if c.lower() not in used_cities]
    return random.choice(available) if available else None

def get_last_letter(city):
    last = city[-1].lower()
    if last in ['ь', 'ъ', 'ы'] and len(city) > 1:
        return city[-2].lower()
    return last

def check_city(cities_db, city_name, used_cities):
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

# ====== 🎮 ЗАГРУЗКА ГОРОДОВ ======
print("📚 Загрузка базы городов...")
CITIES_DB = load_cities_from_file("городада.txt")
city_games = {}

# ====== 📅 ДАТА ======
def get_current_date():
    now = datetime.datetime.now()
    return now.year, now.month, now.day

CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY = get_current_date()

# ====== 🎮 ИГРА В ГОРОДА ======
def start_city_game(user_id):
    start_cities = CITIES_DB.get("м", ["Москва"])
    start_city = random.choice(start_cities)
    last_letter = get_last_letter(start_city)
    
    city_games[user_id] = {
        "last_letter": last_letter,
        "used_cities": [start_city.lower()]
    }
    return f"🎮 Играем в города! Я называю **{start_city}**. Тебе на букву **{last_letter.upper()}**. Твой ход! 🐱"

def bot_make_move(user_id):
    game = city_games[user_id]
    bot_city = get_city_by_letter(CITIES_DB, game["last_letter"], game["used_cities"])
    
    if bot_city:
        game["used_cities"].append(bot_city.lower())
        game["last_letter"] = get_last_letter(bot_city)
        return bot_city
    return None

# ====== 🌐 ПОИСК ======
def search_web(query):
    try:
        params = {"q": query, "format": "json", "language": "ru"}
        response = requests.get(SEARXNG_URL, params=params, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None
        return [{"title": r.get("title", "Без названия"), "url": r.get("url", ""), "content": r.get("content", "")[:800]} for r in results[:3]]
    except Exception as e:
        print("Ошибка поиска:", e)
        return None

# ====== 🎬 АНИМЕ ======
def search_anime_by_name(anime_name):
    key = anime_name.lower()
    
    if key in anime_cache:
        data, timestamp = anime_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data + "\n⚡ (из кэша) 🐱"

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
                
                result = f"""🎬 «{russian_name}» ({english_name})

📅 Год: {year}
⭐ Рейтинг: {score}/10
🎭 Жанры: {genres}
📺 Эпизодов: {episodes}
📖 {description}...

🔗 Подробнее: https://shikimori.one/animes/{anime['id']}
🐱"""
                
                anime_cache[key] = (result, time.time())
                save_cache()
                return result
        return f"Не нашёл аниме «{anime_name}». Попробуй иначе. 🐱"
    except:
        return "Ошибка! Попробуй другое название. 🐱"

def get_random_anime(genre=None, year=None):
    try:
        url = "https://shikimori.one/api/animes"
        params = {"limit": 50, "order": "random"}
        
        if genre:
            genre_map = {
                "боевик": "action", "романтика": "romance", "комедия": "comedy",
                "фэнтези": "fantasy", "драма": "drama", "ужасы": "horror",
                "фантастика": "sci-fi", "триллер": "thriller", "детектив": "detective",
                "меха": "mecha", "киберпанк": "cyberpunk"
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
                score = anime.get("score", "Нет")
                episodes = anime.get("episodes", "Неизвестно")
                year_anime = anime.get("released_on", "Неизвестно")[:4] if anime.get("released_on") else "Неизвестно"
                
                return f"""🎲 Тебе выпало:

🎬 {russian_name}
⭐ {score}/10
📺 {episodes} эпизодов
📅 {year_anime} год

Приятного просмотра! 🐱"""
        return "Ничего не нашёл... 🐱"
    except:
        return "Ошибка! Попробуй ещё раз. 🐱"

def get_top_anime(genre=None, limit=10):
    try:
        url = "https://shikimori.one/api/animes"
        params = {"limit": limit, "order": "popularity", "status": "released"}
        
        if genre:
            genre_map = {
                "боевик": "action", "романтика": "romance", "комедия": "comedy",
                "фэнтези": "fantasy", "драма": "drama", "ужасы": "horror"
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
        return "Не могу получить топ. Попробуй позже. 🐱"
    except:
        return "Ошибка! Попробуй ещё раз. 🐱"

# ====== 🤖 MISTRAL AI ======
SYSTEM_PROMPT = f"""Ты — кот-помощник по имени Кот.

ТЕКУЩАЯ ДАТА: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}

ПРАВИЛА:
1. Отвечай на русском языке
2. Добавляй "🐱" в конце
3. Будь кратким и по делу
4. Можешь использовать эмодзи 🎬🎮🌐🔥😴😸
5. НЕ используй звёздочки (*), решётки (#), подчёркивания (_)"""

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    return "Забыл всё! Начинаем заново. 🐱"

def get_user_memory(user_id):
    return user_memory[user_id]

def ask_mistral(question, user_id, user_name, search_results=None, include_links=False):
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in get_user_memory(user_id)[-10:]:
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
            return fallback_response(question, user_id, user_name, search_results, include_links)
    except Exception as e:
        print(f"Ошибка: {e}")
        return fallback_response(question, user_id, user_name, search_results, include_links)

def fallback_response(question, user_id, user_name, search_results=None, include_links=False):
    q = question.lower()
    add_to_memory(user_id, "user", question[:200])

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

    if "какой сейчас год" in q:
        return f"Сейчас {CURRENT_YEAR} год! 🐱"
    if "какая сегодня дата" in q:
        return f"Сегодня {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR} 🐱"
    if "привет" in q:
        return f"Привет, {user_name}! Как настроение? 🐱"
    if "как дела" in q:
        return f"Мурлычу отлично, {user_name}! 🐱"
    if "спасибо" in q:
        return f"Пожалуйста, {user_name}! 🐱"
    if "пока" in q:
        return f"Пока, {user_name}! 🐱👋"
    if "забудь" in q:
        return clear_memory(user_id)
    
    return f"Не понял, {user_name}. Напиши «список команд» 🐱"

# ====== 📋 ОСНОВНОЙ ОБРАБОТЧИК ======
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
        if "сдаюсь" in text_lower:
            game = city_games.pop(user_id)
            bot.reply_to(message, f"🏆 Игра окончена! Ты назвал {len(game['used_cities'])} городов. 🐱")
            return
        
        if not text.strip():
            bot.reply_to(message, f"Напиши город на букву **{city_games[user_id]['last_letter'].upper()}** 🐱")
            return
        
        game = city_games[user_id]
        
        exists, msg = check_city(CITIES_DB, text, game["used_cities"])
        if not exists:
            bot.reply_to(message, msg)
            return
        
        if text[0].lower() != game["last_letter"]:
            bot.reply_to(message, f"❌ Город должен начинаться на **{game['last_letter'].upper()}**! 🐱")
            return
        
        game["used_cities"].append(text.lower())
        next_letter = get_last_letter(text)
        
        bot_city = bot_make_move(user_id)
        
        if bot_city:
            reply = f"✅ {text}\n\n🤖 {bot_city}\n🎯 Тебе на **{get_last_letter(bot_city).upper()}**! 🐱"
        else:
            city_games.pop(user_id)
            reply = f"✅ {text}\n\n🏆 Я не нашёл город на **{next_letter.upper()}**! Ты победил! 🐱"
        
        bot.reply_to(message, reply)
        return

    if "сыграем в города" in text_lower:
        bot.reply_to(message, start_city_game(user_id))
        return

    # ====== 🎬 АНИМЕ ======
    if "найди аниме" in text_lower:
        anime_name = re.sub(r'(?i)найди аниме', '', text).strip()
        if not anime_name:
            bot.reply_to(message, "Напиши название аниме 🐱")
            return
        bot.reply_to(message, search_anime_by_name(anime_name))
        return

    if "посоветуй аниме" in text_lower:
        years = re.findall(r'\b(19|20)\d{2}\b', text_lower)
        year = years[0] if years else None
        
        genres = ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы", "фантастика", "триллер", "детектив", "меха", "киберпанк"]
        for genre in genres:
            if genre in text_lower:
                bot.reply_to(message, get_random_anime(genre=genre, year=year))
                return
        bot.reply_to(message, get_random_anime(year=year))
        return

    if "топ аниме" in text_lower:
        genres = ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы"]
        for genre in genres:
            if genre in text_lower:
                bot.reply_to(message, get_top_anime(genre=genre))
                return
        bot.reply_to(message, get_top_anime())
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
    if "список команд" in text_lower or "команды" in text_lower:
        reply = f"""📋 **КОМАНДЫ КОТА, {user_name}!**

🎬 **АНИМЕ:**
• найди аниме (название)
• посоветуй аниме
• топ аниме

🎮 **ИГРЫ:**
• сыграем в города
• сдаюсь

🌐 **ПОИСК:**
• котопоиск (запрос)
• котопоиск +ссылка (запрос)

💬 **ОБЩЕНИЕ:**
• привет, как дела, спасибо, пока
• какой сейчас год, какая сегодня дата
• забудь всё

🐱"""
        bot.reply_to(message, reply)
        return

    if "мой айди" in text_lower or "мой id" in text_lower:
        bot.reply_to(message, f"📌 Твой ID: {user_id}\n📌 Имя: {user_name}\n🐱")
        return

    if any(x in text_lower for x in ["какой сейчас год", "какая сегодня дата", "привет", "как дела", "спасибо", "пока", "забудь"]):
        bot.reply_to(message, fallback_response(text_lower, user_id, user_name))
        return

    if "кот" in text_lower or is_reply_to_bot:
        user_query = re.sub(r'[Кк]от[,\s]?', '', text).strip() if "кот" in text_lower else text.strip()
        if not user_query:
            bot.reply_to(message, f"Я слушаю, {user_name}! 😸\nНапиши «список команд» 🐱")
            return
        bot.send_chat_action(chat_id, "typing")
        answer = ask_mistral(user_query, user_id, user_name)
        bot.reply_to(message, answer)
        return

# ====== 🚀 ЗАПУСК ======
if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print(f"Разрешённые чаты: {ALLOWED_CHATS}")
    print(f"Кэш аниме: {len(anime_cache)} записей")
    print("=" * 50)

    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
