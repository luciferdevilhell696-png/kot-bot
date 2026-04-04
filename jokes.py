# jokes.py - модуль шуток
import requests
import random
import logging

logger = logging.getLogger(__name__)

def get_joke():
    """Получает случайную шутку через JokeAPI"""
    try:
        # Используем русские шутки с JokeAPI
        url = "https://v2.jokeapi.dev/joke/Any?lang=ru&type=single"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("error"):
                return get_local_joke()
            joke = data.get("joke", "")
            if joke:
                return f"😂 {joke}\n\n🐱"
        
        return get_local_joke()
    except Exception as e:
        logger.error(f"Ошибка шуток: {e}")
        return get_local_joke()

def get_local_joke():
    """Локальные шутки (на случай, если API не работает)"""
    jokes = [
        "Почему программисты путают Хэллоуин и Рождество? Потому что 31 Oct = 25 Dec!",
        "Что говорит один бит другому? — Меня подташнивает!",
        "— Алло, это техподдержка? — Да. — У меня клавиатура не работает. — А вы пробовали перезагрузить компьютер?",
        "Сколько программистов нужно, чтобы закрутить лампочку? Ни одного, это аппаратная проблема.",
        "— Дорогой, ты меня любишь? — Переменная не объявлена."
    ]
    return f"😂 {random.choice(jokes)}\n\n🐱"
