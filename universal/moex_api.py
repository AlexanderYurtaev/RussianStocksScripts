"""
Модуль для работы с API Московской биржи (Moex ISS).

Предоставляет функции для получения данных по акциям российских компаний.
"""

import json
import urllib.request
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


class MoexAPI:
    """Класс для работы с API Московской биржи."""
    
    BASE_URL = "https://iss.moex.com/iss"
    
    def __init__(self, timeout: int = 15):
        """
        Инициализация API.
        
        Args:
            timeout: Таймаут запросов в секундах
        """
        self.timeout = timeout
        self.headers = {"User-Agent": "Mozilla/5.0 (RussianStocksScripts/1.0)"}
    
    def fetch_security_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Получить все данные по указанному тикеру.
        
        Args:
            ticker: Тикер акции (например, 'ROSN', 'CHMF')
            
        Returns:
            Словарь с данными или None в случае ошибки
        """
        url = f"{self.BASE_URL}/engines/stock/markets/shares/securities/{ticker}.json"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"Ошибка при получении данных для {ticker}: {e}")
            return None
    
    def get_current_price(self, ticker: str, board: str = "TQBR") -> Optional[float]:
        """
        Получить текущую цену акции.
        
        Args:
            ticker: Тикер акции
            board: Код площадки (по умолчанию TQBR - основные торги)
            
        Returns:
            Цена акции или None
        """
        data = self.fetch_security_data(ticker)
        if not data:
            return None
        
        marketdata = data.get("marketdata", {})
        if "data" not in marketdata or "columns" not in marketdata:
            return None
        
        columns = marketdata["columns"]
        
        # Сначала ищем цену на указанной площадке
        for row in marketdata["data"]:
            row_dict = dict(zip(columns, row))
            if row_dict.get("BOARDID") == board and row_dict.get("LAST") is not None:
                return float(row_dict["LAST"])
        
        # Fallback: любая доступная цена
        for row in marketdata["data"]:
            row_dict = dict(zip(columns, row))
            if row_dict.get("LAST") is not None:
                return float(row_dict["LAST"])
        
        return None
    
    def get_shares_outstanding(self, ticker: str, board: str = "TQBR") -> Optional[int]:
        """
        Получить количество акций в обращении (ISSUESIZE).
        
        Args:
            ticker: Тикер акции
            board: Код площадки
            
        Returns:
            Количество акций или None
        """
        data = self.fetch_security_data(ticker)
        if not data:
            return None
        
        securities = data.get("securities", {})
        if "data" not in securities or "columns" not in securities:
            return None
        
        columns = securities["columns"]
        
        for row in securities["data"]:
            row_dict = dict(zip(columns, row))
            if row_dict.get("BOARDID") == board:
                issue_size = row_dict.get("ISSUESIZE")
                if issue_size is not None:
                    return int(issue_size)
        
        return None
    
    def get_market_cap(self, ticker: str) -> Optional[float]:
        """
        Рассчитать рыночную капитализацию.
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Рыночная капитализация в рублях или None
        """
        price = self.get_current_price(ticker)
        shares = self.get_shares_outstanding(ticker)
        
        if price is None or shares is None:
            return None
        
        return price * shares
    
    def fetch_historical_data(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str,
        board: str = "TQBR"
    ) -> Optional[Dict[str, Any]]:
        """
        Получить исторические данные по акции.
        
        Args:
            ticker: Тикер акции
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата в формате YYYY-MM-DD
            board: Код площадки
            
        Returns:
            Словарь с историческими данными или None
        """
        base_url = (
            f"{self.BASE_URL}/history/engines/stock/markets/shares"
            f"/securities/{ticker}.json?from={start_date}&til={end_date}&board={board}"
        )
        
        all_rows = []
        columns = None
        start = 0
        
        try:
            while True:
                url = f"{base_url}&start={start}"
                req = urllib.request.Request(url, headers=self.headers)
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
            
        except Exception as e:
            print(f"Ошибка при получении исторических данных для {ticker}: {e}")
            return None
    
    def parse_historical_prices(
        self, 
        historical_data: Dict[str, Any]
    ) -> Tuple[list, list]:
        """
        Распарсить исторические данные в списки дат и цен закрытия.
        
        Args:
            historical_data: Данные, полученные из fetch_historical_data
            
        Returns:
            Кортеж (список дат, список цен закрытия)
        """
        columns = historical_data.get("columns", [])
        rows = historical_data.get("data", [])
        
        if not rows:
            return [], []
        
        dates = []
        closes = []
        
        for row in rows:
            row_dict = dict(zip(columns, row))
            date_str = row_dict.get("TRADEDATE")
            close = row_dict.get("CLOSE")
            
            if date_str and close is not None:
                try:
                    dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
                    closes.append(float(close))
                except (ValueError, TypeError):
                    continue
        
        return dates, closes


# Создаем глобальный экземпляр для удобства использования
api = MoexAPI()


def get_company_name(ticker: str) -> str:
    """
    Получить название компании по тикеру.
    
    Args:
        ticker: Тикер акции
        
    Returns:
        Название компании
    """
    company_names = {
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
    
    return company_names.get(ticker, ticker)


def format_number(value: float, decimals: int = 2) -> str:
    """
    Форматировать число с разделителями тысяч.
    
    Args:
        value: Число для форматирования
        decimals: Количество знаков после запятой
        
    Returns:
        Отформатированная строка
    """
    if value is None:
        return "N/A"
    
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.{decimals}f} млрд"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.{decimals}f} млн"
    else:
        return f"{value:,.{decimals}f}"