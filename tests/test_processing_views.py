"""Тесты отбора транзакций для представления главной страницы."""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, cast
from unittest.mock import Mock

import pandas as pd
import pytest

from src import processing_views


@pytest.mark.parametrize(
    "field_aliases",
    [
        [],
        {1: []},
        {"field": "path"},
        {"field": [1]},
    ],
)
def test_load_field_aliases_rejects_invalid_structure(
    monkeypatch: pytest.MonkeyPatch,
    field_aliases: Any,
) -> None:
    """Некорректный справочник заменяется пустым словарём."""
    monkeypatch.setattr(processing_views, "load_fields", Mock(return_value=field_aliases))

    assert processing_views._load_field_aliases() == {}


@pytest.mark.parametrize("amount", [True, "100", float("nan"), float("inf")])
def test_get_payment_amount_rejects_invalid_values(amount: Any) -> None:
    """Логические, нечисловые и неконечные суммы отклоняются."""
    assert processing_views._get_payment_amount({"Сумма платежа": amount}) is None


def test_get_payment_amount_returns_float() -> None:
    """Корректная сумма преобразуется в float."""
    assert processing_views._get_payment_amount({"Сумма платежа": -100}) == -100.0


@pytest.mark.parametrize(
    ("date_time", "expected"),
    [
        ("2026-10-18 05:00:00", "Доброе утро"),
        ("2026-10-18 12:00:00", "Добрый день"),
        ("2026-10-18 18:00:00", "Добрый вечер"),
        ("2026-10-18 23:00:00", "Доброй ночи"),
    ],
)
def test_get_greeting(date_time: str, expected: str) -> None:
    """Приветствие соответствует времени суток."""
    assert processing_views.get_greeting(date_time) == [{"greeting": expected}]


@pytest.mark.parametrize("date_time", ["", cast(Any, None)])
def test_get_greeting_rejects_invalid_input(date_time: Any) -> None:
    """Некорректное входное значение регистрируется и отклоняется."""
    with pytest.raises((TypeError, ValueError)):
        processing_views.get_greeting(date_time)


def test_get_transactions_returns_loaded_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Загрузчик возвращает список, полученный от Excel-ридера."""
    transactions = [{"id": 1}]
    reader = Mock(return_value=transactions)
    monkeypatch.setattr(processing_views, "get_transactions_from_xls", reader)

    assert processing_views.get_transactions() == transactions
    reader.assert_called_once_with(processing_views.OPERATIONS_PATH)


@pytest.mark.parametrize("error", [OSError("error"), ValueError("error"), ImportError("error")])
def test_get_transactions_handles_reader_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Ожидаемые ошибки Excel-ридера преобразуются в пустой список."""
    monkeypatch.setattr(processing_views, "get_transactions_from_xls", Mock(side_effect=error))

    assert processing_views.get_transactions() == []


