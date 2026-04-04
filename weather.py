# weather.py - погода через WeatherAPI.com
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
        
        # Получаем координаты города через Nominatim
        geo_url = "https://nominatim.openstreetmap.org/search"
        geo_params = {
            "q": city_name,
            "format": "json",
            "limit": 1,
            "accept-language": "ru"
        }
        geo_response = requests.get(geo_url, params=geo_params, headers={"User-Agent": "KotBot/1.0"}, timeout=10)
        
        if geo_response.status_code != 200:
            return "❌ Ошибка поиска города. Попробуй ещё раз. 🐱"
        
        geo_data = geo_response.json()
        if not geo_data:
            return f"❌ Город '{city_name}' не найден. Проверь название 🐱"
        
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        
        # Получаем погоду через WeatherAPI
        weather_url = "http://api.weatherapi.com/v1/forecast.json"
        weather_params = {
            "key": WEATHER_API_KEY,
            "q": f"{lat},{lon}",
            "days": 3,
            "lang": "ru",
            "aqi": "no"
        }
        weather_response = requests.get(weather_url, params=weather_params, timeout=15)
        
        if weather_response.status_code != 200:
            return "❌ Ошибка получения погоды. Попробуй позже. 🐱"
        
        data = weather_response.json()
        
        location = data["location"]
        current = data["current"]
        forecast = data["forecast"]["forecastday"]
        
        city_name_api = location["name"]
        country = location["country"]
        temp = current["temp_c"]
        feels_like = current["feelslike_c"]
        condition = current["condition"]["text"]
        humidity = current["humidity"]
        wind = current["wind_kph"]
        pressure = round(current["pressure_mb"] * 0.750062)
        visibility = current["vis_km"]
        uv = current["uv"]
        last_updated = current["last_updated"].split(" ")[0]
        
        sunrise = forecast[0]["astro"]["sunrise"]
        sunset = forecast[0]["astro"]["sunset"]
        
        day_forecast = forecast[0]["day"]
        day_temp = day_forecast["avgtemp_c"]
        max_temp = day_forecast["maxtemp_c"]
        min_temp = day_forecast["mintemp_c"]
        day_condition = day_forecast["condition"]["text"]
        
        tomorrow = forecast[1]["day"] if len(forecast) > 1 else None
        
        result = f"""🌤️ **Погода в {city_name_api}, {country}**

📅 {last_updated}

🌡️ **Сейчас:** {temp}°C (ощущается как {feels_like}°C)
📖 {condition}
💧 Влажность: {humidity}%
💨 Ветер: {wind} км/ч
🎯 Давление: {pressure} мм рт.ст.
👁️ Видимость: {visibility} км
☀️ УФ-индекс: {uv}

🌅 Восход: {sunrise} | Закат: {sunset}

📊 **Сегодня:**
🌡️ {day_temp}°C (мин: {min_temp}°C, макс: {max_temp}°C)
📖 {day_condition}

"""
        if tomorrow:
            result += f"""📆 **Завтра:**
🌡️ {tomorrow['avgtemp_c']}°C (мин: {tomorrow['mintemp_c']}°C, макс: {tomorrow['maxtemp_c']}°C)
📖 {tomorrow['condition']['text']}

"""
        
        result += "🐱"
        return result
        
    except Exception as e:
        logger.error(f"Ошибка погоды: {e}")
        return "❌ Ошибка! Попробуй ещё раз 🐱"
