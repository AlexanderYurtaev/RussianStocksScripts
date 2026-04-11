#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования функциональности Russian Stocks Scripts.
"""

import sys

from financial_metrics import FinancialMetrics
from moex_api import api, format_number, get_company_name


def test_moex_api():
    """Тестирование работы с API Московской биржи."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ MOEX API")
    print("=" * 60)

    # Тестируем получение данных для Роснефти
    ticker = "ROSN"
    company_name = get_company_name(ticker)

    print(f"\n1. Получение данных для {company_name} ({ticker}):")

    # Получаем цену
    price = api.get_current_price(ticker)
    if price:
        print(f"   ✓ Цена акции: {price:,.2f} RUB")
    else:
        print("   ✗ Не удалось получить цену")

    # Получаем количество акций
    shares = api.get_shares_outstanding(ticker)
    if shares:
        print(f"   ✓ Акции в обращении: {shares:,} шт.")
    else:
        print("   ✗ Не удалось получить количество акций")

    # Рассчитываем рыночную капитализацию
    market_cap = api.get_market_cap(ticker)
    if market_cap:
        print(f"   ✓ Рыночная капитализация: {format_number(market_cap)} RUB")
    else:
        print("   ✗ Не удалось рассчитать рыночную капитализацию")

    return price is not None and shares is not None


def test_financial_metrics():
    """Тестирование расчета финансовых показателей."""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ РАСЧЕТА ФИНАНСОВЫХ ПОКАЗАТЕЛЕЙ")
    print("=" * 60)

    # Тестовые данные
    ticker = "TEST"
    price = 1000.0
    shares = 1_000_000_000  # 1 млрд акций
    net_income = 100_000_000_000  # 100 млрд RUB прибыли

    metrics = FinancialMetrics(ticker)

    print("\n2. Расчет основных показателей:")

    # P/E расчет
    pe, eps, market_cap = metrics.calculate_pe(price, net_income, shares)
    print(f"   ✓ P/E: {pe:.2f}")
    print(f"   ✓ EPS: {eps:,.2f} RUB")
    print(f"   ✓ Рыночная капитализация: {format_number(market_cap)} RUB")

    # Целевая цена и потенциал
    target_price = metrics.calculate_target_price(eps)
    potential = metrics.calculate_potential(price, target_price)
    print(f"   ✓ Целевая цена (P/E=7): {target_price:,.2f} RUB")
    print(f"   ✓ Потенциал: {potential:+.1f}%")

    # Интерпретация
    print("\n3. Интерпретация показателей:")
    print(f"   ✓ P/E интерпретация: {metrics.interpret_pe(pe)}")

    return True


def test_company_names():
    """Тестирование получения названий компаний."""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ НАЗВАНИЙ КОМПАНИЙ")
    print("=" * 60)

    test_cases = [
        ("ROSN", "Роснефть"),
        ("CHMF", "Северсталь"),
        ("SBER", "Сбербанк"),
        ("GAZP", "Газпром"),
        ("UNKNOWN", "UNKNOWN"),  # Неизвестный тикер
    ]

    print("\n4. Проверка названий компаний:")

    all_passed = True
    for ticker, expected_name in test_cases:
        actual_name = get_company_name(ticker)
        if actual_name == expected_name:
            print(f"   ✓ {ticker}: {actual_name}")
        else:
            print(
                f"   ✗ {ticker}: ожидалось '{expected_name}', получено '{actual_name}'"
            )
            all_passed = False

    return all_passed


def test_number_formatting():
    """Тестирование форматирования чисел."""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ФОРМАТИРОВАНИЯ ЧИСЕЛ")
    print("=" * 60)

    test_cases = [
        (1_000_000_000, "1.00 млрд"),
        (500_000_000, "500.00 млн"),
        (1_000_000, "1.00 млн"),
        (1000, "1,000.00"),
        (None, "N/A"),
    ]

    print("\n5. Проверка форматирования чисел:")

    all_passed = True
    for value, expected in test_cases:
        formatted = format_number(value) if value is not None else format_number(value)
        if formatted == expected:
            print(f"   ✓ {value if value is not None else 'None'}: {formatted}")
        else:
            print(
                f"   ✗ {value if value is not None else 'None'}: ожидалось '{expected}', получено '{formatted}'"
            )
            all_passed = False

    return all_passed


def main():
    """Основная функция тестирования."""
    print("ДЕМОНСТРАЦИЯ РАБОТЫ RUSSIAN STOCKS SCRIPTS")
    print("=" * 60)

    tests = [
        ("MOEX API", test_moex_api),
        ("Финансовые показатели", test_financial_metrics),
        ("Названия компаний", test_company_names),
        ("Форматирование чисел", test_number_formatting),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\nЗапуск теста: {test_name}...")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ✗ Ошибка при выполнении теста: {e}")
            results.append((test_name, False))

    # Вывод итогов
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✓ ПРОЙДЕН" if result else "✗ НЕ ПРОЙДЕН"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nВсего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Не пройдено: {total - passed}")

    if passed == total:
        print("\n✅ Все тесты пройдены успешно!")
        return 0
    else:
        print("\n❌ Некоторые тесты не пройдены.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
