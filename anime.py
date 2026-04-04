# anime.py - модуль аниме
import requests
import random
import re
import time
import json
import logging
import os
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

# Кэш
CACHE_FILE = "anime_cache.json"
CACHE_EXPIRATION = 86400

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

anime_cache = load_cache()

# Жанры
GENRE_MAP = {
    "боевик": "Action", "экшн": "Action",
    "романтика": "Romance",
    "комедия": "Comedy",
    "фэнтези": "Fantasy", "фентези": "Fantasy",
    "драма": "Drama",
    "ужасы": "Horror", "хоррор": "Horror",
    "фантастика": "Sci-Fi",
    "триллер": "Thriller",
    "детектив": "Mystery",
    "меха": "Mecha",
    "киберпанк": "Cyberpunk",
    "школа": "School",
    "спорт": "Sports",
    "психология": "Psychological",
    "мистика": "Mystery"
}

def translate_to_english(text):
    try:
        if not text or text == "???":
            return text
        if any(char.isalpha() and ord(char) < 128 for char in text):
            return text
        translator = GoogleTranslator(source='auto', target='en')
        return translator.translate(text)
    except:
        return text

def search_anime_anilist(search_query, search_type="search"):
    try:
        if search_type == "search":
            query = """
            query ($search: String) {
              Media(search: $search, type: ANIME) {
                id
                title { romaji english native }
                averageScore
                episodes
                seasonYear
                genres
                description(asHtml: false)
                siteUrl
              }
            }
            """
            variables = {"search": search_query}
        elif search_type == "random":
            query = """
            query ($page: Int, $perPage: Int, $genre: String, $year: Int) {
              Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: POPULARITY_DESC, genre: $genre, seasonYear: $year) {
                  id
                  title { romaji english native }
                  averageScore
                  episodes
                  seasonYear
                  genres
                  siteUrl
                }
              }
            }
            """
            variables = {"page": 1, "perPage": 50}
            if search_query.get("genre"):
                variables["genre"] = search_query["genre"]
            if search_query.get("year"):
                variables["year"] = int(search_query["year"])
        elif search_type == "top":
            query = """
            query ($page: Int, $perPage: Int, $genre: String, $year: Int) {
              Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: SCORE_DESC, genre: $genre, seasonYear: $year) {
                  id
                  title { romaji english native }
                  averageScore
                  episodes
                  seasonYear
                  genres
                  siteUrl
                }
              }
            }
            """
            variables = {"page": 1, "perPage": 50}
            if search_query.get("genre"):
                variables["genre"] = search_query["genre"]
            if search_query.get("year"):
                variables["year"] = int(search_query["year"])

        url = "https://graphql.anilist.co"
        response = requests.post(url, json={"query": query, "variables": variables}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if search_type == "search":
                media = data.get("data", {}).get("Media")
                if media:
                    return {"success": True, "data": [media]}
            else:
                media_list = data.get("data", {}).get("Page", {}).get("media", [])
                if media_list:
                    return {"success": True, "data": media_list}
        return {"success": False}
    except Exception as e:
        logger.error(f"Ошибка AniList: {e}")
        return {"success": False}

def get_random_anime(genres=None, year=None):
    try:
        anilist_genres = None
        if genres:
            anilist_genres = [GENRE_MAP.get(g, g.capitalize()) for g in genres if g in GENRE_MAP]
            if anilist_genres:
                anilist_genres = anilist_genres[0]

        result = search_anime_anilist({"genre": anilist_genres, "year": year}, "random")
        if not result["success"] or not result["data"]:
            if genres and year:
                return f"Не нашёл аниме в жанре {', '.join(genres)} за {year} год 😿 🐱"
            if genres:
                return f"Не нашёл аниме в жанре {', '.join(genres)} 😿 🐱"
            if year:
                return f"Не нашёл аниме за {year} год 😿 🐱"
            return "Ничего не нашёл 😿 🐱"

        anime = random.choice(result["data"])
        title = anime.get("title", {})
        name_raw = title.get("native") or title.get("english") or title.get("romaji") or "???"
        name_en = translate_to_english(name_raw)
        score = anime.get("averageScore", "?")
        if score != "?":
            score = score / 10
        episodes = anime.get("episodes", "?")
        year_anime = anime.get("seasonYear", "?")
        genres_list = ", ".join(anime.get("genres", [])[:3])

        return f"""🎲 Тебе выпало:

🎬 {name_en}
⭐ {score}/10
🎭 {genres_list}
📺 {episodes} эпизодов
📅 {year_anime} год

Приятного просмотра! 🐱"""
    except Exception as e:
        logger.error(f"Ошибка get_random_anime: {e}")
        return "Ошибка 😿 🐱"

def search_anime_by_name(anime_name):
    try:
        if anime_name in anime_cache:
            cache_time = anime_cache[anime_name].get("timestamp", 0)
            if time.time() - cache_time < CACHE_EXPIRATION:
                return anime_cache[anime_name]["result"]

        result = search_anime_anilist(anime_name, "search")
        if result["success"] and result["data"]:
            anime = result["data"][0]
            title = anime.get("title", {})
            name_raw = title.get("native") or title.get("english") or title.get("romaji") or "???"
            name_en = translate_to_english(name_raw)
            score = anime.get("averageScore", "?")
            if score != "?":
                score = score / 10
            episodes = anime.get("episodes", "?")
            year = anime.get("seasonYear", "?")
            genres = ", ".join(anime.get("genres", [])[:5])

            output = f"""🎬 {name_en}

📅 {year}
⭐ {score}/10
🎭 {genres}
📺 {episodes} эп.

🔗 https://anilist.co/anime/{anime['id']}
🐱"""

            anime_cache[anime_name] = {"result": output, "timestamp": time.time()}
            save_cache(anime_cache)
            return output
        return f"Не нашёл «{anime_name}» 😿 🐱"
    except Exception as e:
        logger.error(f"Ошибка search_anime_by_name: {e}")
        return "Ошибка! Попробуй другое название. 🐱"

def get_top_anime(genre=None, year=None, limit=10):
    try:
        cache_key = f"top_{genre}_{year}_{limit}"
        if cache_key in anime_cache:
            cache_time = anime_cache[cache_key].get("timestamp", 0)
            if time.time() - cache_time < CACHE_EXPIRATION:
                return anime_cache[cache_key]["result"]

        anilist_genre = None
        if genre:
            anilist_genre = GENRE_MAP.get(genre, genre.capitalize())

        result = search_anime_anilist({"genre": anilist_genre, "year": year}, "top")
        if not result["success"] or not result["data"]:
            if year and genre:
                return f"Не нашёл топ аниме в жанре {genre} за {year} год 😿 🐱"
            if year:
                return f"Не нашёл топ аниме за {year} год 😿 🐱"
            if genre:
                return f"Не нашёл топ аниме в жанре {genre} 😿 🐱"
            return "Ничего не нашёл 😿 🐱"

        data = result["data"][:limit]
        result_text = f"🔥 Топ-{min(limit, len(data))}"
        if genre:
            result_text += f" в жанре {genre}"
        if year:
            result_text += f" за {year} год"
        result_text += ":\n\n"

        for i, anime in enumerate(data, 1):
            title = anime.get("title", {})
            name_raw = title.get("native") or title.get("english") or title.get("romaji") or "???"
            name_en = translate_to_english(name_raw)
            score = anime.get("averageScore", "?")
            if score != "?":
                score = score / 10
            episodes = anime.get("episodes", "?")
            year_anime = anime.get("seasonYear", "?")
            result_text += f"{i}. {name_en} — {score}/10 ⭐\n"
            result_text += f"   📺 {episodes} эп. | 📅 {year_anime}\n"

        result_text += "\n🐱"
        anime_cache[cache_key] = {"result": result_text, "timestamp": time.time()}
        save_cache(anime_cache)
        return result_text
    except Exception as e:
        logger.error(f"Ошибка get_top_anime: {e}")
        return "Ошибка 😿 🐱"
