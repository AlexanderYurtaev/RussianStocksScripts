"""
Модуль для расчета финансовых показателей акций.

Предоставляет функции для расчета P/E и других основных метрик.
"""

from typing import Tuple

from moex_api import format_number


class FinancialMetrics:
    """Класс для расчета финансовых показателей."""

    def __init__(self, ticker: str):
        """
        Инициализация калькулятора метрик.

        Args:
            ticker: Тикер акции
        """
        self.ticker = ticker

    def calculate_pe(
        self, price: float, net_income: float, shares_outstanding: int
    ) -> Tuple[float, float, float]:
        """
        Рассчитать коэффициент P/E (цена/прибыль).

        Args:
            price: Цена акции в рублях
            net_income: Чистая прибыль в рублях
            shares_outstanding: Количество акций в обращении

        Returns:
            Кортеж (P/E, EPS, рыночная капитализация)
        """
        market_cap = price * shares_outstanding
        eps = net_income / shares_outstanding if shares_outstanding > 0 else 0
        pe = price / eps if eps > 0 else float("inf")

        return pe, eps, market_cap

    def calculate_target_price(self, eps: float, target_pe: float = 7.0) -> float:
        """
        Рассчитать целевую цену.

        Args:
            eps: Прибыль на акцию
            target_pe: Целевой коэффициент P/E

        Returns:
            Целевая цена
        """
        return eps * target_pe

    def calculate_potential(self, current_price: float, target_price: float) -> float:
        """
        Рассчитать потенциал роста/падения в процентах.

        Args:
            current_price: Текущая цена
            target_price: Целевая цена

        Returns:
            Потенциал в процентах (положительный - рост, отрицательный - падение)
        """
        if current_price == 0:
            return 0.0
        return ((target_price - current_price) / current_price) * 100

    def interpret_pe(self, pe: float, target_pe: float = 7.0) -> str:
        """
        Интерпретировать значение P/E.

        Args:
            pe: Коэффициент P/E
            target_pe: Целевой коэффициент P/E

        Returns:
            Текстовая интерпретация
        """
        if pe < 0:
            return "Компания убыточна (отрицательная прибыль)."
        elif pe <= target_pe:
            return f"Текущий P/E ({pe:.2f}) ≤ {target_pe} — акция недооценена."
        else:
            return f"Текущий P/E ({pe:.2f}) > {target_pe} — акция переоценена."

    def print_metrics_report(
        self,
        price: float,
        shares_outstanding: int,
        net_income: float,
        target_pe: float = 7.0,
    ) -> None:
        """
        Вывести отчет по финансовым показателям.

        Args:
            price: Цена акции
            shares_outstanding: Количество акций в обращении
            net_income: Чистая прибыль
            target_pe: Целевой P/E
        """
        print("-" * 60)
        print("ФИНАНСОВЫЕ ПОКАЗАТЕЛИ:")
        print("-" * 60)

        # Расчет основных показателей
        pe, eps, market_cap = self.calculate_pe(price, net_income, shares_outstanding)
        target_price = self.calculate_target_price(eps, target_pe)
        potential = self.calculate_potential(price, target_price)

        # Вывод результатов
        print(f"  Рыночная капитализация:  {format_number(market_cap)} RUB")
        print(f"  Цена акции:              {price:,.2f} RUB")
        print(f"  Акции в обращении:       {shares_outstanding:,} шт.")
        print()
        print(f"  Чистая прибыль:          {format_number(net_income)} RUB")
        print(f"  EPS (прибыль на акцию):  {eps:,.2f} RUB")
        print(f"  P/E Ratio:               {pe:.2f}")
        print(f"  Целевая цена (P/E={target_pe}): {target_price:,.2f} RUB")
        print(f"  Потенциал:               {potential:+.1f}%")
        print(f"  Интерпретация:           {self.interpret_pe(pe, target_pe)}")


def parse_income_input(prompt: str) -> float:
    """
    Парсить ввод чистой прибыли от пользователя.

    Args:
        prompt: Текст подсказки

    Returns:
        Чистая прибыль в рублях
    """
    import sys

    try:
        net_income_input = input(prompt).strip()
        net_income_input = (
            net_income_input.replace(" ", "").replace("_", "").replace(",", ".")
        )
        net_income_bln = float(net_income_input)
        return net_income_bln * 1_000_000_000
    except (ValueError, KeyboardInterrupt):
        print("Некорректный ввод. Завершение.")
        sys.exit(1)
