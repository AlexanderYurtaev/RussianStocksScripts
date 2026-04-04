"""
График P/E и цены акции Северстали (CHMF) с поквартальной прибылью.

Как пользоваться:
1. Внесите чистую прибыль по кварталам в словарь NET_INCOME_BY_QUARTER
   (ключ: (год, квартал), значение: млрд RUB)
2. Запустите скрипт — всё остальное (цена, акции, график) автоматически.
"""

import json
import os
import urllib.request
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# =============================================================================
# Чистая прибыль Северстали по кварталам (млрд RUB, МСФО)
# Ключ: (год, квартал), значение: млрд RUB
# Заполняйте по мере появления данных из отчётов:
# https://severstal.com/rus/ir/indicators-reporting/financial-results/
# =============================================================================
NET_INCOME_BY_QUARTER = {
    (2023, 2): 105.27,
    (2023, 3): 0.0,
    (2023, 4): 88.6,
    (2024, 1): 47.41,
    (2024, 2): 35.9,
    (2024, 3): 35.01,
    (2024, 4): 31.22,
    (2025, 1): 21.07,
    (2025, 2): 15.67,
    (2025, 3): 12.99,
    (2025, 4): -17.74,
    # Добавляйте новые кварталы сюда:
    # (2026, 1): XX.X,
}

# Акции в обращении — загружаются автоматически с Moex ISS.
# Если не загрузятся, используется запасное значение:
SHARES_OUTSTANDING_FALLBACK = 837_718_660

# Целевой P/E
TARGET_PE = 7

# Период
START_DATE = "2023-04-01"
END_DATE = "2026-04-04"


def fetch_shares_outstanding():
    """Получить количество акций в обращении с Moex ISS."""
    url = "https://iss.moex.com/iss/engines/stock/markets/shares/securities/CHMF.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        securities = data.get("securities", {})
        if "data" not in securities or "columns" not in securities:
            return None
        columns = securities["columns"]
        for row in securities["data"]:
            row_dict = dict(zip(columns, row))
            if row_dict.get("BOARDID") == "TQBR":
                issue_size = row_dict.get("ISSUESIZE")
                if issue_size is not None:
                    return int(issue_size)
    except Exception as e:
        print(f"Не удалось получить кол-во акций с Moex: {e}")
    return None


def date_to_quarter(dt):
    """Определить квартал по дате."""
    month = dt.month
    quarter = (month - 1) // 3 + 1
    return dt.year, quarter


def get_ttm_net_income(dt):
    """
    Рассчитать TTM (trailing twelve months) чистую прибыль.

    Для даты из прошлого — берём сумму 4 кварталов, заканчивающихся
    кварталом этой даты. Если данных для этого квартала нет (будущее),
    откатываемся назад до последнего известного квартала.
    """
    year, quarter = date_to_quarter(dt)

    # Пытаемся найти TTM от текущего квартала, откатываясь назад
    # если текущего квартала нет в данных
    for attempt in range(8):  # до 8 откатов (= 2 года назад)
        q = quarter - attempt
        y = year
        while q < 1:
            q += 4
            y -= 1

        ttm_sum = 0.0
        count = 0
        for q_offset in range(4):
            qq = q - q_offset
            yy = y
            while qq < 1:
                qq += 4
                yy -= 1
            key = (yy, qq)
            val = NET_INCOME_BY_QUARTER.get(key)
            if val is not None:
                ttm_sum += val
                count += 1

        if count == 4:
            return ttm_sum  # Нашли полные 4 квартала

    return None  # Недостаточно данных


def fetch_history():
    """Получить ВСЕ исторические цены CHMF с Moex ISS (с пагинацией)."""
    base_url = (
        f"https://iss.moex.com/iss/history/engines/stock/markets/shares"
        f"/securities/CHMF.json?from={START_DATE}&til={END_DATE}&board=TQBR"
    )
    all_rows = []
    columns = None
    start = 0

    while True:
        url = f"{base_url}&start={start}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        history = data.get("history", {})
        if columns is None:
            columns = history.get("columns", [])
        all_rows.extend(history.get("data", []))

        cursor = data.get("history.cursor", {})
        if not cursor.get("data"):
            break
        cursor_data = cursor["data"][0]
        cursor_cols = cursor.get("columns", [])
        idx_map = dict(zip(cursor_cols, cursor_data))
        total = idx_map.get("TOTAL", 0)

        if len(all_rows) >= total:
            break
        start += 100

    return {"columns": columns, "data": all_rows}


