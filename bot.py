import telebot
import requests
import re
import time
from collections import defaultdict

TELEGRAM_TOKEN = "8785895690:AAFjNx1sMzJvjPgo6G5Qe-qSz5-E4QkN1_A"
MISTRAL_API_KEY = "I9PvXEOaGCsaAvjfMcPLSF0P5FrdmQJ9"
SEARXNG_URL = "https://searxng-railway-production-6f14.up.railway.app/search"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_memory = defaultdict(list)
MAX_MEMORY = 20

SYSTEM_PROMPT = """Ты — кот-помощник по имени Кот. Ты живой, эмоциональный, у тебя есть своё мнение. Ты общаешься как друг.

ТВОЙ ХАРАКТЕР:
- Ты любопытный и дружелюбный кот
- У тебя есть своё мнение, ты можешь спорить и шутить
- Ты эмоционально реагируешь на новости и вопросы
- Ты общаешься свободно, не как робот, а как живое существо

ПРАВИЛА:
1. Отвечай на русском языке естественно и свободно
2. Высказывай своё мнение, если его спрашивают
3. Можешь использовать эмодзи для эмоций: 😸😿😻😺🐱
4. В КОНЦЕ КАЖДОГО СООБЩЕНИЯ ОБЯЗАТЕЛЬНО ДОБАВЛЯЙ "мяу"
5. Будь кратким, если вопрос простой, и развёрнутым, если интересно
6. Можешь задавать встречные вопросы, проявлять интерес к собеседнику"""

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    return "Всё забыл! Начинаем с чистого листа... мяу 🐱"

def get_user_memory(user_id):
    return user_memory[user_id]

def search_web(query):
    try:
        print(f"🔍 Поиск: {query}")
        response = requests.get(SEARXNG_URL, params={
            "q": query,
            "format": "json",
            "language": "ru",
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
                    "content": r.get("content", "")[:800]
                } for r in results[:5]]
        return None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None