def test_get_transactions_rejects_non_list_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Результат ридера неверного типа не передаётся вызывающему коду."""
    monkeypatch.setattr(processing_views, "get_transactions_from_xls", Mock(return_value=None))

    assert processing_views.get_transactions() == []


def test_get_transactions_view_filters_current_month_and_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Временные границы включаются, а ошибочные записи пропускаются."""
    transactions = [
        {"id": 1, "Дата операции": "01.10.2026 00:00:01", "Статус": "OK"},
        {"id": 2, "Дата операции": "18.10.2026 12:30:00", "Статус": "OK"},
        {"id": 3, "Дата операции": "2026-10-10", "Статус": "OK"},
        {"id": 4, "Дата операции": "15.10.2026 10:30:00", "Статус": "OK"},
        {"id": 5, "Дата операции": "2026-10-17 23:59:59", "Статус": "OK"},
        {"id": 6, "Дата операции": datetime(2026, 10, 12, 8, 0), "Статус": "OK"},
        {"id": 7, "Дата операции": date(2026, 10, 13), "Статус": "OK"},
        {"id": 8, "Дата операции": "01.10.2026 00:00:00", "Статус": "OK"},
        {"id": 9, "Дата операции": "18.10.2026 12:30:01", "Статус": "OK"},
        {"id": 10, "Дата операции": "10.10.2026 10:00:00", "Статус": "FAILED"},
        {"id": 11, "Дата операции": "not-a-date", "Статус": "OK"},
        {"id": 12, "Дата операции": "   ", "Статус": "OK"},
        {"id": 13, "Дата операции": None, "Статус": "OK"},
        {"id": 14, "Дата операции": 20261010, "Статус": "OK"},
        {"id": 15, "Дата операции": pd.NaT, "Статус": "OK"},
    ]
    monkeypatch.setattr(processing_views, "get_transactions", Mock(return_value=transactions))

    result = processing_views.get_transactions_view("2026-10-18 12:30:00", sent=False)

    assert [transaction["id"] for transaction in result] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_get_transactions_view_returns_empty_list_without_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустой исходный список остаётся пустым."""
    monkeypatch.setattr(processing_views, "get_transactions", Mock(return_value=[]))

    assert processing_views.get_transactions_view("2026-10-18 12:30:00", sent=False) == []


def test_get_transactions_view_returns_empty_list_without_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Функция возвращает пустой список, когда период не содержит операций."""
    monkeypatch.setattr(
        processing_views,
        "get_transactions",
        Mock(
            return_value=[
                {"Дата операции": "30.09.2026 23:59:59", "Статус": "OK"},
                {"Дата операции": "18.10.2026 12:30:01", "Статус": "OK"},
            ]
        ),
    )

    assert processing_views.get_transactions_view("2026-10-18 12:30:00", sent=False) == []


def test_get_transactions_view_filters_expenses_and_invalid_amounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """При sent=True остаются только расходы с корректной суммой."""
    transactions = [
        {
            "id": 1,
            "Дата операции": "10.10.2026 10:00:00",
            "Статус": "OK",
            "Сумма платежа": -100.0,
        },
        {
            "id": 2,
            "Дата операции": "10.10.2026 11:00:00",
            "Статус": "OK",
            "Сумма платежа": 100.0,
        },
        {
            "id": 3,
            "Дата операции": "10.10.2026 12:00:00",
            "Статус": "OK",
        },
    ]
    monkeypatch.setattr(processing_views, "get_transactions", Mock(return_value=transactions))

    result = processing_views.get_transactions_view("2026-10-18 12:30:00")

    assert [transaction["id"] for transaction in result] == [1]


def test_get_transactions_view_rejects_invalid_sent() -> None:
    """Параметр sent должен быть логическим значением."""
    with pytest.raises(TypeError, match="sent должен иметь тип bool"):
        processing_views.get_transactions_view("2026-10-18 12:30:00", sent=cast(Any, 1))


