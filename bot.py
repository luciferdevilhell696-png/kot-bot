import telebot
import requests
import re
import uuid
import time
from collections import defaultdict

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

access_token = None
token_expires_at = 0

user_memory = defaultdict(list)
MAX_MEMORY = 10

def get_user_memory(user_id):
    return user_memory[user_id]

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    if user_id in user_memory:
        user_memory[user_id] = []
    return "Мяу! Я всё забыл. Начинаем с чистого листа! 🐱"

def search_web(query):
    try:
        response = requests.get(SEARXNG_URL, params={
            "q": query,
            "format": "json",
            "limit": 3
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return [{
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500]
                } for r in results[:3]]
        return None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None

def need_search(query):
    q = query.lower()
    
    if "найди" in q or "поищи" in q or "узнай" in q:
        return True
    
    question_words = ["кто", "что", "где", "когда", "почему", "зачем", "какой", "сколько"]
    for word in question_words:
        if word in q:
            if "аниме" not in q:
                return True
    
    return False

def get_access_token():
    global access_token, token_expires_at
    
    if access_token and time.time() < token_expires_at:
        return access_token
    
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    payload = {'scope': 'GIGACHAT_API_PERS'}
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            token_expires_at = time.time() + 25 * 60
            print("✅ Получен новый Access Token")
            return access_token
        else:
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def ask_gigachat(question, user_id, search_results=None):
    try:
        token = get_access_token()
        if not token:
            return fallback_response(question, user_id, search_results)
        
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        
        history = get_user_memory(user_id)
        
        system_prompt = """Ты кот-помощник по имени Кот. Отвечай дружелюбно на русском языке.

Правила:
1. Отвечай на русском языке
2. Добавляй "мяу" в конце
3. Отвечай кратко (1-2 предложения)
4. Помни контекст разговора"""

        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in history[-6:]:
            messages.append(msg)
        
        if search_results:
            context = "\n\n".join([
                f"📌 {r['title']}\n{r['content']}\n🔗 {r['url']}"
                for r in search_results[:2]
            ])
            enhanced_question = f"""{question}

Информация из интернета:
{context}

Используй ТОЛЬКО эту информацию для ответа."""
        else:
            enhanced_question = question
        
        messages.append({"role": "user", "content": enhanced_question})
        
        payload = {
            "model": "GigaChat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            add_to_memory(user_id, "user", question)
            add_to_memory(user_id, "assistant", answer)
            
            if search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            return answer
        else:
            return fallback_response(question, user_id, search_results)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return fallback_response(question, user_id, search_results)

def fallback_response(question, user_id, search_results=None):
    q = question.lower()
    
    add_to_memory(user_id, "user", question)
    
    if search_results:
        reply = f"Мяу! Вот что я нашёл по запросу:\n\n"
        for r in search_results[:2]:
            reply += f"📌 {r['title']}\n{r['url']}\n\n"
        return reply + "🐱"
    
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
        return "Мяу! Я Кот — твой пушистый помощник! Запоминаю разговоры и могу искать в интернете 🐱"
    elif "что ты умеешь" in q:
        return "Мяу! Я умею:\n• Общаться 💬\n• Советовать аниме 🎬\n• Запоминать разговор 🧠\n• Искать в интернете 🔍\n\nНапиши «найди» или спроси с вопросительным словом 🐱"
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    else:
        return f"Мяу... Я не понял. Напиши:\n• «Кот привет»\n• «Кот посоветуй аниме»\n• «Кот найди новости»\n• «Кот что я говорил» 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    if "кот" in message.text.lower() or is_reply_to_bot:
        user_query = message.text.strip()
        
        if is_reply_to_bot and "кот" not in user_query.lower():
            user_query = user_query
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', user_query).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме»\n«Кот найди новости»\n«Кот что я говорил» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        
        if need_search(user_query):
            status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу в интернете...")
            search_results = search_web(user_query)
            bot.edit_message_text("💭 Мяу... обрабатываю...", message.chat.id, status_msg.message_id)
            answer = ask_gigachat(user_query, user_id, search_results)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            answer = ask_gigachat(user_query, user_id, None)
        
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С ПАМЯТЬЮ И ПОИСКОМ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Реагирует на:")
    print("1. Сообщения со словом 'Кот'")
    print("2. Ответы на свои сообщения")
    print("\nВозможности:")
    print("• Запоминает разговор 🧠")
    print("• Ищет в интернете 🔍")
    print("• Советует аниме 🎬")
    print("\nКоманды:")
    print("• «Кот что я говорил» — показать память")
    print("• «Кот найди ...» — поиск в интернете")
    print("• «Кот забудь всё» — очистить память")
    print("=" * 50)
    bot.infinity_polling()
