# weather.py - погода через WeatherAPI.com (исправленная)
import requests
import logging
import os

logger = logging.getLogger(__name__)

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather(city_name):
    """Получает погоду для города через WeatherAPI.com"""
    try:
        if not WEATHER_API_KEY:
            return "❌ Погода не настроена. Добавь WEATHER_API_KEY в переменные Railway 🐱"
        
        # 1. Сначала пробуем прямой запрос к WeatherAPI (без геокодера)
        direct_url = "http://api.weatherapi.com/v1/forecast.json"
        direct_params = {
            "key": WEATHER_API_KEY,
            "q": city_name,
            "days": 3,
            "lang": "ru",
            "aqi": "no"
        }
        direct_response = requests.get(direct_url, params=direct_params, timeout=15)
        
        # Если прямой запрос сработал — используем его
        if direct_response.status_code == 200:
            data = direct_response.json()
            location = data["location"]
            current = data["current"]
            forecast = data["forecast"]["forecastday"]
            
            result = format_weather_response(location, current, forecast)
            return result
        
        # 2. Если прямой запрос не сработал (404) — пробуем геокодер
        geo_url = "https://nominatim.openstreetmap.org/search"
        geo_params = {
            "q": city_name,
            "format": "json",
            "limit": 3,
            "accept-language": "ru"
        }
        geo_response = requests.get(geo_url, params=geo_params, headers={"User-Agent": "KotBot/1.0"}, timeout=10)
        
        if geo_response.status_code != 200 or not geo_response.json():
            return f"❌ Город '{city_name}' не найден. Проверь название 🐱"
        
        # Берём первый результат с самым высоким рейтингом (обычно главный город)
        cities = geo_response.json()
        
        # Фильтруем: предпочитаем города без запятых в названии или с country = "Россия"
        best_city = None
        for city in cities:
            display_name = city.get("display_name", "")
            # Если название точно совпадает с запросом (без учёта регистра)
            if city.get("name", "").lower() == city_name.lower():
                best_city = city
                break
            # Если в отображаемом имени нет запятых (просто название города)
            if display_name.count(",") <= 2:
                best_city = city
        
        if not best_city:
            best_city = cities[0]
        
        lat = best_city["lat"]
        lon = best_city["lon"]
        city_display = best_city.get("name", city_name)
        
        # Запрос погоды по координатам
        weather_params = {
            "key": WEATHER_API_KEY,
            "q": f"{lat},{lon}",
            "days": 3,
            "lang": "ru",
            "aqi": "no"
        }
        weather_response = requests.get(direct_url, params=weather_params, timeout=15)
        
        if weather_response.status_code != 200:
            return "❌ Ошибка получения погоды. Попробуй позже. 🐱"
        
        data = weather_response.json()
        location = data["location"]
        current = data["current"]
        forecast = data["forecast"]["forecastday"]
        
        # Подменяем название города на то, что ввёл пользователь
        location["name"] = city_display
        
        result = format_weather_response(location, current, forecast)
        return result
        
    except Exception as e:
        logger.error(f"Ошибка погоды: {e}")
        return "❌ Ошибка! Попробуй ещё раз 🐱"

def format_weather_response(location, current, forecast):
    """Форматирует ответ с погодой"""
    result = f"""🌤️ **Погода в {location['name']}, {location['country']}**

📅 {current['last_updated'].split(' ')[0]}

🌡️ **Сейчас:** {current['temp_c']}°C (ощущается как {current['feelslike_c']}°C)
📖 {current['condition']['text']}
💧 Влажность: {current['humidity']}%
💨 Ветер: {current['wind_kph']} км/ч
🎯 Давление: {round(current['pressure_mb'] * 0.750062)} мм рт.ст.
👁️ Видимость: {current['vis_km']} км
☀️ УФ-индекс: {current['uv']}

🌅 Восход: {forecast[0]['astro']['sunrise']} | Закат: {forecast[0]['astro']['sunset']}

📊 **Сегодня:**
🌡️ {forecast[0]['day']['avgtemp_c']}°C (мин: {forecast[0]['day']['mintemp_c']}°C, макс: {forecast[0]['day']['maxtemp_c']}°C)
📖 {forecast[0]['day']['condition']['text']}

"""
    if len(forecast) > 1:
        result += f"""📆 **Завтра:**
🌡️ {forecast[1]['day']['avgtemp_c']}°C (мин: {forecast[1]['day']['mintemp_c']}°C, макс: {forecast[1]['day']['maxtemp_c']}°C)
📖 {forecast[1]['day']['condition']['text']}

"""
    
    result += "🐱"
    return result
