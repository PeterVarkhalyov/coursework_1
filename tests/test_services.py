"""Тесты публичных сервисов анализа транзакций."""

import json
from collections import defaultdict
from decimal import Decimal
from typing import Any, cast
from unittest.mock import Mock

import pytest

from src import services


def test_get_category_cashback_returns_expected_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сервис формирует JSON со всеми категориями и суммами кешбэка."""
    transactions = [{"Категория": "Супермаркеты", "Кэшбэк": 10}]
    totals = defaultdict(
        Decimal,
        {
            "Супермаркеты": Decimal("125.5"),
            "Транспорт": Decimal("40"),
        },
    )
    get_transactions = Mock(return_value=transactions)
    collect_cashback = Mock(return_value=(totals, defaultdict(int, {"Супермаркеты": 2, "Транспорт": 1})))
    monkeypatch.setattr(services, "get_transactions_cashback", get_transactions)
    monkeypatch.setattr(services, "_collect_category_cashback", collect_cashback)

    result = services.get_category_cashback("2021", "12")

    assert json.loads(result) == {
        "Супермаркеты": 125.5,
        "Транспорт": 40.0,
    }
    assert "Супермаркеты" in result
    get_transactions.assert_called_once_with("2021", "12")
    collect_cashback.assert_called_once_with(transactions)


def test_get_category_cashback_returns_empty_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """При отсутствии подходящих операций возвращается пустой JSON-массив."""
    monkeypatch.setattr(services, "get_transactions_cashback", Mock(return_value=[]))
    collect_cashback = Mock()
    monkeypatch.setattr(services, "_collect_category_cashback", collect_cashback)

    assert services.get_category_cashback("20", "25") == "[]"
    collect_cashback.assert_not_called()


def test_investment_bank_returns_calculated_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сервис возвращает разницу округлённой и исходной сумм."""
    transactions = [{"id": 1}, {"id": 2}]
    filtered_transactions = [{"id": 1}]
    valid_limit = Mock(return_value=True)
    get_transactions = Mock(return_value=filtered_transactions)
    get_total = Mock(return_value=160.89)
    get_limit_total = Mock(return_value=170.0)
    monkeypatch.setattr(services, "valid_limit", valid_limit)
    monkeypatch.setattr(services, "get_transaction_investment_bank", get_transactions)
    monkeypatch.setattr(services, "get_total_amount", get_total)
    monkeypatch.setattr(services, "get_total_limit_amount", get_limit_total)

    result = services.investment_bank("2021-12", transactions, 10)

    assert result == 9.11
    valid_limit.assert_called_once_with(10)
    get_transactions.assert_called_once_with("2021-12", transactions)
    get_total.assert_called_once_with(filtered_transactions)
    get_limit_total.assert_called_once_with(filtered_transactions, 10)


def test_investment_bank_returns_none_for_invalid_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Некорректный порог завершает расчёт до фильтрации операций."""
    monkeypatch.setattr(services, "valid_limit", Mock(return_value=False))
    get_transactions = Mock()
    monkeypatch.setattr(services, "get_transaction_investment_bank", get_transactions)

    assert services.investment_bank("2021-12", [], 20) is None
    get_transactions.assert_not_called()


def test_investment_bank_returns_none_for_negative_difference(monkeypatch: pytest.MonkeyPatch) -> None:
    """Отрицательный результат расчёта считается некорректным."""
    monkeypatch.setattr(services, "valid_limit", Mock(return_value=True))
    monkeypatch.setattr(services, "get_transaction_investment_bank", Mock(return_value=[]))
    monkeypatch.setattr(services, "get_total_amount", Mock(return_value=200.0))
    monkeypatch.setattr(services, "get_total_limit_amount", Mock(return_value=190.0))

    assert services.investment_bank("2021-12", [], 10) is None


def test_get_transactions_search_returns_empty_response_for_invalid_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректный поисковый запрос даёт пустой JSON-ответ."""
    monkeypatch.setattr(services, "_valid_search_query", Mock(return_value=None))
    matches = Mock()
    monkeypatch.setattr(services, "_transaction_matches_search", matches)

    assert json.loads(services.get_transactions_search([{"id": 1}], "")) == {
        "count": 0,
        "result": [],
    }
    matches.assert_not_called()


def test_get_transactions_search_returns_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """В JSON попадают только транзакции, прошедшие поиск."""
    transactions = [{"id": 1}, {"id": 2}, {"id": 3}]
    validator = Mock(return_value="магазин")
    matches = Mock(side_effect=[True, False, True])
    monkeypatch.setattr(services, "_valid_search_query", validator)
    monkeypatch.setattr(services, "_transaction_matches_search", matches)

    assert json.loads(services.get_transactions_search(transactions, " Магазин ")) == {
        "count": 2,
        "result": [{"id": 1}, {"id": 3}],
    }
    validator.assert_called_once_with(" Магазин ")


def test_get_transactions_search_phone_returns_empty_for_invalid_phone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректный телефон завершает поиск до группировки."""
    monkeypatch.setattr(services, "_valid_search_query_phone", Mock(return_value=None))
    get_groups = Mock()
    monkeypatch.setattr(services, "get_phone_transactions", get_groups)

    assert json.loads(services.get_transactions_search_phone([], "wrong")) == {
        "phone": "None",
        "count": 0,
        "result": [],
    }
    get_groups.assert_not_called()


def test_get_transactions_search_phone_returns_empty_when_group_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Корректный номер без совпадающей группы возвращает пустой результат."""
    groups = cast(
        list[dict[str, Any]],
        [cast(Any, "wrong"), {"phone": "+71111111111", "transactions": []}],
    )
    monkeypatch.setattr(services, "_valid_search_query_phone", Mock(return_value="+79991234567"))
    monkeypatch.setattr(services, "get_phone_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_phone([], "+7 999 123-45-67")) == {
        "phone": "None",
        "count": 0,
        "result": [],
    }