def parse_history(data):
    """Распарсить историю цен."""
    columns = data.get("columns", [])
    rows = data.get("data", [])
    if not rows:
        return [], []
    dates = []
    closes = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        date_str = row_dict.get("TRADEDATE")
        close = row_dict.get("CLOSE")
        if date_str and close is not None:
            dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            closes.append(float(close))
    return dates, closes


def calculate_pe_over_time(dates, closes):
    """Рассчитать P/E для каждой даты на основе TTM прибыли."""
    pe_values = []
    ttm_values = []
    for dt, price in zip(dates, closes):
        ttm = get_ttm_net_income(dt)
        if ttm is not None and ttm > 0:
            ttm_rub = ttm * 1_000_000_000
            eps = ttm_rub / SHARES_OUTSTANDING
            pe = price / eps
            pe_values.append(pe)
            ttm_values.append(ttm)
        else:
            pe_values.append(None)
            ttm_values.append(None)
    return pe_values, ttm_values


def plot_chart(dates, closes, pe_values, ttm_values, output_path):
    """Построить двойной график и сохранить в файл."""
    fig, ax1 = plt.subplots(figsize=(16, 8))

    # --- Цена (левая ось) ---
    color_price = "#1f77b4"
    ax1.set_xlabel("Дата", fontsize=12)
    ax1.set_ylabel("Цена акции (RUB)", color=color_price, fontsize=12)
    ax1.plot(dates, closes, color=color_price, linewidth=1.5, label="Цена CHMF")
    ax1.tick_params(axis="y", labelcolor=color_price)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left")

    # --- P/E (правая ось) ---
    color_pe = "#ff7f0e"
    ax2 = ax1.twinx()
    ax2.set_ylabel("P/E Ratio (TTM)", color=color_pe, fontsize=12)
    ax2.axhline(
        y=TARGET_PE,
        color="red",
        linestyle="--",
        linewidth=1,
        alpha=0.6,
        label=f"P/E = {TARGET_PE} (цель)",
    )
    ax2.plot(dates, pe_values, color=color_pe, linewidth=1.5, label="P/E (TTM)")
    ax2.tick_params(axis="y", labelcolor=color_pe)
    ax2.legend(loc="upper right")

    # --- Форматирование ---
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()

    # Информация о кварталах
    q_info = "\n".join(
        f"  {y}Q{q}: {v} млрд" for (y, q), v in sorted(NET_INCOME_BY_QUARTER.items())
    )
    plt.title(
        f"Северсталь (CHMF) — Цена и P/E (TTM)\n"
        f"{START_DATE[:7]} → {END_DATE[:7]}\n"
        f"Квартальная прибыль:\n{q_info}",
        fontsize=11,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"График сохранён: {output_path}")
    plt.close()


def main():
    global SHARES_OUTSTANDING

    # --- Кол-во акций с Moex ---
    shares = fetch_shares_outstanding()
    if shares:
        SHARES_OUTSTANDING = shares
        print(f"Акции в обращении (Moex): {SHARES_OUTSTANDING:,}")
    else:
        SHARES_OUTSTANDING = SHARES_OUTSTANDING_FALLBACK
        print(f"Акции в обращении (fallback): {SHARES_OUTSTANDING:,}")

    # --- История цен ---
    print("Загрузка исторических данных с Moex...")
    data = fetch_history()
    dates, closes = parse_history(data)

    if not dates:
        print("Ошибка: не удалось получить исторические данные.")
        return

    print(f"Получено {len(dates)} торговых дней.")
    print("Расчёт P/E (TTM)...")
    pe_values, ttm_values = calculate_pe_over_time(dates, closes)

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "severstal_pe_quarterly.png",
    )
    print("Построение графика...")
    plot_chart(dates, closes, pe_values, ttm_values, output_path)

    # --- Статистика ---
    valid_pe = [pe for pe in pe_values if pe is not None]
    if valid_pe:
        print(f"\nP/E min: {min(valid_pe):.2f}")
        print(f"P/E max: {max(valid_pe):.2f}")
        print(f"P/E avg: {sum(valid_pe) / len(valid_pe):.2f}")
        print(f"P/E текущий: {valid_pe[-1]:.2f}")

    # Показать последние TTM
    valid_ttm = [t for t in ttm_values if t is not None]
    if valid_ttm:
        print(f"\nTTM min: {min(valid_ttm):.1f} млрд")
        print(f"TTM max: {max(valid_ttm):.1f} млрд")
        print(f"TTM текущий: {valid_ttm[-1]:.1f} млрд")


if __name__ == "__main__":
    main()
