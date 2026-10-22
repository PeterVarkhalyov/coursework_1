""" "Подготовка данных для релизации сервисов."""

import logging
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from math import ceil, isfinite
from pathlib import Path
from typing import Any

from src.fields import get_field_value
from src.processing_views import (
    FIELD_ALIASES,
    Transaction,
    _get_payment_amount,
    _parse_operation_datetime,
    get_transactions,
)

INVESTMENT_LIMITS = [10, 50, 100]
PHONE_BODY = r"(?:\+7|8)[ -]?" r"(?:\(\d{3}\)|\d{3})" r"[ -]?\d{3}" r"[ -]?\d{2}" r"[ -]?\d{2}"

PHONE_PATTERN = re.compile(rf"^{PHONE_BODY}$")

PHONE_IN_TEXT_PATTERN = re.compile(rf"(?<!\d){PHONE_BODY}(?!\d)")

PHONE_CANDIDATE_PATTERN = re.compile(r"(?<!\d)" r"(?:\+7|8)" r"(?:[\s()-]*\d){5,}" r"(?!\d)")

PERSON_TRANSFER_PATTERN = re.compile(
    r"\b" r"(?P<person>" r"[А-ЯЁ][а-яё]+" r"(?:-[А-ЯЁ][а-яё]+)?" r"\s+" r"[А-ЯЁ]\." r")" r"(?=\s|$)"
)

PERSON_QUERY_PATTERN = re.compile(
    r"^"
    r"(?P<name>[А-ЯЁа-яё]+(?:-[А-ЯЁа-яё]+)*)"
    r"\s+"
    r"(?P<surname>[А-ЯЁа-яё]+(?:-[А-ЯЁа-яё]+)*|[А-ЯЁа-яё]\.?)"
    r"$"
)

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("processing_services")
logger.setLevel(logging.DEBUG)
logger.propagate = False

file_handler = logging.FileHandler(
    LOG_DIR / "processing_services.log",
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)

file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def _validate_period(year: int, month: int) -> None:
    """Проверить год и месяц анализа."""
    current_date = datetime.now()

    if isinstance(year, bool) or not isinstance(year, int):
        logger.error("Некорректный тип year: %r", year)
        raise TypeError("year должен быть целым числом")

    if not 1970 <= year <= current_date.year:
        logger.error("Некорректное значение year: %d", year)
        raise ValueError("year должен находиться в диапазоне от 1970 до текущего года")

    if isinstance(month, bool) or not isinstance(month, int):
        logger.error("Некорректный тип month: %r", month)
        raise TypeError("month должен быть целым числом")

    if not 1 <= month <= 12:
        logger.error("Некорректное значение month: %d", month)
        raise ValueError("month должен находиться в диапазоне от 1 до 12")

    if (year, month) > (current_date.year, current_date.month):
        logger.error(
            "Период превышает текущую дату: year=%d, month=%d",
            year,
            month,
        )
        raise ValueError("month и year превышают текущую дату.")


def _get_cashback_amount(transaction: Transaction) -> float | None:
    """Вернуть конечную числовую сумму cashback транзакции или ``None``."""
    amount = get_field_value(transaction, "cashback", FIELD_ALIASES)

    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        logger.warning("Пропущена транзакция с некорректной суммой cashback: %r", amount)
        return None

    numeric_amount = float(amount)
    if not isfinite(numeric_amount):
        logger.warning("Пропущена транзакция с неконечной суммой cashback: %r", amount)
        return None

    return numeric_amount


def _transaction_matches_cashback(
    transaction: Any,
    year: str,
    month: str,
) -> bool:
    """Проверить, соответствует ли cashback транзакции условиям представления."""
    if not isinstance(transaction, dict):
        logger.warning("Пропущена транзакция неверного типа: %r", transaction)
        return False

    if get_field_value(transaction, "status", FIELD_ALIASES) != "OK":
        return False

    operation_datetime = _parse_operation_datetime(get_field_value(transaction, "date_payment", FIELD_ALIASES))
    if operation_datetime is None:
        return False

    cashback = _get_cashback_amount(transaction)
    if cashback is None or cashback < 0:
        return False

    try:
        return operation_datetime.year == int(year) and operation_datetime.month == int(month)
    except TypeError as error:
        logger.warning(
            "Пропущена транзакция с несопоставимой датой %r: %s",
            operation_datetime,
            error,
        )
        return False