def test_get_transactions_search_phone_returns_matching_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """По найденному номеру возвращается список связанных транзакций."""
    transactions = [{"id": 1}, {"id": 2}]
    groups = [{"phone": "+79991234567", "count": 2, "transactions": transactions}]
    monkeypatch.setattr(services, "_valid_search_query_phone", Mock(return_value="+79991234567"))
    monkeypatch.setattr(services, "get_phone_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_phone([], "+79991234567")) == {
        "phone": "+79991234567",
        "count": 2,
        "result": transactions,
    }


def test_get_transactions_search_phone_rejects_non_list_group_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректное поле transactions заменяется пустым списком."""
    groups = [{"phone": "+79991234567", "count": 1, "transactions": "wrong"}]
    monkeypatch.setattr(services, "_valid_search_query_phone", Mock(return_value="+79991234567"))
    monkeypatch.setattr(services, "get_phone_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_phone([], "+79991234567")) == {
        "phone": "+79991234567",
        "count": 0,
        "result": [],
    }


def test_get_transactions_search_phone_total_combines_all_group_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Общий ответ разделяет корректные и ошибочные телефонные группы."""
    normal_one = [{"id": 1}, {"id": 2}]
    normal_two = [{"id": 3}]
    normal_three = [{"id": 4}]
    error_one = [{"id": 5}]
    error_two = [{"id": 6}, {"id": 7}]
    groups = cast(
        list[dict[str, Any]],
        [
            {"phone": "+79991234567", "count": 2, "transactions": normal_one},
            {"phone": "phone_error", "count": 1, "transactions": error_one},
            {"phone": "89215554433", "count": "bad", "transactions": normal_two},
            {"phone": "phone_error", "count": True, "transactions": error_two},
            {"phone": "89990000000", "count": -1, "transactions": normal_three},
            {"phone": "ignored", "count": 1, "transactions": "wrong"},
        ],
    )
    monkeypatch.setattr(services, "get_phone_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_phone_total([])) == {
        "total": 7,
        "result": {
            "count": 4,
            "transactions": normal_one + normal_two + normal_three,
        },
        "error": {
            "count": 3,
            "transactions": error_one + error_two,
        },
    }


def test_get_transactions_search_person_returns_empty_for_invalid_person(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректное имя завершает поиск до группировки."""
    monkeypatch.setattr(services, "_valid_search_query_person", Mock(return_value=None))
    get_groups = Mock()
    monkeypatch.setattr(services, "get_person_transactions", get_groups)

    assert json.loads(services.get_transactions_search_person([], "wrong")) == {
        "person": "None",
        "count": 0,
        "result": [],
    }
    get_groups.assert_not_called()


def test_get_transactions_search_person_returns_empty_when_group_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Нормализованное имя без группы возвращает пустой результат."""
    groups = cast(
        list[dict[str, Any]],
        [cast(Any, "wrong"), {"person": "Сергей З.", "transactions": []}],
    )
    monkeypatch.setattr(services, "_valid_search_query_person", Mock(return_value="Валерий А."))
    monkeypatch.setattr(services, "get_person_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_person([], "Валерий Александров")) == {
        "person": "Валерий А.",
        "count": 0,
        "result": [],
    }


def test_get_transactions_search_person_returns_matching_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """По физлицу возвращаются все связанные транзакции."""
    transactions = [{"id": 1}, {"id": 2}]
    groups = [{"person": "Валерий А.", "count": 2, "transactions": transactions}]
    monkeypatch.setattr(services, "_valid_search_query_person", Mock(return_value="Валерий А."))
    monkeypatch.setattr(services, "get_person_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_person([], "Валерий А.")) == {
        "person": "Валерий А.",
        "count": 2,
        "result": transactions,
    }


def test_get_transactions_search_person_rejects_non_list_group_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректное поле transactions физлица заменяется пустым списком."""
    groups = [{"person": "Валерий А.", "count": 1, "transactions": "wrong"}]
    monkeypatch.setattr(services, "_valid_search_query_person", Mock(return_value="Валерий А."))
    monkeypatch.setattr(services, "get_person_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_search_person([], "Валерий А.")) == {
        "person": "Валерий А.",
        "count": 0,
        "result": [],
    }


def test_get_transactions_total_person_combines_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    """Все группы физических лиц объединяются в один JSON-ответ."""
    first = [{"id": 1}, {"id": 2}]
    second = [{"id": 3}]
    third = [{"id": 4}]
    fourth = [{"id": 5}]
    groups = cast(
        list[dict[str, Any]],
        [
            {"person": "Валерий А.", "count": 2, "transactions": first},
            {"person": "Сергей З.", "count": "bad", "transactions": second},
            {"person": "Анна П.", "count": True, "transactions": third},
            {"person": "Иван К.", "count": -1, "transactions": fourth},
            {"person": "ignored", "count": 1, "transactions": "wrong"},
        ],
    )
    monkeypatch.setattr(services, "get_person_transactions", Mock(return_value=groups))

    assert json.loads(services.get_transactions_total_person([])) == {
        "count": 5,
        "transactions": first + second + third + fourth,
    }
