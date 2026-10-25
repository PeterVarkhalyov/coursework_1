"""Тесты подготовки транзакций для сервисов."""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from unittest.mock import Mock, call

import pytest

from src import processing_services


class FixedDatetime(datetime):
    """Дата и время с фиксированным результатом ``now``."""

    @classmethod
    def now(cls, tz: Any = None) -> "FixedDatetime":
        """Вернуть фиксированный момент для проверки текущего периода."""
        return cls(2026, 10, 21, 12, 0, 0, tzinfo=tz)


@pytest.fixture
def fixed_current_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """Зафиксировать текущую дату на октябре 2026 года."""
    monkeypatch.setattr(processing_services, "datetime", FixedDatetime)


def test_validate_period_accepts_past_and_current_periods(fixed_current_date: None) -> None:
    """Прошлый и текущий месяцы проходят проверку."""
    processing_services._validate_period(1970, 1)
    processing_services._validate_period(2026, 10)


@pytest.mark.parametrize("year", [True, 2026.0, "2026"])
def test_validate_period_rejects_invalid_year_type(
    fixed_current_date: None,
    year: Any,
) -> None:
    """Год должен быть целым числом, но не bool."""
    with pytest.raises(TypeError, match="year должен быть целым числом"):
        processing_services._validate_period(year, 1)


@pytest.mark.parametrize("year", [1969, 2027])
def test_validate_period_rejects_year_outside_range(
    fixed_current_date: None,
    year: int,
) -> None:
    """Год вне допустимого диапазона отклоняется."""
    with pytest.raises(ValueError, match="year должен находиться в диапазоне"):
        processing_services._validate_period(year, 1)


@pytest.mark.parametrize("month", [True, 1.5, "10"])
def test_validate_period_rejects_invalid_month_type(
    fixed_current_date: None,
    month: Any,
) -> None:
    """Месяц должен быть целым числом, но не bool."""
    with pytest.raises(TypeError, match="month должен быть целым числом"):
        processing_services._validate_period(2026, month)


@pytest.mark.parametrize("month", [0, 13])
def test_validate_period_rejects_month_outside_range(
    fixed_current_date: None,
    month: int,
) -> None:
    """Номер месяца должен находиться в диапазоне от 1 до 12."""
    with pytest.raises(ValueError, match="month должен находиться в диапазоне"):
        processing_services._validate_period(2026, month)


def test_validate_period_rejects_future_month(fixed_current_date: None) -> None:
    """Будущий месяц текущего года отклоняется."""
    with pytest.raises(ValueError, match="превышают текущую дату"):
        processing_services._validate_period(2026, 11)


@pytest.mark.parametrize("amount", [True, "10", None, float("nan"), float("inf"), float("-inf")])
def test_get_cashback_amount_rejects_invalid_values(amount: Any) -> None:
    """Логические, нечисловые и неконечные суммы кешбэка пропускаются."""
    assert processing_services._get_cashback_amount({"Кэшбэк": amount}) is None


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, 0.0),
        (10, 10.0),
        (-2.5, -2.5),
    ],
)
def test_get_cashback_amount_returns_float(amount: int | float, expected: float) -> None:
    """Конечная числовая сумма преобразуется в float."""
    assert processing_services._get_cashback_amount({"Кэшбэк": amount}) == expected


def _cashback_transaction(**overrides: Any) -> dict[str, Any]:
    """Сформировать корректную транзакцию с возможностью замены полей."""
    transaction: dict[str, Any] = {
        "Статус": "OK",
        "Дата платежа": "15.12.2021",
        "Кэшбэк": 25.0,
        "Категория": "Супермаркеты",
    }
    transaction.update(overrides)
    return transaction


def test_transaction_matches_cashback_accepts_matching_transaction() -> None:
    """Успешная транзакция с кешбэком за нужный период принимается."""
    assert processing_services._transaction_matches_cashback(_cashback_transaction(), "2021", "12") is True


@pytest.mark.parametrize(
    ("transaction", "year", "month"),
    [
        ("wrong", "2021", "12"),
        (_cashback_transaction(Статус="FAILED"), "2021", "12"),
        (_cashback_transaction(**{"Дата платежа": "not-a-date"}), "2021", "12"),
        (_cashback_transaction(**{"Кэшбэк": None}), "2021", "12"),
        (_cashback_transaction(**{"Кэшбэк": -1}), "2021", "12"),
        (_cashback_transaction(), "2020", "12"),
        (_cashback_transaction(), "2021", "11"),
        (_cashback_transaction(), cast(Any, None), "12"),
    ],
)
def test_transaction_matches_cashback_rejects_unsuitable_transactions(
    transaction: Any,
    year: str,
    month: str,
) -> None:
    """Записи с неподходящими данными или периодом пропускаются."""
    assert processing_services._transaction_matches_cashback(transaction, year, month) is False


