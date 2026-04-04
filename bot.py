import telebot
import requests
import re
import time
from collections import defaultdict
import random
import datetime
import os
import logging

# Импортируем модули
from weather import get_weather
from anime import get_random_anime, search_anime_by_name, get_top_anime
from cities import load_cities_from_file, start_city_game, get_city_by_letter, check_city_in_db, city_games, get_last_letter
from utils import get_exact_datetime, search_web
from currency import get_currency
from news import get_news

# ====== ЛОГИРОВАНИЕ ======
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ====== ТОКЕНЫ ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

MASTER_USER_ID = 5939413307
ALLOWED_CHATS = [5939413307, -1002815261087, -1002102345616]

if not TELEGRAM_TOKEN or not MISTRAL_API_KEY:
    logger.error("Токены не найдены!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ====== ПАМЯТЬ ======
user_memory = defaultdict(list)
user_preferences = defaultdict(list)
MAX_MEMORY = 20
is_sleeping = False

# ====== НАСТРОЙКИ БОТА ======
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

# ====== ДАТА ======
CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY = get_exact_datetime()

# ====== ЗАГРУЗКА ГОРОДОВ ======
logger.info("Загрузка базы городов...")
load_cities_from_file("городада.txt")

# ====== ЖАНРЫ ======
GENRE_MAP = {
    "боевик": "Action", "экшн": "Action", "романтика": "Romance",
    "комедия": "Comedy", "фэнтези": "Fantasy", "драма": "Drama",
    "ужасы": "Horror", "фантастика": "Sci-Fi", "триллер": "Thriller",
    "детектив": "Mystery", "меха": "Mecha", "киберпанк": "Cyberpunk"
}

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

# ====== MISTRAL AI ======
SYSTEM_PROMPT = f"""Ты — кот-помощник по имени Кот.

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

def ask_mistral(question, user_id, user_name):
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in user_memory[user_id][-10:]:
            messages.append(msg)
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
            return answer
        else:
            logger.error(f"Mistral API error: {response.status_code}")
            return "Ошибка. Попробуй ещё раз. 🐱"
    except Exception as e:
        logger.error(f"Mistral error: {e}")
        return "Ошибка! Попробуй ещё раз. 🐱"

# ====== ОСНОВНОЙ ХЕНДЛЕР ======
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

    # ====== РЕЖИМ СНА ======
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

    # ====== ПРОВЕРКА: реагируем только если:
    # 1. Сообщение начинается с "кот"
    # 2. ИЛИ это ответ на сообщение бота ======
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
        # Проверяем сдачу (с "кот" в начале или без)
        if text_lower in ["сдаюсь", "выйти", "закончить"] or text_lower == "кот сдаюсь":
            game = city_games.pop(user_id)
            bot.reply_to(message, f"🏆 Игра окончена! Ты назвал {game['user_cities_count']} городов. 🐱")
            return
        
        if not clean_text.strip():
            game = city_games[user_id]
            bot.reply_to(message, f"Напиши город на букву {game['last_letter'].upper()}! 🐱")
            return
        
        game = city_games[user_id]
        exists, msg = check_city_in_db(clean_text, game["used_cities"])
        if not exists:
            bot.reply_to(message, msg)
            return
        if clean_text[0].lower() != game["last_letter"]:
            bot.reply_to(message, f"Город должен начинаться на букву {game['last_letter'].upper()}! 🐱")
            return
        
        game["used_cities"].append(clean_text.lower())
        game["user_cities_count"] += 1
        next_letter = get_last_letter(clean_text)
        
        # Ход бота
        bot_city = get_city_by_letter(next_letter, game["used_cities"])
        
        if bot_city:
            game["used_cities"].append(bot_city.lower())
            game["last_letter"] = get_last_letter(bot_city)
            reply = f"✅ {clean_text}\n\n🤖 {bot_city}\n🎯 Тебе на {game['last_letter'].upper()}! 🐱"
        else:
            city_games.pop(user_id)
            reply = f"✅ {clean_text}\n\n🏆 Я не нашёл город на {next_letter.upper()}! Ты победил! 🐱"
        bot.reply_to(message, reply)
        return

    if any(x in clean_text.lower() for x in ["сыграем в города", "игра города", "поиграем в города", "давай играть в города"]):
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

    # ====== 🌐 КОТОПОИСК ======
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        if not query:
            bot.reply_to(message, "Напиши что искать 🐱")
            return
        results = search_web(query, SEARXNG_URL)
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

    # ====== 🌤️ ПОГОДА ======
    if "погода" in text_lower:
        city = re.sub(r'^погода\s*', '', text_lower).strip()
        city = re.sub(r'^кот\s*', '', city).strip()
        if not city:
            bot.reply_to(message, "Напиши город после команды 'погода'. Например: погода Москва 🐱")
            return
        weather = get_weather(city)
        bot.reply_to(message, weather)
        return

    # ====== 💱 КУРСЫ ВАЛЮТ ======
    if "курс" in text_lower or "валюта" in text_lower:
        currency = get_currency()
        bot.reply_to(message, currency)
        return

    # ====== 📰 НОВОСТИ ======
    if "новости" in text_lower:
        topic = re.sub(r'новости\s*', '', text_lower).strip()
        topic = re.sub(r'^кот\s*', '', topic).strip()
        if not topic or topic == "новости":
            topic = None
        news = get_news(topic)
        bot.reply_to(message, news)
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
• сдаюсь (или кот сдаюсь)

🌐 **ПОИСК:**
• котопоиск (запрос)
• котопоиск +ссылка (запрос)

🌤️ **ПОГОДА:**
• погода (город)

💱 **КУРСЫ:**
• курс валют

📰 **НОВОСТИ:**
• новости (тема)

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

    if "привет" in text_lower or "здарова" in text_lower:
        bot.reply_to(message, f"Привет, {user_name}! Как настроение? 🐱")
        return

    if "как дела" in text_lower or "как ты" in text_lower:
        bot.reply_to(message, f"Мурлычу отлично, {user_name}! А у тебя? 🐱")
        return

    if "спасибо" in text_lower:
        bot.reply_to(message, f"Пожалуйста, {user_name}! 🐱")
        return

    if "пока" in text_lower or "до свидания" in text_lower:
        bot.reply_to(message, f"Пока, {user_name}! Заходи ещё 🐱👋")
        return

    if "кто ты" in text_lower:
        bot.reply_to(message, f"Я Кот! Твой пушистый помощник. Напиши «список команд» 🐱")
        return

    # ====== 🤖 УМНЫЙ ОТВЕТ (MISTRAL) ======
    bot.send_chat_action(chat_id, "typing")
    answer = ask_mistral(clean_text, user_id, user_name)
    bot.reply_to(message, answer)

# ====== ЗАПУСК ======
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
    print("=" * 50)

    try:
        bot.infinity_polling(skip_pending=True, timeout=60)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
