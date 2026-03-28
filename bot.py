import telebot
import requests
import re
import uuid
import time

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

bot = telebot.TeleBot(TELEGRAM_TOKEN)

access_token = None
token_expires_at = 0

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
            return access_token
        else:
            return None
            
    except Exception as e:
        return None

def ask_gigachat(question):
    try:
        token = get_access_token()
        if not token:
            return fallback_response(question)
        
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        
        payload = {
            "model": "GigaChat",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты кот-помощник. Отвечай на русском, добавляй мяу. Отвечай кратко."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
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
            return data['choices'][0]['message']['content']
        else:
            return fallback_response(question)
            
    except Exception as e:
        return fallback_response(question)

def fallback_response(question):
    q = question.lower()
    
    if "привет" in q:
        return "Мур-мяу! Приветствую, друг! Как настроение? 🐱"
    elif "как дела" in q or "как ты" in q:
        return "Мурлычу отлично! Греюсь на солнышке ☀️🐱"
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Советую:\n\n🎬 Киберпанк: Бегущие по краю\n🎬 Фрирен\n🎬 Дандадан\n\nПриятного просмотра! 🐱"
    elif "кто ты" in q:
        return "Мяу! Я Кот — твой пушистый помощник! 🐱"
    elif "что ты умеешь" in q:
        return "Мяу! Я умею общаться, советовать аниме и отвечать на вопросы! 🐱"
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё 🐱👋"
    else:
        return f"Мяу... Я не понял. Напиши «Кот привет» или «Кот посоветуй аниме» 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if "кот" in message.text.lower():
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_gigachat(user_query)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("🐱 Кот-бот запущен!")
    bot.infinity_polling()
