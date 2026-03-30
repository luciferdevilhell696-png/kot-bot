import telebot
import requests
import re
import time
from collections import defaultdict
import random
import datetime
import os

# ====== 🔐 ТОКЕНЫ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ (RAILWAY) ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

MASTER_USER_ID = 5939413307

ALLOWED_CHATS = [
    5939413307,
    -1002815261087,
    -1002102345616,
]

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не найден в переменных окружения!")
    exit(1)
if not MISTRAL_API_KEY:
    print("❌ ОШИБКА: MISTRAL_API_KEY не найден в переменных окружения!")
    exit(1)

print("✅ Токены загружены из переменных окружения")

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

# ====== 🎮 ЗАГРУЗКА ГОРОДОВ ИЗ ФАЙЛА ======
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
    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден!")
        return {}
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
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
        return False, f"Нет городов на букву {first_letter.upper()} в моей базе 😿"
    
    for c in cities_db[first_letter]:
        if c.lower() == city_lower:
            if city_lower in used_cities:
                return False, f"Город {city_name} уже был! 🐱"
            return True, "OK"
    
    return False, f"Не знаю города {city_name} 😿"

# Загружаем города
print("📚 Загрузка базы городов...")
CITIES_DB = load_cities_from_file("городада.txt")

def start_city_game(user_id):
    if not CITIES_DB:
        return "❌ База городов не загружена! Проверь файл городада.txt 🐱"
    
    start_cities = CITIES_DB.get("м", [])
    if not start_cities:
        for letter, cities in CITIES_DB.items():
            if cities:
                start_cities = cities
                break
    
    if not start_cities:
        return "❌ Нет городов в базе! 🐱"
    
    start_city = random.choice(start_cities)
    last_letter = get_last_letter(start_city)
    
    city_games[user_id] = {
        "last_letter": last_letter,
        "used_cities": [start_city.lower()],
        "user_cities_count": 0
    }
    
    return f"🎮 Играем в города! Я называю {start_city}. Тебе на букву {last_letter.upper()}. Твой ход! 🐱"

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

# ====== 🎬 АНИМЕ (ИСПРАВЛЕННЫЙ ПОИСК ПО ЖАНРАМ) ======
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

def get_random_anime(genre=None, year=None):
    try:
        url = "https://shikimori.one/api/animes"
        headers = {"User-Agent": "KotBot/1.0"}
        
        # Получаем 200 случайных аниме
        params = {"limit": 200, "order": "random"}
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            filtered = data
            
            # Фильтруем по жанру (на стороне бота)
            if genre:
                genre_map = {
                    "боевик": "Action", "экшн": "Action",
                    "романтика": "Romance",
                    "комедия": "Comedy",
                    "фэнтези": "Fantasy", "фентези": "Fantasy",
                    "драма": "Drama",
                    "ужасы": "Horror", "хоррор": "Horror",
                    "фантастика": "Sci-Fi",
                    "триллер": "Thriller",
                    "детектив": "Detective",
                    "меха": "Mecha",
                    "повседневность": "Slice of Life",
                    "психологическое": "Psychological",
                    "историческое": "Historical",
                    "приключения": "Adventure",
                    "мистика": "Mystery",
                    "спорт": "Sports",
                    "гарем": "Harem",
                    "этти": "Ecchi",
                    "школа": "School",
                    "киберпанк": "Cyberpunk",
                    "военное": "Military"
                }
                genre_en = genre_map.get(genre.lower(), genre.capitalize())
                filtered = [a for a in data if any(genre_en.lower() == g['name'].lower() for g in a.get('genres', []))]
                print(f"🎭 Жанр {genre} -> {genre_en}, найдено: {len(filtered)}")
            
            # Фильтруем по году
            if year and filtered:
                filtered = [a for a in filtered if a.get('released_on', '').startswith(str(year))]
                print(f"📅 Год {year}, найдено: {len(filtered)}")
            
            if not filtered:
                if genre:
                    return f"Не нашёл аниме в жанре {genre}. Попробуй другой жанр. 🐱"
                return "Ничего не нашёл... Попробуй позже. 🐱"
            
            anime = random.choice(filtered)
            russian_name = anime.get("russian", anime.get("name", "Неизвестно"))
            score = anime.get("score", "Нет")
            episodes = anime.get("episodes", "Неизвестно")
            year_anime = anime.get("released_on", "Неизвестно")[:4] if anime.get("released_on") else "Неизвестно"
            genres = ', '.join([g['name'] for g in anime.get('genres', [])[:3]])
            
            return f"""🎲 Тебе выпало:

🎬 {russian_name}
⭐ {score}/10
🎭 {genres}
📺 {episodes} эпизодов
📅 {year_anime} год

Приятного просмотра! 🐱"""
        
        return "Ошибка API. Попробуй позже. 🐱"
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Ошибка! Попробуй ещё раз. 🐱"

