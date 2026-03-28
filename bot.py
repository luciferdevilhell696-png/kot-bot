import telebot
import requests
import re
import uuid
import time
import json
from collections import defaultdict

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

bot = telebot.TeleBot(TELEGRAM_TOKEN)

access_token = None
token_expires_at = 0

# Хранилище памяти для каждого пользователя
# Формат: {user_id: [{"role": "user/assistant", "content": "..."}, ...]}
user_memory = defaultdict(list)
MAX_MEMORY = 10  # Храним последние 10 сообщений

def get_user_memory(user_id):
    """Получить историю диалога пользователя"""
    return user_memory[user_id]

def add_to_memory(user_id, role, content):
    """Добавить сообщение в память"""
    user_memory[user_id].append({"role": role, "content": content})
    # Ограничиваем размер памяти
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    """Очистить память пользователя"""
    if user_id in user_memory:
        user_memory[user_id] = []
    return "Мяу! Я всё забыл. Начинаем с чистого листа! 🐱"

def get_access_token():
    global access_token, token_expires_at
    
    if access_token and time.time() < token_expires_at:
        return access_token
    
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    payload = {
        'scope': 'GIGACHAT_API_PERS'
    }
    
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
            print(f"❌ Ошибка получения токена: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def ask_gigachat(question, user_id):
    try:
        token = get_access_token()
        if not token:
            return fallback_response(question, user_id)
        
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        
        # Получаем историю диалога
        history = get_user_memory(user_id)
        
        # Формируем системный промпт с контекстом
        system_prompt = """Ты — кот-помощник по имени Кот. Отвечай дружелюбно.

Правила:
1. Отвечай на русском языке
2. Добавляй "мяу" в конце
3. Отвечай кратко (1-2 предложения)
4. Помни контекст разговора, отвечай на основе предыдущих сообщений"""

        # Собираем все сообщения для отправки
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю диалога (последние сообщения)
        for msg in history:
            messages.append(msg)
        
        # Добавляем текущий вопрос
        messages.append({"role": "user", "content": question})
        
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
            
            # Сохраняем в память
            add_to_memory(user_id, "user", question)
            add_to_memory(user_id, "assistant", answer)
            
            return answer
        else:
            print(f"❌ Ошибка GigaChat: {response.status_code}")
            return fallback_response(question, user_id)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return fallback_response(question, user_id)

def fallback_response(question, user_id):
    q = question.lower()
    
    # Сохраняем вопрос в память (без ответа)
    add_to_memory(user_id, "user", question)
    
    if "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    elif "что я говорил" in q or "что я спрашивал" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мяу... Мы ещё не разговаривали. Напиши что-нибудь! 🐱"
        last_few = history[-3:]  # Последние 3 сообщения
        result = "Мяу! Вот что ты спрашивал недавно:\n\n"
        for msg in last_few:
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
        return "Мяу! Я Кот — твой пушистый помощник с памятью! Запоминаю наш разговор 🐱"
    elif "что ты умеешь" in q:
        return "Мяу! Я умею:\n• Общаться 💬\n• Советовать аниме 🎬\n• Запоминать разговор 🧠\n• Отвечать на вопросы 🤔\n\nНапиши «забудь всё» чтобы очистить память! 🐱"
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    else:
        return f"Мяу... Я не понял. Напиши «Кот привет» или «Кот посоветуй аниме» 🐱"

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
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме»\n«Кот что я говорил» — показать память\n«Кот забудь всё» — очистить память 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_gigachat(user_query, user_id)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С ПАМЯТЬЮ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Реагирует на:")
    print("1. Сообщения со словом 'Кот'")
    print("2. Ответы на свои сообщения")
    print("Новые команды:")
    print("• «Кот что я говорил» — показать историю")
    print("• «Кот забудь всё» — очистить память")
    print("=" * 50)
    bot.infinity_polling()
