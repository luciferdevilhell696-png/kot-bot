import telebot
import requests
import re
import time
from collections import defaultdict
import random

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

SYSTEM_PROMPT = """Ты — кот-помощник по имени Кот. Ты дружелюбный, но отвечаешь КОРОТКО.

ПРАВИЛА:
1. Отвечай КРАТКО! Максимум 2-3 предложения, если не просят подробностей
2. Названия аниме давай в формате: «Русское название» (Original Name)
3. Пример: «Клинок, рассекающий демонов» (Demon Slayer)
4. Высказывай своё мнение, но лаконично
5. В конце каждого сообщения ОБЯЗАТЕЛЬНО добавляй "мяу 🐱"
6. Будь живым и эмоциональным, но НЕ многословным"""

def is_allowed_chat(chat_id):
    return chat_id in ALLOWED_CHATS

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    return "Забыл! Начинаем заново! мяу 🐱"

def get_user_memory(user_id):
    return user_memory[user_id]

def is_master(user_id):
    return user_id == MASTER_USER_ID

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
        params = {
            "search": anime_name,
            "limit": 1
        }
        
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
мяу 🐱"""
            else:
                return f"Мяу... Не нашёл аниме «{anime_name}». Попробуй написать по-другому! 🐱"
        else:
            return "Мяу... Ошибка подключения к Shikimori. Попробуй позже! 🐱"
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Мяу... Ошибка! Попробуй другое название 🐱"

def get_random_anime(genre=None):
    try:
        url = "https://shikimori.one/api/animes"
        params = {
            "limit": 50,
            "order": "random"
        }
        
        if genre:
            genre_map = {
                "боевик": "action",
                "экшн": "action",
                "романтика": "romance",
                "комедия": "comedy",
                "фэнтези": "fantasy",
                "фентези": "fantasy",
                "драма": "drama",
                "ужасы": "horror",
                "фантастика": "sci-fi"
            }
            params["genre"] = genre_map.get(genre.lower(), genre.lower())
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                anime = random.choice(data)
                russian_name = anime.get("russian", anime.get("name", "Неизвестно"))
                english_name = anime.get("name", "Неизвестно")
                score = anime.get("score", "Нет")
                episodes = anime.get("episodes", "Неизвестно")
                year = anime.get("released_on", "Неизвестно")[:4] if anime.get("released_on") else "Неизвестно"
                genres = ', '.join([g['name'] for g in anime.get('genres', [])[:3]])
                
                return f"""🎲 Мяу! Тебе выпало:

🎬 «{russian_name}» ({english_name})
📅 {year} год
⭐ {score}/10
🎭 {genres}
📺 {episodes} эпизодов