@pytest.mark.parametrize(
    "transaction",
    [
        "wrong",
        {"Категория": None, "Кэшбэк": 10},
        {"Категория": "   ", "Кэшбэк": 10},
        {"Категория": "Еда", "Кэшбэк": True},
        {"Категория": "Еда", "Кэшбэк": None},
        {"Категория": "Еда", "Кэшбэк": "wrong"},
        {"Категория": "Еда", "Кэшбэк": "NaN"},
    ],
)
def test_get_category_cashback_skips_invalid_transaction(transaction: Any) -> None:
    """Некорректная категория или сумма не участвуют в агрегации."""
    assert processing_services._get_category_cashback(transaction, 0) is None


@pytest.mark.parametrize(
    ("transaction", "expected"),
    [
        ({"Категория": "  Еда  ", "Кэшбэк": -12.5}, ("Еда", Decimal("12.5"))),
        ({"Категория": "Транспорт", "Кэшбэк": "5"}, ("Транспорт", Decimal("5"))),
    ],
)
def test_get_category_cashback_returns_normalized_value(
    transaction: dict[str, Any],
    expected: tuple[str, Decimal],
) -> None:
    """Категория очищается, а кешбэк возвращается по модулю."""
    assert processing_services._get_category_cashback(transaction, 0) == expected


def test_collect_category_cashback_returns_totals_and_counts() -> None:
    """Кешбэк и количество операций суммируются по категориям."""
    transactions = cast(
        list[dict[str, Any]],
        [
            {"Категория": "Еда", "Кэшбэк": 10},
            {"Категория": " Еда ", "Кэшбэк": -2.5},
            {"Категория": "Транспорт", "Кэшбэк": 5},
            {"Категория": "", "Кэшбэк": 100},
            "wrong",
        ],
    )

    totals, counts = processing_services._collect_category_cashback(transactions)

    assert dict(totals) == {
        "Еда": Decimal("12.5"),
        "Транспорт": Decimal("5"),
    }
    assert dict(counts) == {"Еда": 2, "Транспорт": 1}


