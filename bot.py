import telebot
import requests
import json
import re
import time
from gigachat import GigaChat

# ========== ТВОИ ДАННЫЕ ==========
TELEGRAM_TOKEN = "ТВОЙ_НОВЫЙ_ТОКЕН"  # Вставь новый токен
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"
GIGACHAT_AUTH_KEY = "ТВОЙ_НОВЫЙ_КЛЮЧ"  # Вставь новый ключ

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
    
    # Простые вопросы, на которые не нужно искать
    simple_questions = [
        "привет", "здарова", "здравствуй", "hello", "hi",
        "как дела", "как ты", "как сам", "how are you",
        "что ты умеешь", "что можешь", "расскажи о себе",
        "кто ты", "ты кто", "твое имя",
        "спасибо", "благодарю", "thanks",
        "пока", "до свидания", "bye",
        "аниме", "посоветуй аниме", "аниме посоветуй",
        "фильм", "кино", "что посмотреть"
    ]
    
    # Проверяем, простой ли вопрос
    for simple in simple_questions:
        if simple in query_lower:
            return False
    
    # Если есть вопросительные слова — ищем
    question_words = ["кто", "что", "где", "когда", "почему", "зачем", "какой", "сколько"]
    for word in question_words:
        if word in query_lower:
            return True
    
    # Если вопрос длинный и не в списке простых — ищем
    if len(query.split()) > 3:
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
                # Если есть результаты поиска
                context = "\n\n".join([
                    f"📌 {r['title']}\n{r['content']}\n🔗 {r['url']}"
                    for r in search_results[:3]
                ])
                prompt = f"""Ты — кот-помощник по имени Кот. Отвечай на вопросы пользователя, используя ТОЛЬКО информацию из источников ниже. ОБЯЗАТЕЛЬНО ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ.

Вопрос: {question}

Информация из интернета:
{context}

Правила:
1. Отвечай кратко (2-3 предложения)
2. Добавляй "мяу" или "мур" в ответ
3. В конце поставь 🐱
4. ОБЯЗАТЕЛЬНО ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ

Ответ:"""
            else:
                # Простой диалог без поиска
                prompt = f"""Ты — кот-помощник по имени Кот. Ответь на вопрос дружелюбно и с юмором. ОБЯЗАТЕЛЬНО ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ.

Вопрос: {question}

Правила:
1. Отвечай кратко (1-2 предложения)
2. Будь милым котом, добавляй "мяу" или "мур"
3. В конце поставь 🐱
4. НЕ ищи информацию в интернете, отвечай от себя
5. ОБЯЗАТЕЛЬНО ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ

Ответ:"""
            
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            
            # Добавляем ссылки, только если был поиск
            if search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            
            return answer
            
    except Exception as e:
SearXNG
SearXNG
searxng-railway-production-6f14.up.railway.app


print(f"Ошибка GigaChat: {e}")
        return fallback_response(question)

def fallback_response(question):
    """Запасные ответы (без GigaChat) на русском"""
    q = question.lower()
    
    if "привет" in q or "здарова" in q or "hi" in q:
        return "Мур-мяу! Приветствую, друг! Как настроение? 🐱"
    
    elif "как дела" in q or "как ты" in q:
        return "Мурлычу отлично! Греюсь на солнышке и жду твоих вопросов ☀️🐱"
    
    elif "что ты умеешь" in q or "что можешь" in q:
        return "Мяу! Я умею:\n\n• Отвечать на вопросы 💬\n• Искать информацию в интернете 🔍\n• Советовать аниме 🎬\n• Просто быть милым котом 🐱\n\nПросто спроси меня о чём угодно!"
    
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Из свежего советую:\n\n🎬 «Киберпанк: Бегущие по краю»\n🎬 «Фрирен — провожающая в последний путь»\n🎬 «Дандадан»\n\nНаслаждайся просмотром! 🐱"
    
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! Рад помочь 😊🐱"
    
    elif "пока" in q or "до свидания" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    
    elif "кто ты" in q or "ты кто" in q:
        return "Мяу! Я Кот — твой пушистый помощник! Могу ответить на вопросы, поискать информацию в интернете и посоветовать аниме 🐱"
    
    else:
        return f"Мяу... Я не совсем понял вопрос. Попробуй спросить что-то другое! 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Проверяем, обращаются ли к коту
    if "кот" in message.text.lower():
        # Убираем "кот" из запроса
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот как дела?»\n«Кот посоветуй аниме»\n«Кот кто такой Пушкин?» 🐱")
            return
        
        # Показываем, что бот печатает
        bot.send_chat_action(message.chat.id, "typing")
        
        # Определяем, нужен ли поиск в интернете
        if need_search(user_query):
            # Нужен поиск
            status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу информацию в интернете...")
            search_results = search_web(user_query)
            bot.edit_message_text("💭 Мяу... обрабатываю информацию...", message.chat.id, status_msg.message_id)
            answer = ask_gigachat(user_query, search_results)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            # Простой разговор без поиска
            status_msg = bot.send_message(message.chat.id, "💭 Мяу... думаю...")
            answer = ask_gigachat(user_query, None)
            bot.delete_message(message.chat.id, status_msg.message_id)
        
        # Отправляем ответ
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print("Бот отвечает только на русском языке 🐱")
    print("На простые вопросы отвечает без поиска")
    print("На сложные вопросы ищет в интернете")
    print("=" * 50)
    bot.infinity_polling()
