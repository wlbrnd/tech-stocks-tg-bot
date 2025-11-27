from __future__ import annotations

import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def _normalize_model_name(model: str | None) -> str:

    #Убирает префикс models/ и пробелы, если имя модели скопировано из ListModels.

    if not model:
        return "gemini-2.0-flash-latest"
    cleaned = model.strip()
    if cleaned.startswith("models/"):
        cleaned = cleaned.split("models/", 1)[1]
    return cleaned


GOOGLE_MODEL = _normalize_model_name(
    os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-latest")
)

#Парсинг пользовательского запроса через Google AI Studio (Gemini).
def parse_with_google_ai(user_message):

    if not GOOGLE_API_KEY:
        print("GOOGLE_API_KEY не задан, используем fallback парсер")
        return fallback_parser(user_message)

    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GOOGLE_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    )

    system_prompt = (
        "Извлеки структуру запроса об акциях технологических компаний "
        "за 2024 год. Ответь ТОЛЬКО JSON без пояснений. Ключи: "
        "ticker (тикер), start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), "
        "request_type (graph|stats|analysis). "
        "Если чего-то нет в сообщении, оставь пустую строку или null."
    )
    user_prompt = f'Пользователь говорит: "{user_message}". Верни только JSON.'

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": system_prompt + "\n" + user_prompt}],
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
    }

    try:
        print("Отправляю запрос к Google AI Studio...")
        response = requests.post(api_url, json=payload, timeout=30)
        print(f"Статус ответа: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Ответ от Google: {result}")
            return normalize_parsed_result(
                user_message,
                parse_google_response(result, user_message),
            )

        print(f"Ошибка Google AI API: {response.text}")
        return fallback_parser(user_message)

    except Exception as e:
        print(f"Ошибка запроса к Google AI Studio: {e}")
        return fallback_parser(user_message)


# Извлечение JSON-блока из ответа Gemini.
def parse_google_response(api_response, original_message):

    try:
        candidates = api_response.get("candidates", [])
        if not candidates:
            return fallback_parser(original_message)

        text = ""
        for part in candidates[0].get("content", {}).get("parts", []):
            if "text" in part:
                text += part["text"]

        print(f"Сгенерированный текст: {text}")

        json_match = re.search(r"\{[^}]*\}", text)
        if not json_match:
            return fallback_parser(original_message)

        parsed_data = json.loads(json_match.group())
        return parsed_data

    except Exception as e:
        print(f"Ошибка парсинга ответа Google: {e}")
        return fallback_parser(original_message)

# Гарантирует наличие ключей, добавляя дефолты из fallback.
def normalize_parsed_result(user_message, parsed_data):

    base = fallback_parser(user_message)
    if not isinstance(parsed_data, dict):
        return base

    return {
        "ticker": (
            parsed_data.get("ticker")
            or parsed_data.get("symbol")
            or base["ticker"]
        ),
        "start_date": (
            parsed_data.get("start_date")
            or parsed_data.get("from")
            or base["start_date"]
        ),
        "end_date": (
            parsed_data.get("end_date")
            or parsed_data.get("to")
            or base["end_date"]
        ),
        "request_type": (
            parsed_data.get("request_type")
            or parsed_data.get("type")
            or base["request_type"]
        ),
    }

#Простой парсер на правилах, если не сработает парсинг AI.
def fallback_parser(user_message):
    companies = {
        'apple': 'AAPL', 'эпл': 'AAPL',
        'microsoft': 'MSFT', 'майкрософт': 'MSFT',
        'google': 'GOOGL', 'гугл': 'GOOGL',
        'nvidia': 'NVDA', 'нвидиа': 'NVDA',
        'amd': 'AMD', 'амд': 'AMD',
        'adobe': 'ADBE', 'адоб': 'ADBE',
        'cisco': 'CSCO', 'циско': 'CSCO',
        'salesforce': 'CRM',
        'uber': 'UBER', 'убер': 'UBER',
        'zoom': 'ZM', 'зум': 'ZM',
        'logitech': 'LOGI', 'лоджитек': 'LOGI',
        'philips': 'PHG', 'филипс': 'PHG',
        'zi': 'ZI'
    }

    lower_msg = user_message.lower()
    ticker = None
    for company, tkr in companies.items():
        if company in lower_msg:
            ticker = tkr
            break

    start_date, end_date = None, None

    months = {
        'январ': ('2024-01-01', '2024-01-31'),
        'феврал': ('2024-02-01', '2024-02-29'),
        'март': ('2024-03-01', '2024-03-31'),
        'апрел': ('2024-04-01', '2024-04-30'),
        'май': ('2024-05-01', '2024-05-31'),
        'июн': ('2024-06-01', '2024-06-30'),
        'июл': ('2024-07-01', '2024-07-31'),
        'август': ('2024-08-01', '2024-08-31'),
        'сентябр': ('2024-09-01', '2024-09-30'),
        'октябр': ('2024-10-01', '2024-10-31'),
        'ноябр': ('2024-11-01', '2024-11-30'),
        'декабр': ('2024-12-01', '2024-12-31')
    }

    for month_name, (start, end) in months.items():
        if month_name in lower_msg:
            start_date, end_date = start, end
            break

    if 'перв' in lower_msg and 'полугоди' in lower_msg:
        start_date, end_date = "2024-01-01", "2024-06-30"
    elif 'втор' in lower_msg and 'полугоди' in lower_msg:
        start_date, end_date = "2024-07-01", "2024-12-31"
    elif '1 квартал' in lower_msg or 'первый квартал' in lower_msg:
        start_date, end_date = "2024-01-01", "2024-03-31"
    elif '2 квартал' in lower_msg or 'второй квартал' in lower_msg:
        start_date, end_date = "2024-04-01", "2024-06-30"

    if start_date is None:
        start_date, end_date = "2024-01-01", "2024-12-31"

    request_type = "unknown"
    if any(word in lower_msg for word in ['график', 'покажи']):
        request_type = "graph"
    elif 'анализ' in lower_msg or 'аналитика' in lower_msg:
        request_type = "analysis"
    elif 'статистик' in lower_msg:
        request_type = "stats"

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "request_type": request_type
    }