def _transaction_matches_investment(
    transaction: Any,
    year: str,
    month: str,
) -> bool:
    """Проверить, соответствует ли транзакции условиям представления для инвесткопилки."""
    if not isinstance(transaction, dict):
        logger.warning("Пропущена транзакция неверного типа: %r", transaction)
        return False

    if get_field_value(transaction, "status", FIELD_ALIASES) != "OK":
        return False

    operation_datetime = _parse_operation_datetime(get_field_value(transaction, "date_operation", FIELD_ALIASES))
    if operation_datetime is None:
        return False

    card = get_field_value(transaction, "card_number", FIELD_ALIASES)
    if not isinstance(card, str) or not card.strip():
        return False

    amount = _get_payment_amount(transaction)
    if amount is None or amount >= 0:
        return False

    try:
        return operation_datetime.year == int(year) and operation_datetime.month == int(month)
    except TypeError as error:
        logger.warning(
            "Пропущена транзакция с несопоставимой датой %r: %s",
            operation_datetime,
            error,
        )
        return False


def _get_category_cashback(
    transaction: Any,
    index: int,
) -> tuple[str, Decimal] | None:
    """Получить категорию и сумму cashback подходящей транзакции."""
    if not isinstance(transaction, dict):
        logger.warning(
            "Транзакция %d пропущена: ожидался словарь",
            index,
        )
        return None

    category = get_field_value(transaction, "category", FIELD_ALIASES)
    raw_amount = get_field_value(transaction, "cashback", FIELD_ALIASES)

    if not isinstance(category, str) or not category.strip():
        logger.warning(
            "Транзакция %d пропущена: некорректная категория %r",
            index,
            category,
        )
        return None

    if isinstance(raw_amount, bool) or raw_amount is None:
        logger.warning(
            "Транзакция %d пропущена: некорректная сумма cashback %r",
            index,
            raw_amount,
        )
        return None

    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, ValueError):
        logger.warning(
            "Транзакция %d пропущена: некорректная сумма cashback %r",
            index,
            raw_amount,
        )
        return None

    if not amount.is_finite():
        logger.warning(
            "Транзакция %d пропущена: сумма не является конечной",
            index,
        )
        return None

    return category.strip(), abs(amount)


def _collect_category_cashback(
    transactions: list[dict[str, Any]],
) -> tuple[
    defaultdict[str, Decimal],
    defaultdict[str, int],
]:
    """Рассчитать сумму и количество cashback по каждой категории."""
    category_totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    category_counts: defaultdict[str, int] = defaultdict(int)

    for index, transaction in enumerate(transactions):
        category_cashback = _get_category_cashback(
            transaction,
            index,
        )

        if category_cashback is None:
            continue

        category, cashback = category_cashback
        category_totals[category] += cashback
        category_counts[category] += 1

    return category_totals, category_counts


def get_transactions_cashback(year: str, month: str) -> list[Transaction]:
    """Вернуть успешные транзакции за определенный год и месяц.

    Args:
        year: Год в формате ``YYYY``.
        month: Месяц в формате ``MM``.

    Returns:
        Исходные словари транзакций со статусом ``OK``, дата операции
        которых входят в закрытый интервал, где год и месяц равны year и month.

    При некорректном периоде функция записывает ошибку в журнал и возвращает
    пустой список.
    """
    logger.debug("Фильтрация транзакций на момент year = %r и month = %r", year, month)

    try:
        parsed_year = int(year)
        parsed_month = int(month)
    except (TypeError, ValueError) as error:
        logger.error(
            "Не удалось преобразовать период: year=%r, month=%r: %s",
            year,
            month,
            error,
        )
        return []

    try:
        _validate_period(parsed_year, parsed_month)
    except (TypeError, ValueError):
        return []

    transactions = get_transactions()

    filtered_transactions = [
        transaction for transaction in transactions if _transaction_matches_cashback(transaction, year, month)
    ]

    logger.info(
        "За период год = %r и месяц = %r отобрано транзакций: %d",
        year,
        month,
        len(filtered_transactions),
    )
    return filtered_transactions


def valid_limit(limit: int) -> bool:
    """Проверяет соответсвие limit списку допустимых значений"""
    if isinstance(limit, bool) or not isinstance(limit, int):
        logger.error("limit должен быть целым числом: %r", limit)
        return False

    if limit in INVESTMENT_LIMITS:
        return True

    logger.error("limit %s должен соотвествовать списку: %r", limit, INVESTMENT_LIMITS)
    return False


