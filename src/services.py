"""Сервисы анализа банковских транзакций."""

import json
from typing import Any

from src.processing_services import (
    _collect_category_cashback,
    _transaction_matches_search,
    _valid_search_query,
    _valid_search_query_person,
    _valid_search_query_phone,
    get_person_transactions,
    get_phone_transactions,
    get_total_amount,
    get_total_limit_amount,
    get_transaction_investment_bank,
    get_transactions_cashback,
    valid_limit,
)


def get_category_cashback(year: str, month: str) -> str:
    """Вернуть JSON с анализом кешбэка по категориям."""
    transactions = get_transactions_cashback(year, month)
    if not transactions:
        return json.dumps([], ensure_ascii=False)

    category_cashback, _ = _collect_category_cashback(transactions)

    response = {category: float(cashback) for category, cashback in category_cashback.items()}

    return json.dumps(response, ensure_ascii=False)


def investment_bank(month: str, transactions: list[dict[str, Any]], limit: int) -> float | None:
    """Вернуть значение суммы, которую удалось бы отложить в Инвесткопилку"""
    if not valid_limit(limit):
        return None

    invest_transactions = get_transaction_investment_bank(month, transactions)

    total_amount = get_total_amount(invest_transactions)

    limit_total_amount = get_total_limit_amount(invest_transactions, limit)

    invest_amount = round(limit_total_amount - total_amount, 2)
    if invest_amount < 0:
        return None

    return invest_amount


def get_transactions_search(transactions: list[dict[str, Any]], search_query: str) -> str:
    """Вернуть JSON с найденными транзакциями и их количеством."""
    normalized_query = _valid_search_query(search_query)

    if normalized_query is None:
        return json.dumps(
            {
                "count": 0,
                "result": [],
            },
            ensure_ascii=False,
        )

    found_transactions = list(
        filter(
            lambda transaction: _transaction_matches_search(
                transaction,
                normalized_query,
            ),
            transactions,
        )
    )

    response = {
        "count": len(found_transactions),
        "result": found_transactions,
    }

    return json.dumps(
        response,
        ensure_ascii=False,
        default=str,
    )


def get_transactions_search_phone(transactions: list[dict[str, Any]], phone_num: str) -> str:
    """Вернуть JSON с найденными транзакциями и их количеством по номеру телефона."""
    normalized_query = _valid_search_query_phone(phone_num)

    if normalized_query is None:
        return json.dumps(
            {
                "phone": "None",
                "count": 0,
                "result": [],
            },
            ensure_ascii=False,
        )

    phone_groups = get_phone_transactions(transactions)

    found_group = next(
        (
            phone_group
            for phone_group in phone_groups
            if isinstance(phone_group, dict) and phone_group.get("phone") == normalized_query
        ),
        None,
    )

    if found_group is None:
        response = {
            "phone": "None",
            "count": 0,
            "result": [],
        }
    else:
        found_transactions = found_group.get(
            "transactions",
            [],
        )

        if not isinstance(found_transactions, list):
            found_transactions = []

        response = {
            "phone": normalized_query,
            "count": len(found_transactions),
            "result": found_transactions,
        }

    return json.dumps(
        response,
        ensure_ascii=False,
        default=str,
    )


def get_transactions_search_phone_total(transactions: list[dict[str, Any]]) -> str:
    """Вернуть JSON-ответ со всеми транзакциями, содержащими номера телефонов
    и отдельно номера, которые не прошли валидацию."""
    phone_groups = get_phone_transactions(transactions)

    total_count = 0
    result_transactions: list[dict[str, Any]] = []
    error_count = 0
    error_transactions: list[dict[str, Any]] = []

    for phone_group in phone_groups:
        group_transactions = phone_group.get(
            "transactions",
            [],
        )

        if not isinstance(group_transactions, list):
            continue

        group_count = phone_group.get("count")
        phone = phone_group.get("phone")

        if isinstance(group_count, int) and not isinstance(group_count, bool) and group_count >= 0:
            if phone == "phone_error":
                error_count += group_count
            else:
                total_count += group_count
        else:
            if phone == "phone_error":
                error_count += len(group_transactions)
            else:
                total_count += len(group_transactions)

        if phone == "phone_error":
            error_transactions.extend(group_transactions)
        else:
            result_transactions.extend(group_transactions)

    response = {
        "total": total_count + error_count,
        "result": {"count": total_count, "transactions": result_transactions},
        "error": {"count": error_count, "transactions": error_transactions},
    }

    return json.dumps(
        response,
        ensure_ascii=False,
        default=str,
    )


def get_transactions_search_person(transactions: list[dict[str, Any]], person: str) -> str:
    """Вернуть JSON с найденными транзакциями и их количеством по заданному физическом лицу.
    Args:
        transactions - список исследуемых транзакций
        person - физическое лицо, формат: Имя Ф.
    """
    normalized_person = _valid_search_query_person(person)
    if normalized_person is None:
        return json.dumps(
            {
                "person": "None",
                "count": 0,
                "result": [],
            },
            ensure_ascii=False,
        )

    person_groups = get_person_transactions(transactions)

    found_group = next(
        (
            person_group
            for person_group in person_groups
            if isinstance(person_group, dict) and person_group.get("person") == normalized_person
        ),
        None,
    )

    if found_group is None:
        response = {
            "person": normalized_person,
            "count": 0,
            "result": [],
        }
    else:
        found_transactions = found_group.get(
            "transactions",
            [],
        )

        if not isinstance(found_transactions, list):
            found_transactions = []

        response = {
            "person": normalized_person,
            "count": len(found_transactions),
            "result": found_transactions,
        }

    return json.dumps(
        response,
        ensure_ascii=False,
        default=str,
    )


def get_transactions_total_person(transactions: list[dict[str, Any]]) -> str:
    """Вернуть JSON-ответ со всеми транзакциями, содержащими переводы физическим лицам."""
    person_groups = get_person_transactions(transactions)

    total_count = 0
    result_transactions: list[dict[str, Any]] = []

    for person_group in person_groups:
        group_transactions = person_group.get(
            "transactions",
            [],
        )

        if not isinstance(group_transactions, list):
            continue

        group_count = person_group.get("count")

        if isinstance(group_count, int) and not isinstance(group_count, bool) and group_count >= 0:
            total_count += group_count
        else:
            total_count += len(group_transactions)

        result_transactions.extend(group_transactions)

    response = {
        "count": total_count,
        "transactions": result_transactions,
    }

    return json.dumps(
        response,
        ensure_ascii=False,
        default=str,
    )
