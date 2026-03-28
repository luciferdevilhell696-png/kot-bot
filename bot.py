import telebot
import requests
import json
import re
import time
from gigachat import GigaChat

# ========== ТВОИ ДАННЫЕ (ВСТАВЛЕНЫ) ==========
TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

# Создаём бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== ФУНКЦИЯ ПОИСКА В ИНТЕРНЕТЕ ==========
def search_web(query):
    """Ищет информацию через SearXNG (безлимитно)"""
    try:
        print(f"🔍 Ищу: {query}")
        
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
                print(f"✅ Найдено {len(results)} результатов")
                return [{
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500]
                } for r in results[:5]]
            else:
                print("❌ Результатов не найдено")
                return None
        else:
            print(f"❌ Ошибка SearXNG: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return None

# ========== ФУНКЦИЯ ЗАПРОСА К GIGACHAT ==========
def ask_gigachat(question, search_results=None):
    """Отправляет вопрос в GigaChat"""
    try:
        # Подключаемся к GigaChat
        with GigaChat(
            credentials=GIGACHAT_AUTH_KEY,
            model="GigaChat-2-Lite",
            verify_ssl_certs=False,
            timeout=30
        ) as client:
            
            # Формируем промпт
            if search_results:
                context = "\n\n".join([
                    f"📌 ИСТОЧНИК {i+1}: {r['title']}\n"
                    f"СОДЕРЖАНИЕ: {r['content']}\n"
                    f"ССЫЛКА: {r['url']}"
                    for i, r in enumerate(search_results[:3])
                ])
                
                prompt = f"""Ты — кот-помощник по имени Кот. Отвечай на вопросы пользователя, используя ТОЛЬКО информацию из источников ниже.

ВОПРОС: {question}

ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:
{context}

ПРАВИЛА:
1. Отвечай кратко (2-3 предложения)
2. Добавляй "мяу" или "мур" в ответ
3. В конце поставь 🐱

ОТВЕТ:"""
            else:
                prompt = f"""Ты — кот-помощник по имени Кот. Ответь на вопрос пользователя.

ВОПРОС: {question}

ПРАВИЛА:
1. Отвечай кратко и дружелюбно (2-3 предложения)
2. Добавляй "мяу" или "мур"
3. В конце поставь 🐱

ОТВЕТ:"""
            
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            
            if search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            
            return answer
            
    except Exception as e:
        print(f"❌ Ошибка GigaChat: {e}")
        return fallback_response(question, search_results)

# ========== ЗАПАСНЫЕ ОТВЕТЫ ==========
def fallback_response(question, search_results=None):
    """Ответы на случай ошибки"""
    q = question.lower()
    
    if search_results:
        reply = f"Мяу! Вот что я нашёл по запросу «{question}»:\n\n"
        for r in search_results[:2]:
            reply += f"📌 {r['title']}\n{r['url']}\n\n"
        return reply + "🐱"
    
    if "привет" in q:
        return "Мур-мяу! Приветствую тебя, друг! 🐱"
    elif "как дела" in q:
        return "Мурлычу отлично! Греюсь на солнышке и жду твоих вопросов ☀️🐱"
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Из свежего советую:\n\
SearXNG
SearXNG
searxng-railway-production-6f14.up.railway.app


n🎬 «Киберпанк: Бегущие по краю»\n🎬 «Фрирен — провожающая в последний путь»\n🎬 «Дандадан»\n\nНаслаждайся просмотром! 🐱"
    else:
        return f"Мяу... Я пока учусь. Попробуй спросить про аниме 🐱"

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if "кот" in message.text.lower():
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот посоветуй аниме»\n«Кот как дела?» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу информацию...")
        search_results = search_web(user_query)
        
        bot.edit_message_text("💭 Мяу... обрабатываю...", message.chat.id, status_msg.message_id)
        answer = ask_gigachat(user_query, search_results)
        
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.reply_to(message, answer)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Жду когда меня позовут словом 'Кот'...")
    print("=" * 50)
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🐱 Бот остановлен.")