def get_transaction_investment_bank(date_value: str, transactions: list[Transaction]) -> list[Transaction]:
    """Вернуть список транзакций, которые участвуют в расчете суммы, отложенных средств в Инвесткопилку
    Args:
        date_value: дата в формате ``YYYY-MM``
    Returns:
          список транзакций
    """
    if not isinstance(date_value, str):
        logger.error(
            "Некорректный тип даты: %r",
            date_value,
        )
        return []

    try:
        parsed_date = datetime.strptime(date_value, "%Y-%m")
    except ValueError as error:
        logger.error(
            "Некорректный формат даты %r: %s",
            date_value,
            error,
        )
        return []

    if parsed_date.strftime("%Y-%m") != date_value:
        logger.error(
            "Дата не соответствует формату YYYY-MM: %r",
            date_value,
        )
        return []

    year, month = date_value.split("-")

    try:
        parsed_year = int(year)
        parsed_month = int(month)
    except (TypeError, ValueError) as error:
        logger.error(
            "Не удалось преобразовать период: year=%r, month=%r: %s",
            year,
            month,
            error,
        )
        return []

    try:
        _validate_period(parsed_year, parsed_month)
    except (TypeError, ValueError):
        return []

    filtered_transactions = [
        transaction for transaction in transactions if _transaction_matches_investment(transaction, year, month)
    ]

    logger.info(
        "За период год = %r и месяц = %r отобрано транзакций: %d",
        year,
        month,
        len(filtered_transactions),
    )
    return filtered_transactions


def get_total_amount(transactions: list[Transaction]) -> float:
    """Рассчитать общую сумму транзакций по полю amount_payment,
    используя абсолютные значения — без учёта знака плюс или минус.
    """
    total_amount = 0.0
    for transaction in transactions:
        raw_amount = get_field_value(
            transaction,
            "amount_payment",
            FIELD_ALIASES,
        )

        if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float)):
            logger.warning(
                "Пропущена транзакция с некорректной суммой: %r",
                raw_amount,
            )
            continue

        amount = abs(float(raw_amount))

        total_amount += amount

    return total_amount


def get_total_limit_amount(transactions: list[Transaction], limit: int) -> float:
    """Рассчитать общую сумму транзакций по полю amount_payment,
    используя абсолютные значения — без учёта знака плюс или минус.
    Поле amount_payment округленно по правилам до большего целого числа, соотвествующего значению limit
    """
    total_amount = 0.0
    for transaction in transactions:
        raw_amount = get_field_value(
            transaction,
            "amount_payment",
            FIELD_ALIASES,
        )

        if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float)):
            logger.warning(
                "Пропущена транзакция с некорректной суммой: %r",
                raw_amount,
            )
            continue

        amount = ceil(abs(float(raw_amount)) / limit) * limit

        total_amount += amount

    return total_amount


def _transaction_matches_search(
    transaction: Any,
    search_query: str,
) -> bool:
    """Проверить наличие строки в категории или описании транзакции."""
    if not isinstance(transaction, dict):
        logger.warning(
            "Пропущена транзакция неверного типа: %r",
            transaction,
        )
        return False

    category = get_field_value(
        transaction,
        "category",
        FIELD_ALIASES,
    )
    description = get_field_value(
        transaction,
        "descript",
        FIELD_ALIASES,
    )

    normalized_category = category.casefold() if isinstance(category, str) else ""
    normalized_description = description.casefold() if isinstance(description, str) else ""

    return search_query in normalized_category or search_query in normalized_description


def _valid_search_query(search_query: str) -> str | None:
    """Возвращает нормализированную строку поиска, в случае ошибки - None"""
    if not isinstance(search_query, str):
        logger.error(
            "Строка поиска должна иметь тип str: %r",
            search_query,
        )
        return None

    normalized_query = search_query.strip().casefold()

    if not normalized_query:
        logger.error("Получена пустая строка поиска")
        return None

    return normalized_query


def _valid_search_query_phone(search_query: str) -> str | None:
    """Проверить и нормализовать российский номер телефона."""
    if not isinstance(search_query, str):
        logger.error(
            "Строка поиска должна иметь тип str: %r",
            search_query,
        )
        return None

    normalized_query = search_query.strip()

    if not normalized_query:
        logger.error("Получена пустая строка поиска")
        return None

    if PHONE_PATTERN.fullmatch(normalized_query) is None:
        logger.warning(
            "Некорректный формат номера телефона: %r",
            search_query,
        )
        return None

    digits = re.sub(r"\D", "", normalized_query)

    if normalized_query.startswith("+7"):
        return f"+{digits}"

    return digits