def test_get_transactions_cashback_filters_loaded_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Публичная функция проверяет период и оставляет подходящие записи."""
    transactions = [{"id": 1}, {"id": 2}, {"id": 3}]
    validate_period = Mock()
    get_transactions = Mock(return_value=transactions)
    matches = Mock(side_effect=[True, False, True])
    monkeypatch.setattr(processing_services, "_validate_period", validate_period)
    monkeypatch.setattr(processing_services, "get_transactions", get_transactions)
    monkeypatch.setattr(processing_services, "_transaction_matches_cashback", matches)

    result = processing_services.get_transactions_cashback("2021", "12")

    assert result == [{"id": 1}, {"id": 3}]
    validate_period.assert_called_once_with(2021, 12)
    get_transactions.assert_called_once_with()
    assert matches.call_args_list == [
        call({"id": 1}, "2021", "12"),
        call({"id": 2}, "2021", "12"),
        call({"id": 3}, "2021", "12"),
    ]


@pytest.mark.parametrize(
    ("year", "month"),
    [
        ("wrong", "12"),
        ("2021", "wrong"),
        (cast(Any, None), "12"),
    ],
)
def test_get_transactions_cashback_returns_empty_list_for_non_numeric_period(
    monkeypatch: pytest.MonkeyPatch,
    year: str,
    month: str,
) -> None:
    """Непреобразуемый период регистрируется и даёт пустой список."""
    get_transactions = Mock()
    logger = Mock()
    monkeypatch.setattr(processing_services, "get_transactions", get_transactions)
    monkeypatch.setattr(processing_services, "logger", logger)

    assert processing_services.get_transactions_cashback(year, month) == []
    get_transactions.assert_not_called()
    logger.error.assert_called_once()


@pytest.mark.parametrize(("year", "month"), [("20", "25"), ("2026", "11")])
def test_get_transactions_cashback_returns_empty_list_for_invalid_period(
    monkeypatch: pytest.MonkeyPatch,
    fixed_current_date: None,
    year: str,
    month: str,
) -> None:
    """Период вне диапазона регистрируется и не запускает загрузку данных."""
    get_transactions = Mock()
    monkeypatch.setattr(processing_services, "get_transactions", get_transactions)

    assert processing_services.get_transactions_cashback(year, month) == []
    get_transactions.assert_not_called()


def _investment_transaction(**overrides: Any) -> dict[str, Any]:
    """Сформировать корректную расходную транзакцию по банковской карте."""
    transaction: dict[str, Any] = {
        "Статус": "OK",
        "Дата операции": "15.12.2021 12:00:00",
        "Номер карты": "*1234",
        "Сумма платежа": -160.89,
    }
    transaction.update(overrides)
    return transaction


def test_transaction_matches_investment_accepts_matching_transaction() -> None:
    """Подходящий расход по карте за выбранный месяц принимается."""
    assert processing_services._transaction_matches_investment(_investment_transaction(), "2021", "12") is True


@pytest.mark.parametrize(
    ("transaction", "year", "month"),
    [
        ("wrong", "2021", "12"),
        (_investment_transaction(Статус="FAILED"), "2021", "12"),
        (_investment_transaction(**{"Дата операции": "not-a-date"}), "2021", "12"),
        (_investment_transaction(**{"Номер карты": None}), "2021", "12"),
        (_investment_transaction(**{"Номер карты": "   "}), "2021", "12"),
        (_investment_transaction(**{"Сумма платежа": None}), "2021", "12"),
        (_investment_transaction(**{"Сумма платежа": 100}), "2021", "12"),
        (_investment_transaction(), "2020", "12"),
        (_investment_transaction(), "2021", "11"),
        (_investment_transaction(), cast(Any, None), "12"),
    ],
)
def test_transaction_matches_investment_rejects_unsuitable_transactions(
    transaction: Any,
    year: str,
    month: str,
) -> None:
    """Неподходящие и некорректные операции не участвуют в расчёте."""
    assert processing_services._transaction_matches_investment(transaction, year, month) is False


@pytest.mark.parametrize("limit", processing_services.INVESTMENT_LIMITS)
def test_valid_limit_accepts_supported_values(limit: int) -> None:
    """Все предусмотренные пороги округления разрешены."""
    assert processing_services.valid_limit(limit) is True


@pytest.mark.parametrize("limit", [True, 10.0, "10", 20])
def test_valid_limit_rejects_unsupported_values(limit: Any) -> None:
    """Неверный тип и отсутствующее в настройках значение отклоняются."""
    assert processing_services.valid_limit(limit) is False


def test_get_transaction_investment_bank_rejects_non_string_date() -> None:
    """Дата периода должна быть строкой."""
    assert processing_services.get_transaction_investment_bank(cast(Any, None), []) == []


@pytest.mark.parametrize("date_value", ["wrong", "2021-1"])
def test_get_transaction_investment_bank_rejects_invalid_date_format(date_value: str) -> None:
    """Неверная и неканоническая запись периода отклоняется."""
    assert processing_services.get_transaction_investment_bank(date_value, []) == []


def test_get_transaction_investment_bank_handles_period_conversion_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ошибка преобразования частей периода приводит к пустому результату."""
    parsed_date = Mock()
    parsed_date.strftime.return_value = "wrong-10"
    datetime_mock = Mock()
    datetime_mock.strptime.return_value = parsed_date
    monkeypatch.setattr(processing_services, "datetime", datetime_mock)

    assert processing_services.get_transaction_investment_bank("wrong-10", []) == []


def test_get_transaction_investment_bank_rejects_invalid_period(
    monkeypatch: pytest.MonkeyPatch,
    fixed_current_date: None,
) -> None:
    """Будущий период возвращает пустой список до фильтрации транзакций."""
    matches = Mock()
    monkeypatch.setattr(processing_services, "_transaction_matches_investment", matches)

    assert processing_services.get_transaction_investment_bank("2026-11", []) == []
    matches.assert_not_called()