def test_get_transactions_view_skips_invalid_item_and_timezone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректный элемент и дата с несовместимым часовым поясом пропускаются."""
    transactions = cast(
        list[processing_views.Transaction],
        [
            "not-a-transaction",
            {
                "Дата операции": datetime(2026, 10, 10, tzinfo=timezone.utc),
                "Статус": "OK",
            },
        ],
    )
    monkeypatch.setattr(processing_views, "get_transactions", Mock(return_value=transactions))

    assert processing_views.get_transactions_view("2026-10-18 12:30:00", sent=False) == []


@pytest.mark.parametrize(
    "date_time",
    [
        "2026-10-18",
        "18.10.2026 12:30:00",
        "2026-10-18T12:30:00",
        "",
    ],
)
def test_get_transactions_view_rejects_invalid_input_format(date_time: str) -> None:
    """Входная дата должна соответствовать формату с датой и временем."""
    with pytest.raises(ValueError):
        processing_views.get_transactions_view(date_time)


def test_get_transactions_view_rejects_non_string_input() -> None:
    """Входное значение должно быть строкой."""
    with pytest.raises(TypeError):
        processing_views.get_transactions_view(cast(Any, None))


def test_get_cards_summary_groups_expenses_by_card(monkeypatch: pytest.MonkeyPatch) -> None:
    """Расходы группируются по карте, а некорректные записи пропускаются."""
    transactions = [
        {"Номер карты": "*1234", "Сумма платежа": -100.0},
        {"Номер карты": "  *1234  ", "Сумма платежа": -50.0},
        {"Номер карты": "*5678", "Сумма платежа": 20.0},
        {"Номер карты": "*5678", "Сумма платежа": "bad"},
        {"Номер карты": None, "Сумма платежа": -10.0},
    ]
    monkeypatch.setattr(processing_views, "get_transactions_view", Mock(return_value=transactions))

    assert processing_views.get_cards_summary("2026-10-18 12:30:00") == [
        {
            "last_digits": "1234",
            "total_spent": 150.0,
            "cashback": 1.5,
            "count": 2,
        }
    ]


def test_get_top_transactions_sorts_and_formats_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Топ сортируется по модулю суммы и возвращает требуемые поля."""
    transactions = [
        {
            "Дата платежа": "10.10.2026",
            "Сумма платежа": -100.0,
            "Категория": "Супермаркеты",
            "Описание": "Магазин",
        },
        {
            "Дата платежа": "11.10.2026",
            "Сумма платежа": -500.0,
            "Категория": "Транспорт",
            "Описание": "Билет",
        },
        {"Сумма платежа": "bad"},
    ]
    monkeypatch.setattr(processing_views, "get_transactions_view", Mock(return_value=transactions))

    assert processing_views.get_top_transactions("2026-10-18 12:30:00", 1) == [
        {
            "date": "11.10.2026",
            "amount": 500.0,
            "category": "Транспорт",
            "description": "Билет",
        }
    ]


@pytest.mark.parametrize("count_top", [True, 1.5, "1"])
def test_get_top_transactions_rejects_invalid_count_type(count_top: Any) -> None:
    """Количество транзакций должно быть целым числом, но не bool."""
    with pytest.raises(TypeError, match="count_top должен быть целым числом"):
        processing_views.get_top_transactions("2026-10-18 12:30:00", count_top)


def test_get_top_transactions_rejects_negative_count() -> None:
    """Отрицательное количество транзакций запрещено."""
    with pytest.raises(ValueError, match="count_top не может быть отрицательным"):
        processing_views.get_top_transactions("2026-10-18 12:30:00", -1)


def test_get_top_transactions_returns_empty_list_for_zero() -> None:
    """Нулевое количество даёт пустой список без загрузки транзакций."""
    assert processing_views.get_top_transactions("2026-10-18 12:30:00", 0) == []


@pytest.mark.parametrize(
    ("date_range", "expected_ids"),
    [
        ("W", [7, 8]),
        ("M", [5, 6, 7, 8]),
        ("Y", [3, 4, 5, 6, 7, 8]),
        ("ALL", [1, 2, 3, 4, 5, 6, 7, 8]),
    ],
)
def test_get_transactions_view_supports_date_ranges(
    monkeypatch: pytest.MonkeyPatch,
    date_range: str,
    expected_ids: list[int],
) -> None:
    """Поддерживаются недельный, месячный, годовой и полный периоды."""
    transactions = [
        {"id": 1, "Дата операции": "1900-01-01 00:00:00", "Статус": "OK"},
        {"id": 2, "Дата операции": "2025-12-31 23:59:59", "Статус": "OK"},
        {"id": 3, "Дата операции": "2026-01-01 00:00:00", "Статус": "OK"},
        {"id": 4, "Дата операции": "2026-09-30 23:59:59", "Статус": "OK"},
        {"id": 5, "Дата операции": "2026-10-01 00:00:00", "Статус": "OK"},
        {"id": 6, "Дата операции": "2026-10-19 00:00:00", "Статус": "OK"},
        {"id": 7, "Дата операции": "2026-10-19 00:00:01", "Статус": "OK"},
        {"id": 8, "Дата операции": "2026-10-21 12:00:00", "Статус": "OK"},
    ]
    monkeypatch.setattr(processing_views, "get_transactions", Mock(return_value=transactions))

    result = processing_views.get_transactions_view(
        "2026-10-21 12:00:00",
        sent=False,
        date_range=date_range,
    )

    assert [transaction["id"] for transaction in result] == expected_ids


