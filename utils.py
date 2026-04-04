# utils.py - вспомогательные функции
import requests
import datetime
import logging

logger = logging.getLogger(__name__)

def get_exact_datetime(timezone="Europe/Moscow"):
    """Получает точную дату через worldtimeapi.org"""
    try:
        url = f"http://worldtimeapi.org/api/timezone/{timezone}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            datetime_str = data.get("datetime", "")
            if datetime_str:
                date_part = datetime_str.split("T")[0]
                year, month, day = date_part.split("-")
                return int(year), int(month), int(day)
        now = datetime.datetime.now()
        return now.year, now.month, now.day
    except Exception as e:
        logger.error(f"Ошибка получения даты: {e}")
        now = datetime.datetime.now()
        return now.year, now.month, now.day

def search_web(query, searxng_url):
    """Поиск в интернете через SearxNG"""
    try:
        response = requests.get(searxng_url, params={
            "q": query, "format": "json", "language": "ru", "limit": 5
        }, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return [{
                    "title": r.get("title", "Без названия"),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:800]
                } for r in results[:5]]
        return None
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        return None
