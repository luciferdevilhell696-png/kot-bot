import telebot
import requests
import re
from gigachat import GigaChat

# ========== ТВОИ ДАННЫЕ ==========
TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

bot = telebot.TeleBot(TELEGRAM_TOKEN)

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
                return results[:3]
        return None
    except Exception as e:
        print(f"Search error: {e}")
        return None

def need_search(query):
    q = query.lower()
    
    if "найди" in q or "поищи" in q:
        return True
    
    if any(word in q for word in ["аниме", "посоветуй аниме"]):
        return False
    
    simple = ["привет", "как дела", "что ты умеешь", "кто ты", "спасибо", "пока"]
    if any(word in q for word in simple):
        return False
    
    question_words = ["кто", "что", "где", "когда", "почему"]
    if any(word in q for word in question_words):
        return True
    
    return False

def ask_gigachat(question, search_results=None):
    try:
        with GigaChat(
            credentials=GIGACHAT_AUTH_KEY,
            model="GigaChat-2-Lite",
            verify_ssl_certs=False,
            timeout=30
        ) as client:
            
            if search_results:
                context = ""
                for r in search_results[:2]:
                    title = r.get("title", "")
                    content = r.get("content", "")[:300]
                    url = r.get("url", "")
                    context += f"Источник: {title}\n{content}\nСсылка: {url}\n\n"
                
                prompt = f"""Ты кот-помощник. Ответь на вопрос, используя информацию ниже. Отвечай на русском языке.

Вопрос: {question}

Информация:
{context}

Ответь кратко, добавь 🐱:"""
            else:
                prompt = f"""Ты кот-помощник. Ответь дружелюбно на русском языке.

Вопрос: {question}

Ответь кратко, добавь 🐱:"""
            
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            
            if search_results:
                links = "\n\nИсточники:\n"
                for r in search_results[:2]:
                    links += f"{r.get('url', '')}\n"
                return answer + links
            
            return answer
            
    except Exception as e:
        print(f"GigaChat error: {e}")
        return fallback_response(question)

def fallback_response(question):
    q = question.lower()
    
    if "привет" in q:
        return "Мур-мяу! Привет! Как дела? 🐱"
    elif "как дела" in q:
        return "Мурлычу отлично! А у тебя? ☀️🐱"
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Советую:\n• Киберпанк: Бегущие по краю\n• Фрирен\n• Дандадан 🎬🐱"
    elif "кто ты" in q:
        return "Мяу! Я Кот - твой помощник! 🐱"
    elif "спасибо" in q:
        return "Мур-мяу! Всегда рад помочь! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! 👋🐱"
    else:
        return f"Мяу... Не понял. Спроси что-то другое! 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if "кот" in message.text.lower():
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Напиши что-нибудь, например:\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        
        if need_search(user_query):
            status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу...")
            results = search_web(user_query)
            bot.edit_message_text("💭 Мяу... думаю...", message.chat.id, status_msg.message_id)
            answer = ask_gigachat(user_query, results)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            answer = ask_gigachat(user_query, None)
        
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("🐱 Кот-бот запущен!")
    bot.infinity_polling()
