import telebot
import requests
import re

# ========== ТВОИ ДАННЫЕ ==========
TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
DEEPSEEK_API_KEY = "sk-bcddc6bd46d34d8290a41fb32c4773c1"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def ask_deepseek(question):
    """Отправляет вопрос в DeepSeek API"""
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты — кот-помощник по имени Кот. Отвечай на русском языке, будь дружелюбным, добавляй 'мяу' в конце. Отвечай кратко (1-2 предложения)."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return answer
        else:
            print(f"Ошибка DeepSeek: {response.status_code}")
            return fallback_response(question)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return fallback_response(question)

def fallback_response(question):
    """Запасные ответы (если DeepSeek не работает)"""
    q = question.lower()
    
    if "привет" in q:
        return "Мур-мяу! Приветствую, друг! Как настроение? 🐱"
    elif "как дела" in q:
        return "Мурлычу отлично! Греюсь на солнышке ☀️🐱"
    elif "аниме" in q or "посоветуй" in q:
        return "Мяу! Советую:\n\n🎬 «Киберпанк: Бегущие по краю»\n🎬 «Фрирен»\n🎬 «Дандадан»\n\nПриятного просмотра! 🐱"
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
    # Проверяем, есть ли слово "кот" в сообщении
    if "кот" in message.text.lower():
        # Убираем слово "кот" из запроса
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме» 🐱")
            return
        
        # Показываем, что бот печатает
        bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем ответ от DeepSeek
        answer = ask_deepseek(user_query)
        
        # Отправляем ответ
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С DEEPSEEK ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Жду когда меня позовут словом 'Кот'...")
    print("=" * 50)
    bot.infinity_polling()
