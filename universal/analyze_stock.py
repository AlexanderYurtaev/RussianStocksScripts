"""
Универсальный скрипт для анализа акций российских компаний.

Расчитывает P/E, P/B, P/S и другие финансовые показатели.
Использует данные с Московской биржи и ручной ввод финансовых показателей.
"""

import sys
from datetime import datetime

from financial_metrics import FinancialMetrics, parse_income_input
from moex_api import api, get_company_name


def analyze_stock(ticker: str, target_pe: float = 7.0) -> None:
    """
    Проанализировать акцию компании.

    Args:
        ticker: Тикер акции
        target_pe: Целевой коэффициент P/E
    """
    company_name = get_company_name(ticker)

    print("=" * 70)
    print(f"  {company_name} ({ticker}) — финансовый анализ")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print()

    # --- Получение данных с Moex ---
    print("Получение данных с Московской биржи...")

    price = api.get_current_price(ticker)
    shares = api.get_shares_outstanding(ticker)

    if price:
        print(f"  Цена акции:         {price:,.2f} RUB")
    if shares:
        print(f"  Акции в обращении:  {shares:,} шт.")

    # Запрос данных, если не удалось получить автоматически
    if not price:
        try:
            price = float(input("\nНе удалось получить цену. Введите цену (RUB): "))
        except (ValueError, KeyboardInterrupt):
            print("Некорректный ввод. Завершение.")
            sys.exit(1)

    if not shares:
        try:
            shares = int(
                input("Не удалось получить кол-во акций. Введите число акций: ")
            )
        except (ValueError, KeyboardInterrupt):
            print("Некорректный ввод. Завершение.")
            sys.exit(1)

    print()

    # --- Создание калькулятора метрик ---
    metrics = FinancialMetrics(ticker)

    # --- Ввод финансовых показателей ---
    print("ВВЕДИТЕ ФИНАНСОВЫЕ ПОКАЗАТЕЛИ КОМПАНИИ:")
    print("  (данные из отчётности, в млрд RUB)")
    print()

    # Чистая прибыль
    print(f"Чистая прибыль {company_name}:")
    net_income = parse_income_input("  Чистая прибыль (млрд RUB): ")

    print()

    # --- Вывод отчета ---
    metrics.print_metrics_report(
        price=price,
        shares_outstanding=shares,
        net_income=net_income,
        target_pe=target_pe,
    )

    print("=" * 70)


def main():
    """Основная функция."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Анализ акций российских компаний",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s ROSN              # Анализ Роснефти
  %(prog)s CHMF              # Анализ Северстали
  %(prog)s SBER --target-pe 8  # Анализ Сбербанка с целевым P/E=8
  %(prog)s --list            # Список доступных тикеров
        """,
    )

    parser.add_argument(
        "ticker", nargs="?", help="Тикер акции (например, ROSN, CHMF, SBER)"
    )

    parser.add_argument(
        "--target-pe",
        type=float,
        default=7.0,
        help="Целевой коэффициент P/E (по умолчанию: 7.0)",
    )

    parser.add_argument(
        "--list", action="store_true", help="Показать список доступных тикеров"
    )

    args = parser.parse_args()

    if args.list:
        print("ДОСТУПНЫЕ ТИКЕРЫ РОССИЙСКИХ КОМПАНИЙ:")
        print("-" * 40)
        companies = {
            "ROSN": "Роснефть",
            "CHMF": "Северсталь",
            "GAZP": "Газпром",
            "SBER": "Сбербанк",
            "LKOH": "Лукойл",
            "MGNT": "Магнит",
            "NVTK": "Новатэк",
            "TATN": "Татнефть",
            "ALRS": "АЛРОСА",
            "POLY": "Полюс",
            "MOEX": "Московская биржа",
            "YNDX": "Яндекс",
            "OZON": "Ozon",
            "TCSG": "TCS Group (Тинькофф)",
            "VTBR": "ВТБ",
        }

        for ticker, name in companies.items():
            print(f"  {ticker:6} - {name}")

        print("\nДля анализа используйте: python analyze_stock.py ТИКЕР")
        return

    if not args.ticker:
        parser.print_help()
        print("\nОШИБКА: Не указан тикер акции.")
        print("Используйте --list для просмотра доступных тикеров.")
        sys.exit(1)

    # Проверка, что тикер в верхнем регистре
    ticker = args.ticker.upper()

    try:
        analyze_stock(ticker, args.target_pe)
    except KeyboardInterrupt:
        print("\n\nАнализ прерван пользователем.")
        sys.exit(0)
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
