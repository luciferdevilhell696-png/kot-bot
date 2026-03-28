import telebot
import requests
import re
import time
from collections import defaultdict

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
MISTRAL_API_KEY = "I9PvXEOaGCsaAvjfMcPLSF0P5FrdmQJ9"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_memory = defaultdict(list)
MAX_MEMORY = 20

# Базовая инструкция с гибким форматированием
SYSTEM_PROMPT = """Ты — кот-помощник по имени Кот. Отвечай на русском языке.

ПРАВИЛА ФОРМАТИРОВАНИЯ:
1. Если просят список (например, "топ 5", "список", "перечисли") — отвечай кратко, только названия с короткими описаниями, без лишней воды
2. Если просят подробности ("расскажи подробно", "опиши") — тогда можешь развернуто
3. Если вопрос простой ("как дела", "привет") — отвечай в 1-2 предложения
4. В конце каждого ответа добавляй "мяу" или 🐱
5. Для списков используй формат: 
   1. Название — короткое описание (1 строка)
   2. Название — короткое описание
   и так далее

Будь дружелюбным, но лаконичным, если не просят подробностей."""

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    return "Мяу! Я всё забыл. Начинаем с чистого листа! 🐱"

def get_user_memory(user_id):
    return user_memory[user_id]

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

Ответь кратко и по делу. Если просят список — сделай список с короткими описаниями. В конце добавь ссылки на источники."""
            else:
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь кратко и по делу. Если просят список — сделай список с короткими описаниями."""
            messages.append({"role": "user", "content": enhanced_question})
        else:
            # Проверяем тип вопроса
            if "подробно" in question.lower() or "разверни" in question.lower():
                messages.append({"role": "user", "content": f"Расскажи подробно: {question}"})
            else:
                messages.append({"role": "user", "content": f"Отвечай кратко и по делу. {question}"})

        payload = {
            "model": "mistral-small-latest",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
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
            reply = "Мяу! Нашёл информацию:\n\n"
            for r in search_results[:3]:
                reply += f"📌 {r['title']}\n{r['url']}\n\n"
            return reply + "🐱"
        else:
            reply = "Мяу! Нашёл:\n\n"
            for r in search_results[:3]:
                reply += f"• {r['title']}\n"
            return reply + "🐱"

    if "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    elif "что я говорил" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мяу... Мы ещё не разговаривали 🐱"
        result = "Мяу! Недавно ты спрашивал:\n"
        for msg in history[-5:]:
            if msg["role"] == "user":
                result += f"• {msg['content'][:80]}...\n"
        return result + "🐱"
    elif "привет" in q:
        return "Мур-мяу! Привет! Как настроение? 🐱"
    elif "как дела" in q:
        return "Мурлычу отлично! А у тебя? ☀️🐱"
    elif "аниме" in q:
        return """Мяу! Топ-5 аниме, которые стоит посмотреть:

1. Киберпанк: Бегущие по краю — киберпанк, драма
2. Фрирен — уютное фэнтези
3. Дандадан — комедия, экшн
4. Атака Титанов — эпичная драма
5. Клинок, рассекающий демонов — красивая визуализация

Если хочешь подробнее о каком-то, спроси! 🐱"""
    elif "кто ты" in q:
        return "Мяу! Я Кот — твой помощник. Умею искать в интернете, советовать аниме и отвечать на вопросы 🐱"
    elif "что ты умеешь" in q:
        return """Мяу! Я умею:
• Отвечать на вопросы (кратко и по делу)
• Искать в интернете: «Котопоиск что-то»
• Советовать аниме
• Запоминать разговор

Команды:
«Кот привет»
«Котопоиск новости»
«Кот что я говорил»
«Кот забудь всё» 🐱"""
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    else:
        return f"Мяу... Не понял. Попробуй: «Кот привет», «Кот посоветуй аниме» или «Котопоиск что-то» 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    text_lower = message.text.lower()
    
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу! Напиши что искать: «Котопоиск новости» 🔍🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу...")
        search_results = search_web(user_query)
        
        if search_results:
            bot.edit_message_text("💭 Мяу... обрабатываю...", message.chat.id, status_msg.message_id)
            answer = ask_mistral(user_query, user_id, search_results, include_links)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("😿 Мяу... ничего не нашёл", message.chat.id, status_msg.message_id)
            time.sleep(2)
            bot.delete_message(message.chat.id, status_msg.message_id)
            answer = "Мяу... Ничего не нашёл 🐱"
        
        bot.reply_to(message, answer)
        return
    
    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = message.text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Напиши что-нибудь: «Кот привет», «Кот посоветуй аниме» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_mistral(user_query, user_id, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С MISTRAL AI (умные ответы)")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Режимы: кратко по умолчанию, подробно если просят")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
