"""Тесты формирования JSON-ответов веб-страниц."""

import json
from unittest.mock import Mock, call

import pytest

from src import views


def test_get_main_response_returns_expected_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Главная страница объединяет все рассчитанные блоки в JSON."""
    greeting = Mock(return_value=[{"greeting": "Добрый день"}])
    cards = Mock(return_value=[{"last_digits": "1234", "total_spent": 100.0}])
    top = Mock(return_value=[{"description": "Магазин", "amount": 100.0}])
    currencies = Mock(return_value=[{"currency": "USD", "rate": 80.0}])
    stocks = Mock(return_value=[{"stock": "AAPL", "price": 200.0}])
    monkeypatch.setattr(views, "get_greeting", greeting)
    monkeypatch.setattr(views, "get_cards_summary", cards)
    monkeypatch.setattr(views, "get_top_transactions", top)
    monkeypatch.setattr(views, "get_currency_rates", currencies)
    monkeypatch.setattr(views, "get_stock_rates", stocks)

    response = json.loads(views.get_main_response("2026-10-18 12:30:00"))

    assert response == {
        "greeting": "Добрый день",
        "cards": [{"last_digits": "1234", "total_spent": 100.0}],
        "top_transactions": [{"description": "Магазин", "amount": 100.0}],
        "currency_rates": [{"currency": "USD", "rate": 80.0}],
        "stock_prices": [{"stock": "AAPL", "price": 200.0}],
    }
    greeting.assert_called_once_with("2026-10-18 12:30:00")
    cards.assert_called_once_with("2026-10-18 12:30:00")
    top.assert_called_once_with("2026-10-18 12:30:00", 5)
    currencies.assert_called_once_with()
    stocks.assert_called_once_with()


def test_get_events_response_returns_expected_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Страница событий объединяет расходы, поступления и котировки в JSON."""
    expenses = [{"category": "Еда", "amount": 150.0, "count": 2}]
    income = [{"category": "Зарплата", "amount": 1000.0, "count": 1}]
    category_summary = Mock(
        side_effect=[
            (expenses, 150.0, 2),
            (income, 1000.0, 1),
        ]
    )
    currencies = Mock(return_value=[{"currency": "USD", "rate": 80.0}])
    stocks = Mock(return_value=[{"stock": "AAPL", "price": 200.0}])
    monkeypatch.setattr(views, "get_category_summary", category_summary)
    monkeypatch.setattr(views, "get_currency_rates", currencies)
    monkeypatch.setattr(views, "get_stock_rates", stocks)

    response = json.loads(views.get_events_response("2026-10-18 12:30:00", "W"))

    assert response == {
        "expenses": {
            "total_amount": 150.0,
            "total_count": 2,
            "main": expenses,
        },
        "income": {
            "total_amount": 1000.0,
            "total_count": 1,
            "main": income,
        },
        "currency_rates": [{"currency": "USD", "rate": 80.0}],
        "stock_prices": [{"stock": "AAPL", "price": 200.0}],
    }
    assert category_summary.call_args_list == [
        call("2026-10-18 12:30:00", "W", 7, True),
        call("2026-10-18 12:30:00", "W", 7, False),
    ]
    currencies.assert_called_once_with()
    stocks.assert_called_once_with()