def get_top_anime(genre=None, limit=10):
    try:
        url = "https://shikimori.one/api/animes"
        headers = {"User-Agent": "KotBot/1.0"}
        
        params = {"limit": 50, "order": "popularity", "status": "released"}
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Фильтруем по жанру на стороне бота
            if genre:
                genre_map = {
                    "боевик": "Action", "экшн": "Action",
                    "романтика": "Romance",
                    "комедия": "Comedy",
                    "фэнтези": "Fantasy",
                    "драма": "Drama",
                    "ужасы": "Horror"
                }
                genre_en = genre_map.get(genre.lower(), genre.capitalize())
                data = [a for a in data if any(genre_en.lower() == g['name'].lower() for g in a.get('genres', []))]
            
            if not data:
                return f"Не нашёл топ аниме в жанре {genre}. Попробуй другой жанр. 🐱"
            
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
    
    if "какая сегодня дата" in q or "какое сегодня число" in q:
        return f"Сегодня {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR} 🐱"
    
    if "какой сегодня день" in q or "день недели" in q:
        weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        weekday_num = datetime.datetime.now().weekday()
        return f"Сегодня {weekdays[weekday_num]}! 🐱"

    if "список команд" in q or "команды" in q or "что ты умеешь" in q:
        return f"""📋 КОМАНДЫ КОТА, {user_name}:

🎬 АНИМЕ:
• посоветуй аниме (жанр) — боевик, романтика, комедия, фэнтези, драма, ужасы, триллер, детектив, меха, киберпанк
• найди аниме (название)
• топ аниме

🎮 ИГРЫ:
• сыграем в города
• сдаюсь

🌐 ПОИСК:
• котопоиск (запрос)
• котопоиск +ссылка (запрос)

💬 ОБЩЕНИЕ:
• привет, как дела, спасибо, пока
• какой сейчас год, какая сегодня дата
• забудь всё

Просто напиши команду! 🐱"""
    
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

    # ====== 🎮 ИГРА В ГОРОДА ======
    if user_id in city_games:
        if text_lower in ["сдаюсь", "выйти", "закончить"]:
            game = city_games.pop(user_id)
            user_cities = game.get("user_cities_count", 0)
            bot.reply_to(message, f"🏆 Игра окончена! Ты назвал {user_cities} городов. Хорошая игра! 🐱")
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
        
        # Принимаем город пользователя
        game["used_cities"].append(text.lower())
        game["user_cities_count"] = game.get("user_cities_count", 0) + 1
        next_letter = get_last_letter(text)
        
        # Ход бота
        bot_city = get_city_by_letter(CITIES_DB, next_letter, game["used_cities"])
        
        if bot_city:
            game["used_cities"].append(bot_city.lower())
            game["last_letter"] = get_last_letter(bot_city)
            reply = f"✅ Принято! {text}\n\n🤖 Мой ход: {bot_city}\n🎯 Тебе на букву {game['last_letter'].upper()}! 🐱"
        else:
            city_games.pop(user_id)
            reply = f"✅ Принято! {text}\n\n🏆 Я не могу найти город на букву {next_letter.upper()}! Ты победил!\n📊 Ты назвал {game['user_cities_count']} городов. 🐱"
        
        bot.reply_to(message, reply)
        return

    if "сыграем в города" in text_lower or "игра города" in text_lower or "поиграем в города" in text_lower:
        bot.reply_to(message, start_city_game(user_id))
        return

    if "мой айди" in text_lower or "мой id" in text_lower:
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

    # ====== 🌐 КОТОПОИСК ======
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()

        if not user_query:
            bot.reply_to(message, f"Напиши что искать, {user_name}! 🐱")
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

    # ====== 🎬 АНИМЕ (ПРЯМОЙ ВЫЗОВ) ======
    if "посоветуй аниме" in text_lower:
        # Проверяем жанр
        genres_list = ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы", 
                       "фантастика", "триллер", "детектив", "меха", "киберпанк"]
        
        found_genre = None
        for genre in genres_list:
            if genre in text_lower:
                found_genre = genre
                break
        
        # Проверяем год
        year_match = re.search(r'\b(19|20)\d{2}\b', text_lower)
        year = year_match.group(0) if year_match else None
        
        bot.reply_to(message, get_random_anime(genre=found_genre, year=year))
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

    # ====== 💬 ОБЫЧНЫЕ КОМАНДЫ ======
    simple_commands = ["список команд", "команды", "что ты умеешь", "привет", "здарова", 
                       "как дела", "как ты", "спасибо", "пока", "до свидания", "кто ты", 
                       "какой сейчас год", "какая сегодня дата", "какое сегодня число", 
                       "какой сегодня день", "забудь всё", "очисти память", "что я говорил", 
                       "что я спрашивал"]
    
    if any(cmd in text_lower for cmd in simple_commands):
        answer = fallback_response(text_lower, user_id, user_name, None, False)
        bot.reply_to(message, answer)
        return

    # ====== 🤖 УМНЫЙ ОТВЕТ ======
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

# ====== 🚀 ЗАПУСК ======
if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print(f"Разрешённые чаты: {ALLOWED_CHATS}")
    print(f"Режим: {bot_settings['mode']} | Токены: {bot_settings['max_tokens']} | Температура: {bot_settings['temperature']}")
    print(f"Текущая дата: {CURRENT_DAY}.{CURRENT_MONTH}.{CURRENT_YEAR}")
    print(f"База городов: {sum(len(v) for v in CITIES_DB.values()) if CITIES_DB else 0} городов")
    print("=" * 50)

    # Удаляем вебхук чтобы избежать ошибки 409
    try:
        bot.remove_webhook()
        print("✅ Вебхук удалён")
    except:
        pass
    
    time.sleep(1)

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
