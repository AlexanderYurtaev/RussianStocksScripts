"""
Скрипт расчёта текущего P/E МосБиржи (MOEX) на Московской бирже.

Источники данных:
- Цена акции: Moex ISS API (автоматически)
- Кол-во акций: Moex ISS API, поле ISSUESIZE (автоматически)
- Чистая прибыль: вводится вручную из отчётов МосБиржи
"""

import json
import sys
import urllib.request
from datetime import datetime

MOEX_ISS_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/shares/securities/MOEX.json"
)


def fetch_moex_data():
    """Получить все данные по MOEX с Moex ISS API."""
    try:
        req = urllib.request.Request(
            MOEX_ISS_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Ошибка при получении данных с Moex: {e}")
        return None


def get_price(data):
    """Получить текущую цену MOEX."""
    marketdata = data.get("marketdata", {})
    if "data" not in marketdata:
        return None
    columns = marketdata["columns"]
    for row in marketdata["data"]:
        row_dict = dict(zip(columns, row))
        if row_dict.get("BOARDID") == "TQBR" and row_dict.get("LAST") is not None:
            return float(row_dict["LAST"])
    # Fallback: любая доступная цена
    for row in marketdata["data"]:
        row_dict = dict(zip(columns, row))
        if row_dict.get("LAST") is not None:
            return float(row_dict["LAST"])
    return None


def get_shares_outstanding(data):
    """Получить количество акций в обращении из Moex (ISSUESIZE)."""
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
    return None


def main():
    print("=" * 60)
    print("  МосБиржа (MOEX) — расчёт P/E")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()

    # --- Автоматические данные с Moex ---
    print("Получение данных с Московской биржи...")
    moex_data = fetch_moex_data()

    price = None
    shares = None

    if moex_data:
        price = get_price(moex_data)
        shares = get_shares_outstanding(moex_data)

    if price:
        print(f"  Цена акции:         {price:,.2f} RUB")
    if shares:
        print(f"  Акции в обращении:  {shares:,} шт.")

    if not price:
        price = float(input("\nНе удалось получить цену. Введите цену (RUB): "))
    if not shares:
        shares = int(input("Не удалось получить кол-во акций. Введите число акций: "))

    print()

    # --- Ручной ввод прибыли ---
    print("Введите чистую прибыль МосБиржи из отчётности:")
    print("  (данные МСФО, в млрд RUB)")
    print("  Источник: https://www.moex.com/s1593")
    print()

    try:
        net_income_input = input("Чистая прибыль (млрд RUB): ").strip()
        net_income_input = (
            net_income_input.replace(" ", "").replace("_", "").replace(",", ".")
        )
        net_income_bln = float(net_income_input)
    except (ValueError, KeyboardInterrupt):
        print("Некорректный ввод. Завершение.")
        sys.exit(1)

    print()

    # --- Расчёт ---
    net_income_rub = net_income_bln * 1_000_000_000
    eps = net_income_rub / shares
    pe = price / eps
    market_cap_rub = price * shares

    # Целевая цена при P/E = 7
    target_pe = 7
    target_price = eps * target_pe
    upside = ((target_price - price) / price) * 100

    print("-" * 60)
    print("РЕЗУЛЬТАТ:")
    print(
        f"  Рыночная капитализация:  {market_cap_rub:,.0f} RUB  ({market_cap_rub / 1e9:,.1f} млрд)"
    )
    print(
        f"  Чистая прибыль (год):    {net_income_rub:,.0f} RUB  ({net_income_bln:,.1f} млрд)"
    )
    print(f"  EPS (прибыль на акцию):  {eps:,.2f} RUB")
    print(f"  P/E Ratio:               {pe:.2f}")
    print()
    print(f"  Целевая цена (P/E=7):    {target_price:,.2f} RUB")
    print(f"  Потенциал:               {upside:+.1f}%")
    print("-" * 60)

    # --- Интерпретация ---
    if pe < 0:
        print("Компания убыточна (отрицательная прибыль).")
    elif pe <= target_pe:
        print(f"Текущий P/E ({pe:.2f}) ≤ 7 — акция недооценена.")
        print(f"До справедливой цены (P/E=7) осталось {abs(upside):.1f}% роста.")
    else:
        print(f"Текущий P/E ({pe:.2f}) > 7 — акция переоценена.")
        print(f"До справедливой цены (P/E=7) нужно снижение на {abs(upside):.1f}%.")

    print()
    print("Подсказка: данные о прибыли берите из официальных отчётов МосБиржи.")


if __name__ == "__main__":
    main()
