import telebot
import requests
import json
import re
import time
from gigachat import GigaChat

# ========== ТВОИ ДАННЫЕ (СТАРЫЕ КЛЮЧИ - ВРЕМЕННО) ==========
TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def search_web(query):
    """Поиск в интернете через SearXNG"""
    try:
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
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500]
                } for r in results[:5]]
        return None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None

def need_search(query):
    """Определяет, нужен ли поиск в интернете"""
    query_lower = query.lower()
    
    # Слова, которые явно говорят "ищи в интернете"
    search_keywords = ["найди", "поищи", "узнай", "найди мне", "поищи в интернете"]
    for word in search_keywords:
        if word in query_lower:
            return True
    
    # Если это запрос на аниме — НЕ ищем
    anime_keywords = ["аниме", "посоветуй аниме", "какое аниме", "аниме посоветуй"]
    for word in anime_keywords:
        if word in query_lower:
            return False
    
    # Если это приветствие или простой диалог — НЕ ищем
    simple_questions = [
        "привет", "здарова", "здравствуй", "hello", "hi",
        "как дела", "как ты", "как сам", "как жизнь",
        "что ты умеешь", "что можешь", "расскажи о себе",
        "кто ты", "ты кто", "твое имя", "как тебя зовут",
        "спасибо", "благодарю",
        "пока", "до свидания", "покеда",
        "что посмотреть", "посоветуй фильм", "кино посоветуй"
    ]
    
    for simple in simple_questions:
        if simple in query_lower:
            return False
    
    # Вопросительные слова — ищем
    question_words = ["кто", "что", "где", "когда", "почему", "зачем", "какой", "сколько"]
    for word in question_words:
        if word in query_lower:
            if "аниме" not in query_lower:
                return True
    
    return False

def ask_gigachat(question, search_results=None):
    """Отправляет вопрос в GigaChat"""
    try:
        with GigaChat(
            credentials=GIGACHAT_AUTH_KEY,
            model="GigaChat-2-Lite",
            verify_ssl_certs=False,
            timeout=30
        ) as client:
            
            if search_results:
                context = "\n\n".join([
                    f"📌 {r['title']}\n{r['content']}\n🔗 {r['url']}"
                    for r in search_results[:3]
                ])
                prompt = f"""Ты — кот-помощник по имени Кот. Отвечай на вопросы пользователя, используя ТОЛЬКО информацию из источников ниже.

Вопрос: {question}

Информация из интернета:
{context}

Правила:
1. Отвечай кратко (2-3 предложения)
2. Добавляй "мяу" или "мур"
3. В конце поставь 🐱
4. Обязательно отвечай на русском языке

Ответ:"""
            else:
                prompt = f"""Ты — кот-помощник по имени Кот. Отвечай дружелюбно и с юмором.

Вопрос: {question}

Правила:
1. Отвечай кратко (1-2 предложения)
2. Будь милым котом, добавляй "мяу" или "мур"
3. В конце поставь 🐱
4. НЕ ищи информацию в интернете, отвечай от себя
5. Обязательно отвечай на русском языке

Ответ:"""
            
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            
            if search_results:
                links = "\n\n📌 Исто
SearXNG
SearXNG
searxng-railway-production-6f14.up.railway.app


чники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            
            return answer
            
    except Exception as e:
        print(f"Ошибка GigaChat: {e}")
        return fallback_response(question)

def fallback_response(question):
    """Запасные ответы"""
    q = question.lower()
    
    if "привет" in q:
        return "Мур-мяу! Приветствую! Как настроение? 🐱"
    
    elif "как дела" in q or "как ты" in q:
        return "Мурлычу отлично! Греюсь на солнышке ☀️🐱"
    
    elif "что ты умеешь" in q:
        return "Мяу! Я умею:\n\n• Общаться 💬\n• Искать в интернете 🔍\n• Советовать аниме 🎬\n\nПросто спроси меня! 🐱"
    
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Советую посмотреть:\n\n🎬 «Киберпанк: Бегущие по краю»\n🎬 «Фрирен»\n🎬 «Дандадан»\n\nПриятного просмотра! 🐱"
    
    elif "кто ты" in q:
        return "Мяу! Я Кот — твой пушистый помощник! 🐱"
    
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! 😊🐱"
    
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    
    else:
        return f"Мяу... Я не понял вопрос. Попробуй спросить что-то другое! 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if "кот" in message.text.lower():
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме»\n«Кот найди новости» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        
        if need_search(user_query):
            status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу в интернете...")
            search_results = search_web(user_query)
            bot.edit_message_text("💭 Мяу... обрабатываю...", message.chat.id, status_msg.message_id)
            answer = ask_gigachat(user_query, search_results)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            answer = ask_gigachat(user_query, None)
        
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print("Бот: @kot_helper_bot")
    print("Поиск в интернете работает ТОЛЬКО если:")
    print("- Сказать 'найди' или 'поищи'")
    print("- Спросить с вопросительным словом")
    print("=" * 50)
    bot.infinity_polling()