Приятного просмотра! 🐱"""
            else:
                return "Мяу... Ничего не нашёл. Попробуй другие параметры! 🐱"
        else:
            return "Мяу... Ошибка подключения. Попробуй позже! 🐱"
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Мяу... Ошибка! Попробуй ещё раз 🐱"

def get_top_anime(genre=None, limit=10):
    try:
        url = "https://shikimori.one/api/animes"
        params = {
            "limit": limit,
            "order": "popularity",
            "status": "released"
        }
        
        if genre:
            genre_map = {
                "боевик": "action",
                "экшн": "action",
                "романтика": "romance",
                "комедия": "comedy",
                "фэнтези": "fantasy",
                "драма": "drama"
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
                
                return result + "\nмяу 🐱"
        return "Мяу... Не могу получить топ. Попробуй позже! 🐱"
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Мяу... Ошибка! Попробуй ещё раз 🐱"

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
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь КРАТКО (2-3 предложения), выскажи своё мнение. В конце добавь ссылки."""
            else:
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь КРАТКО (2-3 предложения), выскажи своё мнение."""
            messages.append({"role": "user", "content": enhanced_question})
        else:
            messages.append({"role": "user", "content": f"Ответь КРАТКО (2-3 предложения). {question} В конце обязательно скажи мяу!"})

        payload = {
            "model": "mistral-small-latest",
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 300
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            if "мяу" not in answer.lower():
                answer = answer.rstrip() + " мяу 🐱"
            
            add_to_memory(user_id, "user", question[:200])
            add_to_memory(user_id, "assistant", answer[:500])
            
            if include_links and search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            return answer
        else:
            print(f"❌ Ошибка Mistral: {response.status_code}")
            return fallback_response(question, user_id, user_name, search_results, include_links)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return fallback_response(question, user_id, user_name, search_results, include_links)

def fallback_response(question, user_id, user_name, search_results=None, include_links=False):
    q = question.lower()
    add_to_memory(user_id, "user", question[:200])

    if search_results:
        if include_links:
            reply = "Нашёл кое-что интересное! 😸\n\n"
            for r in search_results[:3]:
                reply += f"📌 {r['title']}\n{r['url']}\n\n"
            return reply + "Зацени! мяу 🐱"
        else:
            reply = "Смотри, что нашёл:\n\n"
            for r in search_results[:3]:
                reply += f"• {r['title']}\n"
            return reply + "\nХочешь ссылки? Добавь +ссылка! мяу 🐱"

    # ========== КОМАНДА "КАК МЕНЯ ЗОВУТ" ==========
    if "как меня зовут" in q or "как меня звать" in q or "моё имя" in q:
        return f"Мяу! Твоё имя — {user_name}! Разве ты забыл? 😸 мяу 🐱"
    
    # ========== АНИМЕ-КОМАНДЫ ==========
    
    if "посоветуй аниме" in q or "рекомендуй аниме" in q:
        for genre in ["боевик", "романтика", "комедия", "фэнтези", "драма", "ужасы"]:
            if genre in q:
                return get_random_anime(genre=genre)
        return get_random_anime()
    
    elif "топ" in q and "аниме" in q:
        for genre in ["боевик", "романтика", "комедия", "фэнтези", "драма"]:
            if genre in q:
                return get_top_anime(genre=genre)
        return get_top_anime()
    
    elif "найди аниме" in q or "найти аниме" in q:
        anime_name = re.sub(r'найди аниме|найти аниме', '', q).strip()
        if anime_name:
            return search_anime_by_name(anime_name)
        return "Мяу! Напиши название аниме, которое хочешь найти! 🐱"
    
    # ========== ОБЫЧНЫЕ КОМАНДЫ ==========
    
    elif "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    elif "что я говорил" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мы ещё не болтали! Напиши что-нибудь 😸 мяу 🐱"
        result = "Ты спрашивал:\n\n"
        for msg in history[-5:]:
            if msg["role"] == "user":
                result += f"• {msg['content'][:80]}...\n"
        return result + "\nА теперь о чём поговорим? мяу 🐱"
    elif "привет" in q:
        return random.choice([
            f"Мур-мяу! Привет, {user_name}! Как настроение? 😸 мяу 🐱",
            f"О, привет, {user_name}! Давно ждал! Что нового? мяу 🐱",
            f"Мяу! Привет-привет, {user_name}! Рад тебя видеть! 😺 мяу 🐱"
        ])
    elif "как дела" in q:
        return random.choice([
            f"Мурлычу отлично, {user_name}! А у тебя? мяу 🐱",
            f"Замечательно, {user_name}! Солнышко, тепло, и ты рядом! мяу 😸",
            f"Отлично, {user_name}! Жду твоих вопросов! мяу 🐱"
        ])
    elif "кто ты" in q:
        return f"Я Кот! Твой пушистый друг, {user_name}. Люблю аниме, болтать и узнавать новое. А ты? мяу 🐱"
    elif "что ты умеешь" in q:
        return f"""Умею, {user_name}:
• Болтать как друг
• Искать в интернете: «Котопоиск что-то»
• Советовать аниме: «Кот посоветуй аниме»
• Находить аниме: «Кот найди аниме Название»
• Показывать топ: «Кот топ аниме»
• Запоминать разговоры
• А ещё я знаю твоё имя! Напиши «как меня зовут» 😸

