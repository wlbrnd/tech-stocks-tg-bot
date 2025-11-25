import sqlite3

import matplotlib.pyplot as plt
import pandas as pd


def generate_stock_chart(ticker, start_date, end_date):
    # Генерация графика цен акций (сохраняется как изображение)
    try:
        conn = sqlite3.connect('stocks.db')

        query = """
        SELECT Date, Close
        FROM stock_prices
        WHERE Ticker = ? AND Date BETWEEN ? AND ?
        ORDER BY Date
        """

        df = pd.read_sql_query(
            query, conn, params=[ticker, start_date, end_date]
        )
        conn.close()

        if df.empty:
            return None, "❌ Данные не найдены для указанного периода"

        df['Date'] = pd.to_datetime(df['Date'])

        plt.figure(figsize=(12, 6))
        plt.plot(
            df['Date'],
            df['Close'],
            linewidth=2,
            color='blue',
            marker='o',
            markersize=3,
        )
        plt.title(
            f'Цены акций {ticker} ({start_date} - {end_date})',
            fontsize=14,
            fontweight='bold',
        )
        plt.xlabel('Дата')
        plt.ylabel('Цена закрытия ($)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        filename = f"chart_{ticker}_{start_date}_{end_date}.png"
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.close()

        return (
            filename,
            f"📈 График {ticker} за период {start_date} - {end_date}",
        )

    except Exception as e:
        print(f"Ошибка генерации графика: {e}")
        return None, f"❌ Ошибка при построении графика: {e}"
