from __future__ import annotations

import os
import requests

from dotenv import load_dotenv

from stats_calculator import calculate_stock_stats

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def _normalize_model_name(model: str | None) -> str:
    if not model:
        return "gemini-1.5-flash"
    cleaned = model.strip()
    if cleaned.startswith("models/"):
        cleaned = cleaned.split("models/", 1)[1]
    return cleaned


GOOGLE_MODEL = _normalize_model_name(
    os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
)
GOOGLE_FALLBACK_MODEL = _normalize_model_name(
    os.getenv("GOOGLE_FALLBACK_MODEL", "gemini-1.5-flash")
)

# Аналитика через Google AI Studio (Gemini)
def generate_ai_analysis(ticker, start_date, end_date):

    stats = None
    try:
        stats, _ = calculate_stock_stats(ticker, start_date, end_date)
        if not stats:
            return "❌ Не удалось получить данные для анализа"

        if not GOOGLE_API_KEY:
            return fallback_analysis(stats, ticker)

        prompt = (
            "Дай краткий (3-4 предложения) анализ акции за указанный период. "
            "Не пиши вступлений. Формат: тренд, волатильность/риски, "
            "активность, вывод."
            f"\nТикер: {ticker}\nПериод: {start_date} - {end_date}"
            f"\nСтарт: ${stats['start_price']:.2f}, конец: "
            f"${stats['end_price']:.2f}"
            f"\nИзменение: {stats['price_change_percent']:.1f}%"
            f"\nМин/макс: ${stats['min_price']:.2f} / "
            f"${stats['max_price']:.2f}"
            f"\nСредняя: ${stats['average_price']:.2f}, волатильность: "
            f"${stats['volatility']:.2f}"
            f"\nОбъем: {stats['total_volume']:,.0f}, дней: "
            f"{stats['days_count']}"
        )

        def call_model(model_name: str, max_tokens: int = 160):
            api_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={GOOGLE_API_KEY}"
            )
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.6,
                    "maxOutputTokens": max_tokens,
                    "responseModalities": ["TEXT"],
                },
            }
            try:
                resp = requests.post(api_url, json=payload, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    text = ""
                    content = result.get("candidates", [{}])[0].get(
                        "content",
                        {},
                    )
                    for part in content.get("parts", []):
                        if "text" in part:
                            text += part["text"]
                    if text:
                        return text
                    # Логируем пустой ответ для дебага
                    if result.get("candidates"):
                        finish = result["candidates"][0].get("finishReason")
                        print(
                            f"Пустой ответ модели {model_name}, "
                            f"finishReason={finish}"
                        )
                    return None
                else:
                    print(f"Ошибка Google AI API ({model_name}): {resp.text}")
                    return None
            except Exception as err:
                print(f"Ошибка запроса к модели {model_name}: {err}")
                return None

        # Основная модель
        text = call_model(GOOGLE_MODEL, max_tokens=512)
        if text:
            return format_ai_response(text)

        # Ретрай на fallback-модель (обычно flash),
        # если основная недоступна/пустая
        if GOOGLE_FALLBACK_MODEL and GOOGLE_FALLBACK_MODEL != GOOGLE_MODEL:
            text = call_model(GOOGLE_FALLBACK_MODEL, max_tokens=384)
            if text:
                return format_ai_response(text)

        return fallback_analysis(stats, ticker)

    except Exception as e:
        print(f"Ошибка AI-анализа: {e}")
        if stats:
            return fallback_analysis(stats, ticker)
        return "❌ Не удалось сформировать аналитику"


def format_ai_response(text):
    cleaned_text = text.strip()
    if '```' in cleaned_text:
        cleaned_text = cleaned_text.replace('```', '').strip()

    return f"AI-Аналитика:\n\n{cleaned_text}"

# Запасной анализ на правилах если AI не сработал
def fallback_analysis(stats, ticker):

    analysis = "Аналитика (анализ на правилах):\n\n"

    # Анализ тренда
    change_percent = stats['price_change_percent']
    if change_percent > 10:
        analysis += (
            f"Сильный тренд - акция {ticker} выросла на "
            f"{change_percent:.1f}%, демонстрируя отличную динамику. "
        )
    elif change_percent > 2:
        analysis += (
            "↗️ Умеренный рост - "
            f"{ticker} показала позитивную динамику с ростом "
            f"{change_percent:.1f}%. "
        )
    elif change_percent > -2:
        analysis += (
            "➡️ Боковой тренд - цена колебалась в узком диапазоне "
            f"({change_percent:.1f}%). "
        )
    elif change_percent > -10:
        analysis += (
            "↘️ Коррекция - "
            f"{ticker} снизилась на {abs(change_percent):.1f}%, "
            "что может быть временной коррекцией. "
        )
    else:
        analysis += (
            "📉 Сильное падение - значительное снижение на "
            f"{abs(change_percent):.1f}% требует внимания. "
        )

    volatility = stats['volatility']
    if volatility > 8:
        analysis += "Высокая волатильность указывает на повышенные риски. "
    elif volatility > 3:
        analysis += (
            "Умеренная волатильность соответствует рыночным ожиданиям. "
        )
    else:
        analysis += "Низкая волатильность говорит о стабильности. "

    avg_volume = stats['total_volume'] / stats['days_count']
    if avg_volume > 50000000:
        analysis += "Высокие объемы торгов подтверждают интерес инвесторов. "
    else:
        analysis += "Объемы торгов в рамках средних значений. "

    if change_percent > 5 and volatility < 5:
        analysis += "📊 Вывод: Перспективная динамика с управляемыми рисками."
    elif change_percent < -5:
        analysis += (
            "📊 Вывод: Требуется осторожность из-за негативной динамики."
        )
    else:
        analysis += "📊 Вывод: Нейтральная картина, рекомендуется мониторинг."

    return analysis