Спрашивай что хочешь! мяу 🐱"""
    elif "спасибо" in q:
        return random.choice([
            f"Мур-мяу, {user_name}! Всегда пожалуйста! 😊 мяу 🐱",
            f"Ой, мне приятно, {user_name}! Обращайся! мяу 🐱"
        ])
    elif "пока" in q:
        return random.choice([
            f"Пока-пока, {user_name}! Заходи ещё! мяу 🐱👋",
            f"До встречи, {user_name}! Хорошего дня! мяу 🐱"
        ])
    else:
        return f"Интересный вопрос, {user_name}! 😸 Расскажи подробнее, а я посоветую что-нибудь!\n\nПопробуй:\n• Кот посоветуй аниме\n• Кот найди аниме Киберпанк\n• Кот топ аниме\n• Котопоиск новости\n• как меня зовут\nмяу 🐱"

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
    
    if "мой айди" in text_lower or "мой id" in text_lower:
        username = message.from_user.username if message.from_user.username else "нет"
        bot.reply_to(message, f"📌 Твой ID: `{user_id}`\n📌 Твоё имя: {user_name}\n📌 Username: @{username}\n\nID этого чата: `{chat_id}`\n\nДобавь chat_id в ALLOWED_CHATS, если хочешь чтобы бот работал здесь! мяу 🐱", parse_mode="Markdown")
        return
    
    if "кот спать" in text_lower:
        if is_master(user_id):
            is_sleeping = True
            bot.reply_to(message, random.choice([
                f"Мяу-мяу... Спокойной ночи, {user_name}! 😴 Кот уснул... мяу 🐱",
                f"Зеваю... Укладываюсь спать, {user_name}... 😴 мяу 🐱",
                f"Спатки? Хорошо, {user_name}... Всем спокойных снов... 😴 мяу 🐱"
            ]))
        else:
            bot.reply_to(message, f"Мяу... {user_name}, только мой хозяин может меня усыплять! 😾 мяу 🐱")
        return
    
    if "кот проснись" in text_lower:
        if is_master(user_id):
            is_sleeping = False
            bot.reply_to(message, random.choice([
                f"Мяу-мяу! Доброе утро, {user_name}! Кот проснулся! ☀️ мяу 🐱",
                f"Мур... уже утро? Потягушки! Доброе утро, {user_name}! 😸 мяу 🐱",
                f"Проснулся! Слышу голос {user_name}! Всем привет! мяу 🐱"
            ]))
        else:
            bot.reply_to(message, f"Мяу... {user_name}, только мой хозяин может меня будить! 😾 мяу 🐱")
        return
    
    if is_sleeping:
        if random.random() < 0.1:
            bot.reply_to(message, random.choice([
                f"Мур... сплю, {user_name}... не мешай... 😴 мяу",
                f"Ззз... позже, {user_name}... кот спит... 😴 мяу",
                f"Храп-храп... утром приходи, {user_name}... 😴 мяу"
            ]))
        return
    
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        
        if not user_query:
            bot.reply_to(message, f"Мяу! {user_name}, напиши что искать! Например: «Котопоиск новости» 🔍 мяу 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу...")
        search_results = search_web(user_query)
        
        if search_results:
            bot.edit_message_text("💭 Нашёл кое-что! Сейчас расскажу...", message.chat.id, status_msg.message_id)
            answer = ask_mistral(user_query, user_id, user_name, search_results, include_links)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("😿 Ничего не нашёл... Попробуй по-другому!", message.chat.id, status_msg.message_id)
            time.sleep(2)
            bot.delete_message(message.chat.id, status_msg.message_id)
            answer = "Ничего не нашёл! Может, переформулируем? мяу 🐱"
        
        bot.reply_to(message, answer)
        return
    
    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', text).strip()
        
        if not user_query:
            bot.reply_to(message, f"Мяу? Я слушаю, {user_name}! 😸\n\nНапиши что-нибудь:\n• Кот привет\n• Кот посоветуй аниме\n• Кот найди аниме Киберпанк\n• Кот топ боевиков\n• Котопоиск новости\n• Кот что я говорил\n• как меня зовут\n\nЖду! мяу 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_mistral(user_query, user_id, user_name, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С SHIKIMORI API ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print(f"Разрешённые чаты: {ALLOWED_CHATS}")
    print("\nАНИМЕ-КОМАНДЫ:")
    print("• Кот посоветуй аниме — случайное аниме")
    print("• Кот посоветуй боевик — случайный боевик")
    print("• Кот найди аниме Название — поиск по названию")
    print("• Кот топ аниме — топ-10 популярных")
    print("\nПОИСК В ИНТЕРНЕТЕ:")
    print("• Котопоиск новости — без ссылок")
    print("• Котопоиск +ссылка новости — со ссылками")
    print("\nОБЩЕНИЕ:")
    print("• Кот привет")
    print("• Кот как дела?")
    print("• как меня зовут — узнать своё имя")
    print("• Кот что я говорил — память")
    print("• Кот забудь всё — очистить память")
    print("\nСОН (только для хозяина):")
    print("• Кот спать")
    print("• Кот проснись")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