def test_get_transaction_investment_bank_filters_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """После проверки периода остаются только подходящие расходные операции."""
    transactions = [{"id": 1}, {"id": 2}, {"id": 3}]
    validate_period = Mock()
    matches = Mock(side_effect=[True, False, True])
    monkeypatch.setattr(processing_services, "_validate_period", validate_period)
    monkeypatch.setattr(processing_services, "_transaction_matches_investment", matches)

    result = processing_services.get_transaction_investment_bank("2021-12", transactions)

    assert result == [{"id": 1}, {"id": 3}]
    validate_period.assert_called_once_with(2021, 12)
    assert matches.call_args_list == [
        call({"id": 1}, "2021", "12"),
        call({"id": 2}, "2021", "12"),
        call({"id": 3}, "2021", "12"),
    ]


def test_get_total_amount_sums_absolute_numeric_values() -> None:
    """Исходные суммы складываются по модулю, ошибочные значения пропускаются."""
    transactions: list[dict[str, Any]] = [
        {"Сумма платежа": -100.25},
        {"Сумма платежа": 50},
        {"Сумма платежа": True},
        {"Сумма платежа": "25"},
        {},
    ]

    assert processing_services.get_total_amount(transactions) == 150.25


def test_get_total_limit_amount_rounds_each_value_up() -> None:
    """Каждая сумма округляется вверх до ближайшего заданного порога."""
    transactions: list[dict[str, Any]] = [
        {"Сумма платежа": -1712},
        {"Сумма платежа": -1765},
        {"Сумма платежа": -100},
        {"Сумма платежа": False},
        {"Сумма платежа": None},
    ]

    assert processing_services.get_total_limit_amount(transactions, 50) == 3650.0


@pytest.mark.parametrize(
    ("transaction", "search_query", "expected"),
    [
        ("wrong", "поиск", False),
        ({"Категория": "Супермаркеты", "Описание": "Продукты"}, "супер", True),
        ({"Категория": "Другое", "Описание": "Оплата телефона"}, "телефона", True),
        ({"Категория": None, "Описание": "Нужный текст"}, "нужный", True),
        ({"Категория": "Другое", "Описание": None}, "поиск", False),
        ({"Категория": None, "Описание": None}, "поиск", False),
    ],
)
def test_transaction_matches_search(
    transaction: Any,
    search_query: str,
    expected: bool,
) -> None:
    """Поиск выполняется без учёта регистра по категории и описанию."""
    assert processing_services._transaction_matches_search(transaction, search_query) is expected


@pytest.mark.parametrize("search_query", [None, 10, "", "   "])
def test_valid_search_query_rejects_invalid_values(search_query: Any) -> None:
    """Нестроковый и пустой поисковый запрос отклоняется."""
    assert processing_services._valid_search_query(search_query) is None


def test_valid_search_query_normalizes_value() -> None:
    """Пробелы удаляются, а регистр приводится к нижнему."""
    assert processing_services._valid_search_query("  СуПеР  ") == "супер"


@pytest.mark.parametrize("search_query", [None, "", "   ", "+7 921 11-22-33"])
def test_valid_search_query_phone_rejects_invalid_values(search_query: Any) -> None:
    """Пустые, нестроковые и неполные номера отклоняются."""
    assert processing_services._valid_search_query_phone(search_query) is None


@pytest.mark.parametrize(
    ("search_query", "expected"),
    [
        (" +7 (999) 123-45-67 ", "+79991234567"),
        ("8 921 555-44-33", "89215554433"),
    ],
)
def test_valid_search_query_phone_normalizes_value(search_query: str, expected: str) -> None:
    """Корректный телефон очищается от пробелов, скобок и дефисов."""
    assert processing_services._valid_search_query_phone(search_query) == expected


def test_get_phone_transactions_groups_valid_and_invalid_candidates() -> None:
    """Телефоны группируются, а ошибочные кандидаты попадают в отдельную группу."""
    first = {"id": 1, "Описание": "Оплата +7 (999) 123-45-67"}
    second = {"id": 2, "Описание": "Перевод +7 999 123-45-67"}
    third = {"id": 3, "Описание": "Оплата 8 921 555-44-33"}
    invalid = {"id": 4, "Описание": "Номера +7 921 11-22-33 и 8 921 12-34"}
    transactions = cast(
        list[processing_services.Transaction],
        [
            first,
            second,
            third,
            invalid,
            {"id": 5, "Описание": "Без телефона"},
            {"id": 6, "Описание": None},
            "wrong",
        ],
    )

    result = processing_services.get_phone_transactions(transactions)

    assert result == [
        {
            "phone": "+79991234567",
            "count": 2,
            "transactions": [first, second],
        },
        {
            "phone": "89215554433",
            "count": 1,
            "transactions": [third],
        },
        {
            "phone": "phone_error",
            "count": 2,
            "transactions": [invalid],
        },
    ]


