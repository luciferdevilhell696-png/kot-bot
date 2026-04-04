# currency.py - модуль курсов валют
import requests
import logging

logger = logging.getLogger(__name__)

def get_currency():
    """Получает курсы валют (USD, EUR) через API Центробанка"""
    try:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            valute = data.get("Valute", {})
            
            usd = valute.get("USD", {})
            eur = valute.get("EUR", {})
            cny = valute.get("CNY", {})
            
            result = f"""💱 **Курсы валют (ЦБ РФ):**

🇺🇸 USD: {usd.get('Value', '?')} ₽
🇪🇺 EUR: {eur.get('Value', '?')} ₽
🇨🇳 CNY: {cny.get('Value', '?')} ₽

📅 {data.get('Date', '?').split('T')[0]}

🐱"""
            return result
        else:
            return "❌ Ошибка получения курсов валют. Попробуй позже. 🐱"
    except Exception as e:
        logger.error(f"Ошибка курсов валют: {e}")
        return "❌ Ошибка! Попробуй ещё раз 🐱"
