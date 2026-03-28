import telebot
import requests
import re
import time
from collections import defaultdict
import random

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
MISTRAL_API_KEY = "I9PvXEOaGCsaAvjfMcPLSF0P5FrdmQJ9"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

# 👇 ТВОЙ TELEGRAM ID (только ты можешь усыплять кота)
MASTER_USER_ID = 5939413307

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_memory = defaultdict(list)
user_sleeping = defaultdict(bool)
MAX_MEMORY = 20

SYSTEM_PROMPT = """Ты — кот-помощник по имени Кот. Ты дружелюбный, но отвечаешь КОРОТКО.

ПРАВИЛА:
1. Отвечай КРАТКО! Максимум 2-3 предложения, если не просят подробностей
2. Названия аниме давай в формате: «Русское название» (Original Name)
3. Пример: «Клинок, рассекающий демонов» (Demon Slayer)
4. Высказывай своё мнение, но лаконично
5. В конце каждого сообщения ОБЯЗАТЕЛЬНО добавляй "мяу 🐱"
6. Будь живым и эмоциональным, но НЕ многословным"""

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

def ask_mistral(question, user_id, search_results=None, include_links=False):
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
            return fallback_response(question, user_id, search_results, include_links)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return fallback_response(question, user_id, search_results, include_links)

def fallback_response(question, user_id, search_results=None, include_links=False):
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

    if "забудь" in q or "очисти память" in q:
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
            "Мур-мяу! Привет! Как настроение? 😸 мяу 🐱",
            "О, привет! Давно ждал! Что нового? мяу 🐱",
            "Мяу! Привет-привет! Рад тебя видеть! 😺 мяу 🐱"
        ])
    elif "как дела" in q:
        return random.choice([
            "Мурлычу отлично! А у тебя? мяу 🐱",
            "Замечательно! Солнышко, тепло, и ты рядом! мяу 😸",
            "Отлично! Жду твоих вопросов! мяу 🐱"
        ])
    elif "аниме" in q or "посоветуй" in q:
        return """Мяу! Мои любимчики:

1. «Клинок, рассекающий демонов» (Demon Slayer) — красота невероятная!
2. «Киберпанк: Бегущие по краю» (Cyberpunk Edgerunners) — мощно и душевно
3. «Фрирен» (Frieren) — уютное и глубокое
4. «Дандадан» (Dandadan) — угар и экшн

Какой жанр любишь? Расскажу подробнее! мяу 🐱"""
    elif "кто ты" in q:
        return "Я Кот! Твой пушистый друг. Люблю аниме, болтать и узнавать новое. А ты? мяу 🐱"
    elif "что ты умеешь" in q:
        return """Умею:
• Болтать как друг
• Искать в интернете: «Котопоиск что-то»
• Советовать аниме
• Запоминать разговоры
• А ещё могу спать, если скажешь «Кот спать» 😴

Спрашивай что хочешь! мяу 🐱"""
    elif "спасибо" in q:
        return random.choice([
            "Мур-мяу! Всегда пожалуйста! 😊 мяу 🐱",
            "Ой, мне приятно! Обращайся! мяу 🐱"
        ])
    elif "пока" in q:
        return random.choice([
            "Пока-пока! Заходи ещё! мяу 🐱👋",
            "До встречи! Хорошего дня! мяу 🐱"
        ])
    else:
        return f"Интересный вопрос! 😸 Расскажи подробнее, а я посоветую что-нибудь! мяу 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text or ""
    text_lower = text.lower()
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    # Команда "мой айди" — покажет ID (для настройки)
    if "мой айди" in text_lower or "мой id" in text_lower:
        bot.reply_to(message, f"Твой Telegram ID: `{user_id}`\n\nЭтот ID нужно вставить в код вместо MASTER_USER_ID, чтобы только ты мог усыплять кота! мяу 🐱", parse_mode="Markdown")
        return
    
    # Команды сна и пробуждения (только для хозяина)
    if "кот спать" in text_lower:
        if is_master(user_id):
            user_sleeping[user_id] = True
            bot.reply_to(message, random.choice([
                "Мяу-мяу... Спокойной ночи, хозяин... 😴 мяу 🐱",
                "Зеваю... Укладываюсь спать... Мур-мяу... 😴 мяу 🐱",
                "Спатки? Хорошо... Пушистых снов, хозяин... 😴 мяу 🐱"
            ]))
        else:
            bot.reply_to(message, "Мяу... Только мой хозяин может меня усыплять! 😾 мяу 🐱")
        return
    
    if "кот проснись" in text_lower:
        if is_master(user_id):
            user_sleeping[user_id] = False
            bot.reply_to(message, random.choice([
                "Мяу-мяу! Доброе утро, хозяин! Выспался отлично! ☀️ мяу 🐱",
                "Мур... уже утро? Потягушки! Доброе утро! 😸 мяу 🐱",
                "Проснулся! Слышу голос хозяина! Чем займёмся? мяу 🐱"
            ]))
        else:
            bot.reply_to(message, "Мяу... Только мой хозяин может меня будить! 😾 мяу 🐱")
        return
    
    # Если кот спит — не отвечаем на другие сообщения
    if user_sleeping[user_id]:
        if random.random() < 0.1:
            bot.reply_to(message, random.choice([
                "Мур... сплю... не мешай... 😴 мяу",
                "Ззз... позже... мяу... 😴",
                "Храп-храп... мяу... 😴"
            ]))
        return
    
    # Обработка остальных команд (когда кот бодрствует)
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        
        if not user_query:
            bot.reply_to(message, "Напиши что искать! Например: «Котопоиск новости» 🔍 мяу 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу...")
        search_results = search_web(user_query)
        
        if search_results:
            bot.edit_message_text("💭 Нашёл кое-что! Сейчас расскажу...", message.chat.id, status_msg.message_id)
            answer = ask_mistral(user_query, user_id, search_results, include_links)
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
            bot.reply_to(message, "Мяу? Я слушаю! 😸\n\nНапиши что-нибудь:\n• Кот привет\n• Кот посоветуй аниме\n• Котопоиск новости\n• Кот что я говорил\n• мой айди — узнать свой ID\n\nЕсли хочешь спать — скажи «Кот спать» 😴\n\nЖду! мяу 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_mistral(user_query, user_id, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-ДРУГ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print(f"Хозяин ID: {MASTER_USER_ID}")
    print("\nКоманды только для хозяина:")
    print("• «Кот спать» — кот засыпает 😴")
    print("• «Кот проснись» — кот просыпается ☀️")
    print("\nДля всех:")
    print("• «мой айди» — показать свой Telegram ID")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