def get_phone_transactions(
    transactions: list[Transaction],
) -> list[Transaction]:
    """Сгруппировать транзакции по найденным номерам телефонов."""
    grouped_transactions: dict[
        str,
        list[Transaction],
    ] = {}

    invalid_phone_count = 0
    invalid_phone_transactions: list[Transaction] = []

    for index, transaction in enumerate(transactions):
        if not isinstance(transaction, dict):
            logger.warning(
                "Транзакция %d пропущена: ожидался словарь",
                index,
            )
            continue

        description = get_field_value(
            transaction,
            "descript",
            FIELD_ALIASES,
        )

        if not isinstance(description, str):
            logger.debug(
                "Транзакция %d пропущена: отсутствует описание",
                index,
            )
            continue

        phone_candidates = list(
            PHONE_CANDIDATE_PATTERN.finditer(
                description,
            )
        )

        if not phone_candidates:
            continue

        transaction_has_invalid_phone = False

        for phone_match in phone_candidates:
            raw_phone = phone_match.group().strip()

            phone = _valid_search_query_phone(
                raw_phone,
            )

            if phone is None:
                invalid_phone_count += 1
                transaction_has_invalid_phone = True

                logger.warning(
                    "Транзакция %d содержит " "некорректный номер телефона %r",
                    index,
                    raw_phone,
                )
                continue

            grouped_transactions.setdefault(
                phone,
                [],
            ).append(transaction)

        if transaction_has_invalid_phone:
            invalid_phone_transactions.append(transaction)

    result: list[Transaction] = [
        {
            "phone": phone,
            "count": len(phone_transactions),
            "transactions": phone_transactions,
        }
        for phone, phone_transactions in grouped_transactions.items()
    ]

    if invalid_phone_count > 0:
        result.append(
            {
                "phone": "phone_error",
                "count": invalid_phone_count,
                "transactions": invalid_phone_transactions,
            }
        )

    logger.info(
        "Найдено корректных уникальных номеров: %d; " "некорректных кандидатов: %d",
        len(grouped_transactions),
        invalid_phone_count,
    )

    return result


def get_phone_group(
    transactions: list[Transaction],
) -> list[Transaction]:
    """Получение всего списка найденых телефонов и количество транзакций"""
    phone_transactions = get_phone_transactions(
        transactions,
    )

    result: list[dict[str, str | int]] = [
        {
            "phone": phone_group["phone"],
            "count": phone_group["count"],
        }
        for phone_group in phone_transactions
        if isinstance(phone_group.get("phone"), str)
        and isinstance(phone_group.get("count"), int)
        and not isinstance(phone_group.get("count"), bool)
    ]

    return result


def _normalize_name_part(value: str) -> str:
    """Нормализовать регистр части имени с поддержкой дефиса."""
    return "-".join(part[:1].upper() + part[1:].lower() for part in value.split("-"))


def _valid_search_query_person(
    search_query: Any,
) -> str | None:
    """Проверить имя и фамилию и привести их к формату: Имя Ф."""
    if not isinstance(search_query, str):
        logger.error(
            "Строка поиска должна иметь тип str: %r",
            search_query,
        )
        return None

    normalized_query = " ".join(search_query.strip().split())

    if not normalized_query:
        logger.error("Получена пустая строка поиска")
        return None

    person_match = PERSON_QUERY_PATTERN.fullmatch(
        normalized_query,
    )

    if person_match is None:
        logger.warning(
            "Некорректный формат имени и фамилии: %r",
            search_query,
        )
        return None

    name = _normalize_name_part(
        person_match.group("name"),
    )
    surname = person_match.group("surname").rstrip(".")

    return f"{name} {surname[0].upper()}."


def _get_person_from_transaction(
    transaction: Any,
) -> str | None:
    """Получить имя и инициал фамилии из транзакции-перевода."""
    if not isinstance(transaction, dict):
        logger.warning(
            "Пропущена транзакция неверного типа: %r",
            transaction,
        )
        return None

    category = get_field_value(
        transaction,
        "category",
        FIELD_ALIASES,
    )
    description = get_field_value(
        transaction,
        "descript",
        FIELD_ALIASES,
    )

    if not isinstance(category, str) or category.strip().casefold() != "переводы":
        return None

    if not isinstance(description, str):
        return None

    person_match = PERSON_TRANSFER_PATTERN.search(
        description.strip(),
    )

    if person_match is None:
        return None

    return person_match.group("person")


def get_person_transactions(
    transactions: list[Transaction],
) -> list[Transaction]:
    """Сгруппировать переводы по физическим лицам."""
    grouped_transactions: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for transaction in transactions:
        person = _get_person_from_transaction(
            transaction,
        )

        if person is None:
            continue

        grouped_transactions.setdefault(
            person,
            [],
        ).append(transaction)

    response: list[Transaction] = [
        {
            "person": person,
            "count": len(person_transactions),
            "transactions": person_transactions,
        }
        for person, person_transactions in grouped_transactions.items()
    ]

    logger.info(
        "Найдено физических лиц: %d; переводов: %d",
        len(response),
        sum(len(person_transactions) for person_transactions in grouped_transactions.values()),
    )

    return response


def get_person_group(
    transactions: list[Transaction],
) -> list[Transaction]:
    """Получение всего списка найденых физических лиц и количество транзакций"""
    person_transactions = get_person_transactions(
        transactions,
    )

    result: list[dict[str, str | int]] = [
        {
            "person": person_group["person"],
            "count": person_group["count"],
        }
        for person_group in person_transactions
        if isinstance(person_group.get("person"), str)
        and isinstance(person_group.get("count"), int)
        and not isinstance(person_group.get("count"), bool)
    ]

    return result
