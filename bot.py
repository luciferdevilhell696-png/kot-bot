import telebot
import requests
import json
import re
import time
from gigachat import GigaChat

# ========== ТВОИ ДАННЫЕ (ЗАМЕНИ НА НОВЫЕ КЛЮЧИ) ==========
TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def search_web(query):
    try:
        print(f"Searching: {query}")
        response = requests.get(SEARXNG_URL, params={
            "q": query,
            "format": "json",
            "categories": "general",
            "limit": 5
        }, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return [{
                    "title": r.get("title", "No title"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500]
                } for r in results[:5]]
        return None
    except Exception as e:
        print(f"Search error: {e}")
        return None

def ask_gigachat(question, search_results=None):
    try:
        with GigaChat(
            credentials=GIGACHAT_AUTH_KEY,
            model="GigaChat-2-Lite",
            verify_ssl_certs=False,
            timeout=30
        ) as client:
            
            if search_results:
                context = "\n\n".join([
                    f"Source: {r['title']}\nContent: {r['content']}\nURL: {r['url']}"
                    for r in search_results[:3]
                ])
                prompt = f"""You are a cat assistant. Answer the question using ONLY the information below.

Question: {question}

Information:
{context}

Answer briefly, add 🐱 at the end:"""
            else:
                prompt = f"You are a cat assistant. Answer the question: {question} 🐱"
            
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            
            if search_results:
                links = "\n\nSources:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            return answer
    except Exception as e:
        print(f"GigaChat error: {e}")
        return fallback_response(question, search_results)

def fallback_response(question, search_results=None):
    q = question.lower()
    if search_results:
        reply = "Meow! I found:\n\n"
        for r in search_results[:2]:
            reply += f"📌 {r['title']}\n{r['url']}\n\n"
        return reply + "🐱"
    if "привет" in q or "hello" in q:
        return "Meow! Hello! 🐱"
    elif "аниме" in q or "anime" in q:
        return "Meow! I recommend: Cyberpunk Edgerunners, Frieren, Dandadan 🎬🐱"
    else:
        return "Meow... Ask me something 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if "кот" in message.text.lower() or "kot" in message.text.lower():
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text.lower())
        user_query = re.sub(r'kot[,\s]?', '', user_query).strip()
        
        if not user_query:
            bot.reply_to(message, "Meow? Ask me something, like: 'kot recommend anime' 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Meow... searching...")
        search_results = search_web(user_query)
        bot.edit_message_text("💭 Meow... thinking...", message.chat.id, status_msg.message_id)
        answer = ask_gigachat(user_query, search_results)
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("🐱 Cat bot started!")
    bot.infinity_polling()
