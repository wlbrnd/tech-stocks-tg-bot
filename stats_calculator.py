import sqlite3

import pandas as pd

# Рассчет статистику по акциям за период
def calculate_stock_stats(ticker, start_date, end_date):

    try:
        conn = sqlite3.connect('stocks.db')

        query = """
        SELECT Date, Open, High, Low, Close, Volume
        FROM stock_prices
        WHERE Ticker = ? AND Date BETWEEN ? AND ?
        ORDER BY Date
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=[ticker, start_date, end_date],
        )
        conn.close()

        if df.empty:
            return None, "❌ Данные не найдены"

        # Основная статистика
        stats = {
            'period_start': df['Date'].iloc[0],
            'period_end': df['Date'].iloc[-1],
            'start_price': df['Close'].iloc[0],
            'end_price': df['Close'].iloc[-1],
            'price_change': df['Close'].iloc[-1] - df['Close'].iloc[0],
            'price_change_percent': (
                (df['Close'].iloc[-1] - df['Close'].iloc[0])
                / df['Close'].iloc[0]
            ) * 100,
            'average_price': df['Close'].mean(),
            'min_price': df['Close'].min(),
            'max_price': df['Close'].max(),
            'volatility': df['Close'].std(),
            'total_volume': df['Volume'].sum(),
            'days_count': len(df)
        }

        return stats, "✅ Статистика рассчитана"

    except Exception as e:
        print(f"Ошибка расчета статистики: {e}")
        return None, f"❌ Ошибка расчета: {e}"

# Форматирование статистики в красивое сообщение
def format_stats_message(stats, ticker):

    if not stats:
        return "❌ Не удалось рассчитать статистику"

    message = f"📊 Статистика {ticker}\n\n"
    message += f"Период: {stats['period_start']} - {stats['period_end']}\n"
    message += (
        f"Изменение цены: ${stats['price_change']:.2f} "
        f"({stats['price_change_percent']:.1f}%)\n"
    )
    message += f"Начальная цена: ${stats['start_price']:.2f}\n"
    message += f"Конечная цена: ${stats['end_price']:.2f}\n"
    message += f"Минимум: ${stats['min_price']:.2f}\n"
    message += f"Максимум: ${stats['max_price']:.2f}\n"
    message += f"Средняя цена: ${stats['average_price']:.2f}\n"
    message += f"Волатильность: ${stats['volatility']:.2f}\n"
    message += f"Общий объем: {stats['total_volume']:,}\n"
    message += f"Торговых дней: {stats['days_count']}"

    # Определение тренда
    if stats['price_change'] > 0:
        message += "\n\n📈 Тренд: РОСТ 🟢"
    elif stats['price_change'] < 0:
        message += "\n\n📉 Тренд: ПАДЕНИЕ 🔴"
    else:
        message += "\n\n➡️ Тренд: СТАБИЛЬНЫЙ ⚪"

    return message