def test_get_phone_transactions_omits_empty_error_group() -> None:
    """Группа ошибок не создаётся при отсутствии некорректных кандидатов."""
    assert processing_services.get_phone_transactions([]) == []


def test_get_phone_group_returns_only_valid_phone_and_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Краткая сводка содержит только строковый телефон и целое количество."""
    phone_groups = cast(
        list[processing_services.Transaction],
        [
            {"phone": "+79991234567", "count": 2},
            {"phone": 10, "count": 1},
            {"phone": "phone_error", "count": True},
            {"phone": "wrong", "count": "1"},
        ],
    )
    get_phone_transactions = Mock(return_value=phone_groups)
    monkeypatch.setattr(processing_services, "get_phone_transactions", get_phone_transactions)

    assert processing_services.get_phone_group([{"id": 1}]) == [{"phone": "+79991234567", "count": 2}]
    get_phone_transactions.assert_called_once_with([{"id": 1}])


def test_normalize_name_part_supports_hyphen() -> None:
    """Каждая часть составного имени получает правильный регистр."""
    assert processing_services._normalize_name_part("аННа-мАРия") == "Анна-Мария"


@pytest.mark.parametrize("search_query", [None, "", "   ", "Сергей", "Сергей 123"])
def test_valid_search_query_person_rejects_invalid_values(search_query: Any) -> None:
    """Пустой запрос и строка без имени с фамилией отклоняются."""
    assert processing_services._valid_search_query_person(search_query) is None


@pytest.mark.parametrize(
    ("search_query", "expected"),
    [
        ("  валерий   александров  ", "Валерий А."),
        ("анна-мария петрова", "Анна-Мария П."),
        ("Сергей З.", "Сергей З."),
    ],
)
def test_valid_search_query_person_normalizes_value(search_query: str, expected: str) -> None:
    """Полная фамилия и инициал приводятся к формату «Имя Ф.»."""
    assert processing_services._valid_search_query_person(search_query) == expected


@pytest.mark.parametrize(
    ("transaction", "expected"),
    [
        ("wrong", None),
        ({"Категория": None, "Описание": "Валерий А."}, None),
        ({"Категория": "Супермаркеты", "Описание": "Валерий А."}, None),
        ({"Категория": "Переводы", "Описание": None}, None),
        ({"Категория": "Переводы", "Описание": "Без имени"}, None),
        ({"Категория": " Переводы ", "Описание": "Перевод Валерий А."}, "Валерий А."),
    ],
)
def test_get_person_from_transaction(transaction: Any, expected: str | None) -> None:
    """Физлицо извлекается только из описания транзакции категории «Переводы»."""
    assert processing_services._get_person_from_transaction(transaction) == expected


def test_get_person_transactions_groups_transfers() -> None:
    """Переводы одному физлицу объединяются в одну группу."""
    first = {"id": 1, "Категория": "Переводы", "Описание": "Перевод Валерий А."}
    second = {"id": 2, "Категория": "Переводы", "Описание": "Валерий А. возврат"}
    third = {"id": 3, "Категория": "Переводы", "Описание": "Сергей З."}
    transactions = [
        first,
        second,
        third,
        {"id": 4, "Категория": "Переводы", "Описание": "Без имени"},
    ]

    assert processing_services.get_person_transactions(transactions) == [
        {
            "person": "Валерий А.",
            "count": 2,
            "transactions": [first, second],
        },
        {
            "person": "Сергей З.",
            "count": 1,
            "transactions": [third],
        },
    ]


def test_get_person_group_returns_only_valid_person_and_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Краткая сводка отбрасывает группы с некорректными полями."""
    person_groups = cast(
        list[processing_services.Transaction],
        [
            {"person": "Валерий А.", "count": 2},
            {"person": 10, "count": 1},
            {"person": "Сергей З.", "count": True},
            {"person": "Анна П.", "count": "1"},
        ],
    )
    get_person_transactions = Mock(return_value=person_groups)
    monkeypatch.setattr(processing_services, "get_person_transactions", get_person_transactions)

    assert processing_services.get_person_group([{"id": 1}]) == [{"person": "Валерий А.", "count": 2}]
    get_person_transactions.assert_called_once_with([{"id": 1}])
