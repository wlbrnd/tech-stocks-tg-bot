import logging
import os
import sqlite3

import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai_analyzer import generate_ai_analysis
from chart_generator import generate_stock_chart
from google_parser import parse_with_google_ai
from stats_calculator import calculate_stock_stats, format_stats_message


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения")


# Инициализирую базы данных
def init_database():
    data_path = "tech_stocks_2024_cleaned.csv"
    
    if not os.path.exists(data_path):
        logging.error(f"CSV с данными не найден: {data_path}")
        raise FileNotFoundError(f"Не найден файл данных: {data_path}")

    conn = sqlite3.connect('stocks.db')
    df = pd.read_csv(data_path)
    df.to_sql('stock_prices', conn, if_exists='replace', index=False)
    conn.close()
    print("База данных создана")


# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для анализа акций технологических компаний за "
        "2024 год! 📈\n\n"
        "Для начала напиши запрос, например:\n"
        "• 'Покажи график Apple за март'\n"
        "• 'Анализ Циско в период с апреля по август'\n"
        "• 'Статистика NVIDIA за первое полугодие'"
    )


# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я понимаю запросы на естественном языке:\n"
        "• График [компания] за [период]\n"
        "• Анализ [компания] за [период]\n"
        "• Статистика [компания] за [период]\n\n"
        "Пример: 'Покажи график Apple за март 2024'"
    )

# Формирование ответа на запрос
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    await update.message.reply_chat_action(action="typing")
    parsed_query = parse_with_google_ai(user_message)

    ticker = parsed_query.get('ticker')
    start_date = parsed_query.get('start_date')
    end_date = parsed_query.get('end_date')
    request_type = parsed_query.get('request_type', 'unknown')

    response = "🤖 Анализирую через AI...\n\n"
    response += f"Тикер: {ticker or 'не указан'}\n"
    response += f"Период: {start_date or '?'} - {end_date or '?'}\n"
    response += f"Тип запроса: {request_type}\n\n"

    if ticker and start_date:
        # Для графиков
        if request_type == 'graph':
            await update.message.reply_text("Строю график...")
            filename, chart_message = generate_stock_chart(
                ticker,
                start_date,
                end_date,
            )

            if filename and os.path.exists(filename):
                with open(filename, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=chart_message,
                    )
                os.remove(filename)
            else:
                await update.message.reply_text(f"❌ {chart_message}")

        # Для статистики
        elif request_type == 'stats':
            stats, stats_message = calculate_stock_stats(
                ticker,
                start_date,
                end_date,
            )
            if stats:
                stats_text = format_stats_message(stats, ticker)
                await update.message.reply_text(stats_text)
            else:
                await update.message.reply_text(f"❌ {stats_message}")

        # Для аналитики (в начале сводка статистики)
        elif request_type == 'analysis':
            stats, stats_message = calculate_stock_stats(
                ticker,
                start_date,
                end_date,
            )
            if stats:

                stats_text = format_stats_message(stats, ticker)
                await update.message.reply_text(stats_text)

                await update.message.reply_chat_action(action="typing")
                await update.message.reply_text("🧠 Генерирую AI-аналитику...")

                analysis_text = generate_ai_analysis(
                    ticker,
                    start_date,
                    end_date,
                )
                await update.message.reply_text(analysis_text)
            else:
                await update.message.reply_text(f"❌ {stats_message}")

        else:
            stats, stats_message = calculate_stock_stats(
                ticker,
                start_date,
                end_date,
            )
            if stats:
                stats_text = format_stats_message(stats, ticker)
                await update.message.reply_text(stats_text)
            else:
                await update.message.reply_text(f"❌ {stats_message}")

    elif parsed_query.get('ticker'):
        response += (
            "✅ Запрос распознан! Уточни что хочешь:\n"
            "• 'график Apple за март'\n"
            "• 'статистика Tesla'\n"
            "• 'анализ NVIDIA'"
        )
        await update.message.reply_text(response)
    else:
        response += (
            "❌ Укажи компанию: Apple, Microsoft, Google, NVIDIA, AMD, Adobe, "
            "Cisco, Salesforce, Uber, Zoom, Logitech, Philips, ZI"
        )
        await update.message.reply_text(response)


# Основная функция
def main():
    try:

        if not BOT_TOKEN:
            logging.error("BOT_TOKEN не установлен.")
            return

        init_database()
        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        logging.info("Бот запущен на сервере...")
        app.run_polling()
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")


if __name__ == "__main__":
    main()
