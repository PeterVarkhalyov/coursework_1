"""Реализация блока Веб-страницы"""

import json
from typing import Any

from src.currencies import get_currency_rates
from src.processing_views import get_cards_summary, get_category_summary, get_greeting, get_top_transactions
from src.stocks import get_stock_rates


def get_main_response(date_time: str) -> Any:
    """Вернуть JSON-ответ для Главной страницы."""
    response = {
        "greeting": get_greeting(date_time)[0]["greeting"],
        "cards": get_cards_summary(date_time),
        "top_transactions": get_top_transactions(date_time, 5),
        "currency_rates": get_currency_rates(),
        "stock_prices": get_stock_rates(),
    }

    return json.dumps(response, ensure_ascii=False)


def get_events_response(date_time: str, date_range: str = "M") -> Any:
    """Вернуть JSON-ответ для страницы События"""
    expenses, expenses_total, expenses_count = get_category_summary(date_time, date_range, 7, True)
    income, income_total, income_count = get_category_summary(date_time, date_range, 7, False)
    response = {
        "expenses": {"total_amount": expenses_total, "total_count": expenses_count, "main": expenses},
        "income": {"total_amount": income_total, "total_count": income_count, "main": income},
        "currency_rates": get_currency_rates(),
        "stock_prices": get_stock_rates(),
    }

    return json.dumps(response, ensure_ascii=False)
