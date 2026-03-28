import telebot
import requests
import re
import time
from collections import defaultdict

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
KIMI_API_KEY = "sk-2uHOnhgaQKZL0EIY4cSprAvaxBDZJ8gehJMkK5586IG0ikZi"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_memory = defaultdict(list)
MAX_MEMORY = 10

SYSTEM_PROMPT = """Ты — кот-помощник по имени Кот. Отвечай дружелюбно на русском языке.

Правила:
1. Отвечай на русском языке
2. Добавляй "мяу" в конце
3. Отвечай кратко (1-2 предложения)
4. Помни контекст разговора"""

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
                    "content": r.get("content", "")[:500]
                } for r in results[:5]]
        return None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None

def ask_kimi(question, user_id, search_results=None, include_links=False):
    try:
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {KIMI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        history = get_user_memory(user_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for msg in history[-6:]:
            messages.append(msg)
        
        if search_results:
            context = "\n\n".join([
                f"📌 {r['title']}\n{r['content']}" for r in search_results[:3]
            ])
            
            if include_links:
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь кратко на основе этой информации. В конце добавь ссылки на источники."""
            else:
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь кратко на основе этой информации. НЕ добавляй ссылки, только текст ответа."""
            messages.append({"role": "user", "content": enhanced_question})
        else:
            messages.append({"role": "user", "content": question})

        payload = {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            add_to_memory(user_id, "user", question)
            add_to_memory(user_id, "assistant", answer)
            
            if include_links and search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            return answer
        else:
            print(f"❌ Ошибка Kimi: {response.status_code}")
            return fallback_response(question, user_id, search_results, include_links)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return fallback_response(question, user_id, search_results, include_links)

def fallback_response(question, user_id, search_results=None, include_links=False):
    q = question.lower()
    add_to_memory(user_id, "user", question)

    if search_results:
        if include_links:
            reply = "Мяу! Вот что я нашёл:\n\n"
            for r in search_results[:3]:
                reply += f"📌 {r['title']}\n{r['url']}\n\n"
            return reply + "🐱"
        else:
            reply = "Мяу! Вот что я нашёл:\n\n"
            for r in search_results[:2]:
                reply += f"• {r['title']}\n"
            return reply + "\nЧтобы увидеть ссылки, напиши «Котопоиск +ссылка» 🐱"

    if "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    elif "что я говорил" in q or "что я спрашивал" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мяу... Мы ещё не разговаривали. Напиши что-нибудь! 🐱"
        result = "Мяу! Вот что ты спрашивал недавно:\n\n"
        for msg in history[-4:]:
            role = "Ты" if msg["role"] == "user" else "Я"
            result += f"{role}: {msg['content'][:50]}\n"
        return result + "🐱"
    elif "привет" in q:
        return "Мур-мяу! Приветствую, друг! Как настроение? 🐱"
    elif "как дела" in q:
        return "Мурлычу отлично! Греюсь на солнышке ☀️🐱"
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Советую:\n\n🎬 Киберпанк: Бегущие по краю\n🎬 Фрирен\n🎬 Дандадан\n\nПриятного просмотра! 🐱"
    elif "кто ты" in q:
        return "Мяу! Я Кот — твой пушистый помощник! Использую Kimi AI 🐱"
    elif "что ты умеешь" in q:
        return "Мяу! Я умею:\n• Общаться 💬\n• Советовать аниме 🎬\n• Запоминать разговор 🧠\n• Искать в интернете 🔍\n\nПоиск:\n• «Котопоиск новости» — без ссылок\n• «Котопоиск +ссылка новости» — со ссылками 🐱"
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    else:
        return f"Мяу... Я не понял. Напиши:\n• «Кот привет»\n• «Кот посоветуй аниме»\n• «Котопоиск новости»\n• «Кот что я говорил» 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    text_lower = message.text.lower()
    
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу! Напиши что искать после «Котопоиск», например:\n\n«Котопоиск новости» — без ссылок\n«Котопоиск +ссылка новости» — со ссылками 🔍🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу в интернете...")
        search_results = search_web(user_query)
        
        if search_results:
            bot.edit_message_text("💭 Мяу... обрабатываю...", message.chat.id, status_msg.message_id)
            answer = ask_kimi(user_query, user_id, search_results, include_links)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("😿 Мяу... ничего не нашёл. Попробуй переформулировать запрос!", message.chat.id, status_msg.message_id)
            time.sleep(2)
            bot.delete_message(message.chat.id, status_msg.message_id)
            answer = "Мяу... Ничего не нашёл по этому запросу. Попробуй спросить по-другому! 🐱"
        
        bot.reply_to(message, answer)
        return
    
    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = message.text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме»\n«Котопоиск новости»\n«Кот что я говорил» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_kimi(user_query, user_id, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С KIMI AI ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Модель: Kimi (moonshot-v1-8k)")
    print("=" * 50)
    
    # Запускаем с обработкой ошибок
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