def test_get_transactions_view_filters_incoming_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Режим incoming оставляет поступления и пропускает расходы и пустые суммы."""
    transactions = [
        {
            "id": 1,
            "Дата операции": "2026-10-10 10:00:00",
            "Статус": "OK",
            "Сумма платежа": 100.0,
        },
        {
            "id": 2,
            "Дата операции": "2026-10-10 11:00:00",
            "Статус": "OK",
            "Сумма платежа": -100.0,
        },
        {
            "id": 3,
            "Дата операции": "2026-10-10 12:00:00",
            "Статус": "OK",
        },
    ]
    monkeypatch.setattr(processing_views, "get_transactions", Mock(return_value=transactions))

    result = processing_views.get_transactions_view(
        "2026-10-18 12:30:00",
        sent=False,
        incoming=True,
    )

    assert [transaction["id"] for transaction in result] == [1]


def test_validate_category_arguments_accepts_valid_values() -> None:
    """Корректные аргументы проходят проверку без исключения."""
    processing_views._validate_category_arguments([], 7, True)


@pytest.mark.parametrize(
    ("transactions", "count_top", "expenses", "error", "message"),
    [
        (None, 7, True, TypeError, "transactions должен быть списком"),
        ([], True, True, TypeError, "count_top должен быть целым числом"),
        ([], 1.5, True, TypeError, "count_top должен быть целым числом"),
        ([], -1, True, ValueError, "count_top не может быть отрицательным"),
        ([], 7, 1, TypeError, "expenses должен иметь тип bool"),
    ],
)
def test_validate_category_arguments_rejects_invalid_values(
    transactions: Any,
    count_top: Any,
    expenses: Any,
    error: type[Exception],
    message: str,
) -> None:
    """Некорректные аргументы отклоняются с понятной ошибкой."""
    with pytest.raises(error, match=message):
        processing_views._validate_category_arguments(transactions, count_top, expenses)


@pytest.mark.parametrize(
    ("transaction", "expenses"),
    [
        ("wrong", True),
        ({"Категория": None, "Сумма платежа": -10}, True),
        ({"Категория": "   ", "Сумма платежа": -10}, True),
        ({"Категория": "Еда", "Сумма платежа": True}, True),
        ({"Категория": "Еда", "Сумма платежа": None}, True),
        ({"Категория": "Еда", "Сумма платежа": "wrong"}, True),
        ({"Категория": "Еда", "Сумма платежа": "NaN"}, True),
        ({"Категория": "Еда", "Сумма платежа": 10}, True),
        ({"Категория": "Еда", "Сумма платежа": -10}, False),
    ],
)
def test_get_category_amount_skips_invalid_or_wrong_direction(
    transaction: Any,
    expenses: bool,
) -> None:
    """Некорректные записи и операции другого направления пропускаются."""
    assert processing_views._get_category_amount(transaction, 0, expenses) is None


@pytest.mark.parametrize(
    ("transaction", "expenses", "expected"),
    [
        (
            {"Категория": "  Еда  ", "Сумма платежа": -125.5},
            True,
            ("Еда", Decimal("125.5")),
        ),
        (
            {"Категория": "Зарплата", "Сумма платежа": 1000},
            False,
            ("Зарплата", Decimal("1000")),
        ),
    ],
)
def test_get_category_amount_returns_normalized_value(
    transaction: dict[str, Any],
    expenses: bool,
    expected: tuple[str, Decimal],
) -> None:
    """Подходящая операция возвращается с очищенной категорией и модулем суммы."""
    assert processing_views._get_category_amount(transaction, 0, expenses) == expected


def test_collect_category_totals_returns_amounts_and_counts() -> None:
    """Суммы и количества накапливаются отдельно для каждой категории."""
    transactions = [
        {"Категория": "Еда", "Сумма платежа": -100},
        {"Категория": "Еда", "Сумма платежа": -50},
        {"Категория": "Транспорт", "Сумма платежа": -20},
        {"Категория": "Доход", "Сумма платежа": 1000},
    ]

    totals, counts = processing_views._collect_category_totals(transactions, True)

    assert dict(totals) == {
        "Еда": Decimal("150"),
        "Транспорт": Decimal("20"),
    }
    assert dict(counts) == {"Еда": 2, "Транспорт": 1}


def test_build_category_result_does_not_double_other_total() -> None:
    """Остаточные категории суммируются в «Остальное» ровно один раз."""
    totals = defaultdict(
        Decimal,
        {
            "Еда": Decimal("100"),
            "Транспорт": Decimal("80"),
            "Развлечения": Decimal("20"),
            "Остальное": Decimal("10"),
        },
    )
    counts = defaultdict(int, {"Еда": 2, "Транспорт": 1, "Развлечения": 3, "Остальное": 1})

    result = processing_views._build_category_result(totals, counts, count_top=2)

    assert result == [
        {"category": "Еда", "amount": 100.0, "count": 2},
        {"category": "Транспорт", "amount": 80.0, "count": 1},
        {"category": "Остальное", "amount": 30.0, "count": 4},
    ]


def test_build_category_result_omits_empty_other_category() -> None:
    """Категория «Остальное» не добавляется, если остаточных данных нет."""
    totals = defaultdict(Decimal, {"Еда": Decimal("10.55")})
    counts = defaultdict(int, {"Еда": 1})

    result = processing_views._build_category_result(
        totals,
        counts,
        count_top=1,
        digit_round=2,
    )

    assert result == [{"category": "Еда", "amount": 10.55, "count": 1}]


def test_get_category_summary_returns_expense_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Итог расходов содержит топ, остаток, общую сумму и количество."""
    transactions = [
        {"Категория": "Еда", "Сумма платежа": -100},
        {"Категория": "Еда", "Сумма платежа": -50},
        {"Категория": "Транспорт", "Сумма платежа": -30},
        {"Категория": "Развлечения", "Сумма платежа": -20},
    ]
    view = Mock(return_value=transactions)
    monkeypatch.setattr(processing_views, "get_transactions_view", view)

    result, total, count = processing_views.get_category_summary(
        "2026-10-18 12:30:00",
        date_range="W",
        count_top=2,
        expenses=True,
    )

    assert result == [
        {"category": "Еда", "amount": 150.0, "count": 2},
        {"category": "Транспорт", "amount": 30.0, "count": 1},
        {"category": "Остальное", "amount": 20.0, "count": 1},
    ]
    assert total == 200.0
    assert count == 4
    view.assert_called_once_with("2026-10-18 12:30:00", True, False, "W")