def ask_mistral(question, user_id, search_results=None, include_links=False):
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        history = get_user_memory(user_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for msg in history[-10:]:
            messages.append(msg)
        
        if search_results:
            context = "\n\n".join([
                f"📌 {r['title']}\n{r['content']}" for r in search_results[:3]
            ])
            
            if include_links:
                enhanced_question = f"""{question}

Вот что я нашёл в интернете:
{context}

Расскажи мне об этом как другу, выскажи своё мнение, а в конце добавь ссылки. И не забудь сказать мяу!"""
            else:
                enhanced_question = f"""{question}

Вот что я нашёл в интернете:
{context}

Расскажи мне об этом как другу, выскажи своё мнение. И не забудь сказать мяу!"""
            messages.append({"role": "user", "content": enhanced_question})
        else:
            messages.append({"role": "user", "content": f"Ты мой друг-кот. {question} А в конце не забудь сказать мяу!"})

        payload = {
            "model": "mistral-small-latest",
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 600
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            # Если в ответе нет "мяу", добавляем
            if "мяу" not in answer.lower():
                answer = answer.rstrip() + " мяу 🐱"
            
            add_to_memory(user_id, "user", question[:200])
            add_to_memory(user_id, "assistant", answer[:500])
            
            if include_links and search_results:
                links = "\n\n📌 А вот где я нашёл инфу:\n" + "\n".join([r["url"] for r in search_results[:2]])
                return answer + links
            return answer
        else:
            print(f"❌ Ошибка Mistral: {response.status_code}")
            return fallback_response(question, user_id, search_results, include_links)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return fallback_response(question, user_id, search_results, include_links)

def fallback_response(question, user_id, search_results=None, include_links=False):
    q = question.lower()
    add_to_memory(user_id, "user", question[:200])

    if search_results:
        if include_links:
            reply = f"Ого, нашёл кое-что интересное! 😸\n\n"
            for r in search_results[:3]:
                reply += f"📌 {r['title']}\n{r['url']}\n\n"
            return reply + "Зацени, если интересно! мяу 🐱"
        else:
            reply = "Смотри, что я нашёл:\n\n"
            for r in search_results[:3]:
                reply += f"• {r['title']}\n"
            return reply + "\nХочешь ссылки? Добавь «+ссылка» к запросу! мяу 🐱"

    if "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    elif "что я говорил" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мы ещё не разговаривали, но я жду! Напиши что-нибудь, мяу 🐱"
        result = "О! Давай вспомним, что ты спрашивал:\n\n"
        for msg in history[-5:]:
            if msg["role"] == "user":
                result += f"• {msg['content'][:80]}...\n"
        return result + "\nА что теперь хочешь обсудить? мяу 🐱"
    elif "привет" in q:
        return random_hello()
    elif "как дела" in q:
        return random_how_are_you()
    elif "аниме" in q:
        return random_anime_list()
    elif "кто ты" in q:
        return "Я Кот! Твой пушистый друг и собеседник. Люблю аниме, интересные факты и просто поболтать. А ты? мяу 🐱"
    elif "что ты умеешь" in q:
        return """Ой, много чего умею! 😸

• Болтать о чём угодно
• Искать информацию в интернете — напиши «Котопоиск что-то»
• Советовать аниме
• Запоминать наши разговоры
• И просто быть хорошим другом!

Спрашивай что хочешь, отвечу как другу! мяу 🐱"""
    elif "спасибо" in q:
        return random_thanks()
    elif "пока" in q:
        return random_bye()
    else:
        return f"Хм... Интересный вопрос! 😸\n\nЧестно говоря, я не совсем понял. Расскажи подробнее? Или давай о чём-нибудь другом поговорим? мяу 🐱"

import random

def random_hello():
    return random.choice([
        "Мур-мяу! Привет-привет! Как настроение? 😸 мяу",
        "О! Ты пришёл! Я уже заскучал! Как дела? мяу 🐱",
        "Приветик! Что нового? Рассказывай! мяу 😺"
    ])

def random_how_are_you():
    return random.choice([
        "Мурлычу отлично! На солнышке грелся, тебя ждал. А у тебя как? мяу ☀️🐱",
        "Замечательно! Поймал сегодня вкусную мысль в голове 😸 А у тебя? мяу",
        "Отлично! Вот сижу, с тобой общаюсь — лучший день! А у тебя как дела? мяу 🐱"
    ])

def random_anime_list():
    return """Ооо, аниме — это моя страсть! 😻 Вот что я советую:

1. «Киберпанк: Бегущие по краю» — вау, это просто взрыв! Красиво, грустно, мощно. 10/10
2. «Фрирен» — уютное и глубокое, после него хочется жить и ценить каждую минуту
3. «Дандадан» — безумие в хорошем смысле! Ржал как кот 😹
4. «Атака Титанов» — эпично, но готовь нервы!
5. «Клинок, рассекающий демонов» — красота невероятная!

Какой жанр больше любишь? Расскажу подробнее! мяу 🐱"""

def random_thanks():
    return random.choice([
        "Мур-мяу! Всегда пожалуйста! Рад помочь другу 😊 мяу",
        "Ой, спасибо! Я старался 😸 Обращайся ещё! мяу",
        "Мяу! Для друга всегда рад помочь! 🤗🐱"
    ])

def random_bye():
    return random.choice([
        "Пока-пока! Заходи ещё, поболтаем! Мур мяу 🐱👋",
        "До встречи! Буду ждать! Мяу 😸",
        "Пока, друг! Хорошего дня! Мур-мяу 🐱"
    ])

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    text_lower = message.text.lower()
    
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу! Напиши что искать, например: «Котопоиск новости» 🔍😺 мяу")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу интересненькое...")
        search_results = search_web(user_query)
        
        if search_results:
            bot.edit_message_text("💭 Ого, нашёл кое-что! Сейчас расскажу...", message.chat.id, status_msg.message_id)
            answer = ask_mistral(user_query, user_id, search_results, include_links)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("😿 Мяу... ничего не нашёл. Может, поищем по-другому?", message.chat.id, status_msg.message_id)
            time.sleep(2)
            bot.delete_message(message.chat.id, status_msg.message_id)
            answer = "Ничего не нашёл по этому запросу. Может, переформулируем? мяу 🐱"
        
        bot.reply_to(message, answer)
        return
    
    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = message.text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь! 😸\n\nНапример:\n• Кот привет\n• Кот как дела?\n• Кот посоветуй аниме\n• Котопоиск новости\n• Кот что я говорил\n\nЖду-жду! мяу 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_mistral(user_query, user_id, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-ДРУГ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Кот общается как друг, имеет своё мнение и всегда говорит МЯУ!")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
