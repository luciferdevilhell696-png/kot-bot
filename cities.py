# cities.py - модуль игры в города
import random
import logging

logger = logging.getLogger(__name__)

city_games = {}
CITIES_DB = {}

def load_cities_from_file(filename="городада.txt"):
    global CITIES_DB
    cities_db = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                city = line.strip()
                if not city:
                    continue
                first_letter = city[0].lower()
                if first_letter not in cities_db:
                    cities_db[first_letter] = []
                cities_db[first_letter].append(city)
        logger.info(f"Загружено городов: {sum(len(v) for v in cities_db.values())}")
        CITIES_DB = cities_db
        return cities_db
    except Exception as e:
        logger.error(f"Ошибка загрузки городов: {e}")
        return {}

def get_city_by_letter(letter, used_cities):
    cities = CITIES_DB.get(letter, [])
    available = [c for c in cities if c.lower() not in used_cities]
    return random.choice(available) if available else None

def get_last_letter(city):
    last = city[-1].lower()
    if last in ['ь', 'ъ', 'ы'] and len(city) > 1:
        return city[-2].lower()
    return last

def check_city_in_db(city_name, used_cities):
    city_lower = city_name.lower()
    first_letter = city_name[0].lower()
    if first_letter not in CITIES_DB:
        return False, f"Нет городов на букву {first_letter.upper()} 😿"
    for c in CITIES_DB[first_letter]:
        if c.lower() == city_lower:
            if city_lower in used_cities:
                return False, f"Город {city_name} уже был! 🐱"
            return True, "OK"
    return False, f"Не знаю города {city_name} 😿"

def start_city_game(user_id):
    if not CITIES_DB:
        return "❌ База городов не загружена! 🐱"
    start_cities = CITIES_DB.get("м", [])
    if not start_cities:
        for letter, cities in CITIES_DB.items():
            if cities:
                start_cities = cities
                break
    start_city = random.choice(start_cities)
    last_letter = get_last_letter(start_city)
    city_games[user_id] = {
        "last_letter": last_letter,
        "used_cities": [start_city.lower()],
        "user_cities_count": 0
    }
    return f"🎮 Играем в города! Я называю {start_city}. Тебе на букву {last_letter.upper()}. Твой ход! 🐱"

def bot_make_move(user_id):
    game = city_games[user_id]
    bot_city = get_city_by_letter(game["last_letter"], game["used_cities"])
    if bot_city:
        game["used_cities"].append(bot_city.lower())
        game["last_letter"] = get_last_letter(bot_city)
        return bot_city
    return None
