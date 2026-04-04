# news.py - модуль новостей
import requests
import logging
import os

logger = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def get_news(topic=None, limit=5):
    """Получает новости через NewsAPI"""
    try:
        if not NEWS_API_KEY:
            return "❌ Новости не настроены. Добавь NEWS_API_KEY в переменные Railway 🐱"
        
        if topic:
            query = topic
        else:
            query = "россия"
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "ru",
            "sortBy": "publishedAt",
            "pageSize": limit,
            "apiKey": NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            
            if not articles:
                return f"📰 Новостей по запросу '{topic}' не найдено 🐱"
            
            result = f"📰 **Новости по запросу '{topic or 'россия'}':**\n\n"
            for i, article in enumerate(articles[:limit], 1):
                title = article.get("title", "Без заголовка")
                source = article.get("source", {}).get("name", "Неизвестный источник")
                url = article.get("url", "")
                result += f"{i}. **{title}**\n📌 {source}\n🔗 {url}\n\n"
            
            return result + "🐱"
        else:
            return "❌ Ошибка получения новостей. Попробуй позже. 🐱"
    except Exception as e:
        logger.error(f"Ошибка новостей: {e}")
        return "❌ Ошибка! Попробуй ещё раз 🐱"