def test_get_category_summary_returns_income_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Для поступлений используется входящий режим фильтрации."""
    transactions = [{"Категория": "Зарплата", "Сумма платежа": 1000}]
    view = Mock(return_value=transactions)
    monkeypatch.setattr(processing_views, "get_transactions_view", view)

    result = processing_views.get_category_summary(
        "2026-10-18 12:30:00",
        expenses=False,
    )

    assert result == ([{"category": "Зарплата", "amount": 1000.0, "count": 1}], 1000.0, 1)
    view.assert_called_once_with("2026-10-18 12:30:00", False, True, "M")


@pytest.mark.parametrize(
    ("transactions", "count_top", "expenses", "error"),
    [
        (None, 7, True, TypeError),
        ([], -1, True, ValueError),
        ([], 7, cast(Any, 1), TypeError),
    ],
)
def test_get_category_summary_propagates_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    transactions: Any,
    count_top: int,
    expenses: bool,
    error: type[Exception],
) -> None:
    """Ошибки аргументов регистрируются и передаются вызывающему коду."""
    monkeypatch.setattr(processing_views, "get_transactions_view", Mock(return_value=transactions))

    with pytest.raises(error):
        processing_views.get_category_summary(
            "2026-10-18 12:30:00",
            count_top=count_top,
            expenses=expenses,
        )
