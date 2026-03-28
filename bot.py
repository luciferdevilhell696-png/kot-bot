import telebot
import re
from gigachat import GigaChat

# ========== ТВОИ ДАННЫЕ ==========
TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
GIGACHAT_AUTH_KEY = "MDE5ZDMzOTYtMjhjYy03M2YzLWJlNGItOTAzYTZiYzI3YzA0OmQzYTk3YzdmLWRlZDMtNDE2ZS04NGIzLTg1YmU2OWJjZTg3OA=="

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def ask_gigachat(question):
    """Отправляет вопрос в GigaChat и получает ответ на русском"""
    try:
        with GigaChat(
            credentials=GIGACHAT_AUTH_KEY,
            model="GigaChat-2-Lite",
            verify_ssl_certs=False,
            timeout=30
        ) as client:
            
            prompt = f"""Ты — кот-помощник по имени Кот. Ты общаешься с другом.

Правила:
1. Отвечай на русском языке
2. Будь дружелюбным, добавляй "мяу" или "мур"
3. Отвечай кратко (1-2 предложения)
4. В конце ставь 🐱

Вопрос друга: {question}

Твой ответ:"""
            
            response = client.chat(prompt)
            answer = response.choices[0].message.content
            return answer
            
    except Exception as e:
        print(f"Ошибка GigaChat: {e}")
        return "Мяу... У меня проблемы с интернетом. Попробуй позже! 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Проверяем, есть ли слово "кот" в сообщении
    if "кот" in message.text.lower():
        # Убираем слово "кот" из запроса
        user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        # Если ничего не написали после "кот"
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Просто напиши что-нибудь, например:\n\n«Кот привет»\n«Кот как дела?»\n«Кот посоветуй аниме» 🐱")
            return
        
        # Показываем, что бот печатает
        bot.send_chat_action(message.chat.id, "typing")
        
        # Получаем ответ от GigaChat
        answer = ask_gigachat(user_query)
        
        # Отправляем ответ
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print("Бот отвечает только когда его зовут 'Кот'")
    print("Общается на русском языке")
    print("=" * 50)
    bot.infinity_polling()
