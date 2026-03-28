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
MAX_MEMORY = 30

SYSTEM_PROMPT = """Ты — кот-помощник по имени Кот. Отвечай дружелюбно на русском языке.

Правила:
1. Отвечай на русском языке
2. Добавляй "мяу" в конце
3. Отвечай максимально подробно и развёрнуто, не ограничивай себя
4. Можешь давать списки, описания, советы
5. Помни контекст разговора"""

def add_to_memory(user_id, role, content):
    user_memory[user_id].append({"role": role, "content": content})
    if len(user_memory[user_id]) > MAX_MEMORY:
        user_memory[user_id].pop(0)

def clear_memory(user_id):
    user_memory[user_id] = []
    return "Мяу! Я всё забыл. Начинаем с чистого листа! 🐱"

def get_user_memory(user_id):
    return user_memory[user_id]

def search_web(query):
    try:
        print(f"🔍 Поиск: {query}")
        response = requests.get(SEARXNG_URL, params={
            "q": query,
            "format": "json",
            "language": "ru",
            "limit": 15
        }, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                print(f"✅ Найдено {len(results)} результатов")
                return [{
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")
                } for r in results[:15]]
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
        
        for msg in history[-15:]:
            messages.append(msg)
        
        if search_results:
            context = "\n\n".join([
                f"📌 {r['title']}\n{r['content']}" for r in search_results[:10]
            ])
            
            if include_links:
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь максимально подробно и развёрнуто на основе этой информации. Составь полный список, подробные описания. В конце обязательно добавь ссылки на все источники."""
            else:
                enhanced_question = f"""{question}

Информация из интернета:
{context}

Ответь максимально подробно и развёрнуто на основе этой информации. Составь полный список, подробные описания. НЕ добавляй ссылки, только текст ответа."""
            messages.append({"role": "user", "content": enhanced_question})
        else:
            messages.append({"role": "user", "content": question})

        payload = {
            "model": "mistral-small-latest",
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 4000
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            add_to_memory(user_id, "user", question[:500])
            add_to_memory(user_id, "assistant", answer[:1000])
            
            if include_links and search_results:
                links = "\n\n📌 Источники:\n" + "\n".join([r["url"] for r in search_results[:5]])
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
    add_to_memory(user_id, "user", question[:300])

    if search_results:
        if include_links:
            reply = "Мяу! Вот что я нашёл:\n\n"
            for r in search_results[:8]:
                reply += f"📌 {r['title']}\n{r['url']}\n\n"
            return reply + "🐱"
        else:
            reply = "Мяу! Вот что я нашёл:\n\n"
            for r in search_results[:8]:
                reply += f"• {r['title']}\n"
            return reply + "\nЧтобы увидеть ссылки, напиши «Котопоиск +ссылка» 🐱"

    if "забудь" in q or "очисти память" in q:
        return clear_memory(user_id)
    elif "что я говорил" in q or "что я спрашивал" in q:
        history = get_user_memory(user_id)
        if not history:
            return "Мяу... Мы ещё не разговаривали. Напиши что-нибудь! 🐱"
        result = "Мяу! Вот что ты спрашивал недавно:\n\n"
        for msg in history[-8:]:
            role = "Ты" if msg["role"] == "user" else "Я"
            result += f"{role}: {msg['content'][:200]}\n"
        return result + "🐱"
    elif "привет" in q:
        return "Мур-мяу! Приветствую, друг! Как настроение? Можешь задать любой вопрос, я отвечу максимально подробно! 🐱"
    elif "как дела" in q:
        return "Мурлычу отлично! Греюсь на солнышке, жду твоих вопросов. Чем могу помочь? ☀️🐱"
    elif "аниме" in q or "посоветуй" in q:
        return """Мяу! Вот подробный список аниме с описаниями:

🎬 Киберпанк: Бегущие по краю
   Жанр: киберпанк, драма, экшн
   Студия: Trigger
   О чём: В антиутопическом будущем парень Дэвид пытается выжить в Найт-Сити, становясь киберпанком. Встречает девушку Люси и попадает в мир преступности.
   Почему стоит: Шедевр от Studio Trigger, 10/10 визуал, глубокая драма, шикарная музыка, 10 эпизодов идеального хронометража.

🎬 Фрирен: Провожающая в последний путь
   Жанр: фэнтези, драма, приключения
   Студия: Madhouse
   О чём: Эльфийка-маг Фрирен после победы над демоном понимает, что не ценила время, проведённое с друзьями-людьми. Отправляется в новое путешествие, чтобы лучше понять людей.
   Почему стоит: Глубокое философское аниме, уютная атмосфера, отличная анимация, много эмоций.

🎬 Дандадан
   Жанр: комедия, экшн, сверхъестественное
   Студия: Science SARU
   О чём: Школьник-фанат НЛО и девушка-верующая в призраков спорят, чьи убеждения верны. В процессе оба получают сверхъестественные способности.
   Почему стоит: Безумный и весёлый сюжет, отличный юмор, динамичный экшн, уникальный визуальный стиль.

🎬 Атака Титанов
   Жанр: экшн, драма, постапокалипсис
   Студия: Wit Studio → MAPPA
   О чём: Человечество живёт за огромными стенами, спасаясь от гигантских существ — титанов. История Эрена Йегера, который клянётся уничтожить всех титанов.
   Почему стоит: Эпическая история с неожиданными поворотами, глубокая проработка персонажей, морально сложные вопросы.

🎬 Клинок, рассекающий демонов
   Жанр: экшн, фэнтези, драма
   Студия: ufotable
   О чём: Танджиро Камадо становится охотником на демонов, чтобы спасти свою сестру-демона и найти лекарство.
   Почему стоит: Потрясающая анимация от ufotable, эмоциональная история, красивые боевые сцены.

🎬 Твоё имя
   Жанр: романтика, драма, фантастика
   Режиссёр: Макото Синкай
   О чём: Парень из Токио и девушка из провинции обнаруживают, что иногда меняются телами.
   Почему стоит: Шедевр Макото Синкая, невероятно красивая анимация, трогательная история любви.

🎬 Ванпанчмен
   Жанр: комедия, экшн, пародия
   Студия: Madhouse
   О чём: Сайтама — герой, который может победить любого врага одним ударом, но страдает от скуки.
   Почему стоит: Отличная пародия на супергеройский жанр, смешно, динамично, неожиданно глубоко.

🎬 Сказание о Гуррэн-Лаганн
   Жанр: меха, экшн, драма
   Студия: Gainax
   О чём: Симон и Камина бросают вызов могущественному врагу, используя гигантского меха.
   Почему стоит: Безумная энергетика, преодоление невозможного, культовое аниме.

Приятного просмотра! Если хочешь рекомендации под конкретный жанр или настроение, просто уточни! 🐱"""
    elif "кто ты" in q:
        return "Мяу! Я Кот — твой пушистый помощник! Использую Mistral AI. Могу отвечать на любые вопросы максимально подробно, искать информацию в интернете, составлять списки аниме, фильмов, книг, объяснять сложные вещи простым языком. Просто спроси меня о чём угодно! 🐱"
    elif "что ты умеешь" in q:
        return """Мяу! Я умею очень многое:

💬 Общаться — отвечаю подробно и развёрнуто на любые вопросы

🎬 Советовать аниме — составляю подробные списки с описаниями жанров, сюжетов, почему стоит смотреть

🔍 Искать в интернете — команда «Котопоиск» ищет актуальную информацию
   • «Котопоиск новости» — ответ без ссылок
   • «Котопоиск +ссылка новости» — ответ со ссылками

🧠 Запоминать разговор — помню до 30 последних сообщений
   • «Кот что я говорил» — показать историю
   • «Кот забудь всё» — очистить память

📚 Могу:
   • Объяснять сложные вещи простым языком
   • Составлять списки и рейтинги
   • Давать советы по аниме, фильмам, сериалам
   • Помогать с учебой и работой
   • Просто болтать и поднимать настроение

Просто напиши «Кот привет» и задавай любой вопрос! 🐱"""
    elif "спасибо" in q:
        return "Мур-мяу! Всегда пожалуйста! Рад помочь. Если будут ещё вопросы — спрашивай! 😊🐱"
    elif "пока" in q:
        return "Мяу! Пока-пока! Заходи ещё, буду ждать новых вопросов! 🐱👋"
    else:
        return f"Мяу... Я не совсем понял. Попробуй спросить по-другому или выбери команду:\n\n• «Кот привет»\n• «Кот посоветуй аниме»\n• «Котопоиск что-то»\n• «Кот что я говорил»\n• «Кот что ты умеешь» 🐱"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    text_lower = message.text.lower()
    
    if "котопоиск" in text_lower:
        include_links = "+ссылка" in text_lower
        
        user_query = re.sub(r'котопоиск|\+ссылка', '', text_lower).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу! Напиши что искать после «Котопоиск», например:\n\n«Котопоиск лучшие аниме 2026»\n«Котопоиск +ссылка новости» 🔍🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        status_msg = bot.send_message(message.chat.id, "🔍 Мяу... ищу в интернете...")
        search_results = search_web(user_query)
        
        if search_results:
            bot.edit_message_text("💭 Мяу... обрабатываю информацию...", message.chat.id, status_msg.message_id)
            answer = ask_mistral(user_query, user_id, search_results, include_links)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("😿 Мяу... ничего не нашёл. Попробуй переформулировать запрос!", message.chat.id, status_msg.message_id)
            time.sleep(2)
            bot.delete_message(message.chat.id, status_msg.message_id)
            answer = "Мяу... Ничего не нашёл по этому запросу. Попробуй спросить по-другому! 🐱"
        
        bot.reply_to(message, answer)
        return
    
    if "кот" in text_lower or is_reply_to_bot:
        if is_reply_to_bot and "кот" not in text_lower:
            user_query = message.text.strip()
        else:
            user_query = re.sub(r'[Кк]от[,\s]?', '', message.text).strip()
        
        if not user_query:
            bot.reply_to(message, "Мяу? Я слушаю... Напиши что-нибудь, например:\n\n«Кот привет»\n«Кот посоветуй аниме»\n«Котопоиск новости»\n«Кот что я говорил»\n«Кот что ты умеешь» 🐱")
            return
        
        bot.send_chat_action(message.chat.id, "typing")
        answer = ask_mistral(user_query, user_id, None, False)
        bot.reply_to(message, answer)

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 КОТ-БОТ С MISTRAL AI БЕЗ ОГРАНИЧЕНИЙ!")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print("Модель: Mistral Small")
    print("Длина ответов: МАКСИМАЛЬНАЯ (до 4000 токенов)")
    print("Контекст: БЕЗ ОГРАНИЧЕНИЙ")
    print("\nПоиск в интернете:")
    print("• «Котопоиск что-то» — ответ без ссылок")
    print("• «Котопоиск +ссылка что-то» — ответ со ссылками")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(15)
            print("Перезапуск...")
