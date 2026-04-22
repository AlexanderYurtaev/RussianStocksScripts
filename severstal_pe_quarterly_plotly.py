"""
Интерактивный график P/E и цены акции Северстали (CHMF) с поквартальной прибылью.
Использует Plotly для интерактивности (наведение, зум, выделение).

Как пользоваться:
1. Внесите чистую прибыль по кварталам в словарь NET_INCOME_BY_QUARTER
   (ключ: (год, квартал), значение: млрд RUB)
2. Запустите скрипт — откроется браузер с интерактивным графиком.

Источники данных (МСФО):
https://severstal.com/rus/ir/indicators-reporting/financial-results/
"""

import json
import os
import urllib.request
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    (2026, 1): 0.05,
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
END_DATE = "2026-04-15"


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


def plot_chart_interactive(dates, closes, pe_values, ttm_values):
    """Построить интерактивный двойной график с помощью Plotly."""
    # Создаём subplot с двумя осями Y
    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
    )

    # --- Цена (левая ось) ---
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=closes,
            mode="lines",
            name="Цена CHMF",
            line=dict(color="#1f77b4", width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Цена: %{y:.2f} RUB<extra></extra>",
        ),
        secondary_y=False,
    )

    # --- P/E (правая ось) ---
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=pe_values,
            mode="lines",
            name="P/E (TTM)",
            line=dict(color="#ff7f0e", width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>P/E: %{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    # --- Линия целевого P/E ---
    fig.add_hline(
        y=TARGET_PE,
        line_dash="dash",
        line_color="red",
        line_width=1,
        opacity=0.6,
        annotation_text=f"P/E = {TARGET_PE} (цель)",
        annotation_position="top right",
        secondary_y=True,
    )

    # --- Настройка осей ---
    fig.update_xaxes(title_text="Дата", tickformat="%Y-%m", tickangle=-45)
    fig.update_yaxes(title_text="Цена акции (RUB)", secondary_y=False)
    fig.update_yaxes(title_text="P/E Ratio (TTM)", secondary_y=True)

    # --- Заголовок ---
    fig.update_layout(
        title=dict(
            text=(
                f"Северсталь (CHMF) — Цена и P/E (TTM)<br>"
                f"<sup>{START_DATE[:7]} → {END_DATE[:7]}</sup>"
            ),
            font=dict(size=16),
            x=0.5,
        ),
        hovermode="x unified",
        height=700,
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    # --- Сохранение и показ ---
    output_html = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "severstal_pe_quarterly.html",
    )

    # Сохраняем в HTML для последующего просмотра
    fig.write_html(output_html, auto_open=False)
    print(f"Интерактивный график сохранён: {output_html}")

    # Открываем в браузере
    fig.show()


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

    print("Построение интерактивного графика...")
    plot_chart_interactive(dates, closes, pe_values, ttm_values)

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
