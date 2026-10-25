"""Подготовка данных для главной страницы приложения."""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from math import isfinite
from pathlib import Path
from typing import Any, TypedDict, cast

from src.fields import get_field_value, load_fields
from src.readers import get_transactions_from_xls

Transaction = dict[str, Any]
Greeting = dict[str, str]

DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
OPERATIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "operations.xlsx"
FIELD_ALIASES_PATH = Path(__file__).resolve().parent.parent / "configs" / "field_aliases.json"

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("processing_views")
logger.setLevel(logging.DEBUG)
logger.propagate = False

file_handler = logging.FileHandler(
    LOG_DIR / "processing_views.log",
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)

file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


class CategoryResult(TypedDict):
    """Информация о категории транзакций."""

    category: str
    amount: float
    count: int


def _load_field_aliases() -> dict[str, list[str]]:
    """Загрузить и проверить справочник названий полей транзакций."""
    field_aliases = load_fields(FIELD_ALIASES_PATH)

    if not isinstance(field_aliases, dict):
        logger.error(
            "Не удалось загрузить справочник полей из %s: ожидался словарь, получено %s",
            FIELD_ALIASES_PATH,
            type(field_aliases).__name__,
        )
        return {}

    aliases_are_valid = all(
        isinstance(field_name, str) and isinstance(paths, list) and all(isinstance(path, str) for path in paths)
        for field_name, paths in field_aliases.items()
    )
    if not aliases_are_valid:
        logger.error("Справочник полей %s имеет некорректную структуру", FIELD_ALIASES_PATH)
        return {}

    logger.info("Справочник полей успешно загружен: %d полей", len(field_aliases))
    return cast(dict[str, list[str]], field_aliases)


FIELD_ALIASES = _load_field_aliases()


def _get_payment_amount(transaction: Transaction) -> float | None:
    """Вернуть конечную числовую сумму платежа или ``None``."""
    amount = get_field_value(transaction, "amount_payment", FIELD_ALIASES)

    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        logger.warning("Пропущена транзакция с некорректной суммой платежа: %r", amount)
        return None

    numeric_amount = float(amount)
    if not isfinite(numeric_amount):
        logger.warning("Пропущена транзакция с неконечной суммой платежа: %r", amount)
        return None

    return numeric_amount


def _get_last_digits(card_number: Any) -> str | None:
    """Вернуть последние четыре символа непустого номера карты."""
    if not isinstance(card_number, str) or not card_number.strip():
        logger.warning("Пропущена транзакция с некорректным номером карты: %r", card_number)
        return None

    return card_number.strip()[-4:]


def _parse_operation_datetime(value: Any) -> datetime | None:
    """Преобразовать дату и время операции из Excel или строки в ``datetime``."""
    if isinstance(value, datetime):
        if value != value:
            logger.warning("Пропущена транзакция с пустой датой операции")
            return None
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    if not isinstance(value, str) or not value.strip():
        logger.warning("Пропущена транзакция с некорректной датой операции: %r", value)
        return None

    normalized_value = value.strip()

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError:
        pass

    for date_format in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(normalized_value, date_format)
        except ValueError:
            continue

    logger.warning("Не удалось распознать дату операции: %r", value)
    return None


def _transaction_matches_view(
    transaction: Any,
    period_start: datetime,
    period_end: datetime,
    sent: bool,
    incoming: bool,
) -> bool:
    """Проверить, соответствует ли транзакция условиям представления."""
    if not isinstance(transaction, dict):
        logger.warning("Пропущена транзакция неверного типа: %r", transaction)
        return False

    if get_field_value(transaction, "status", FIELD_ALIASES) != "OK":
        return False

    operation_datetime = _parse_operation_datetime(get_field_value(transaction, "date_operation", FIELD_ALIASES))
    if operation_datetime is None:
        return False

    amount = _get_payment_amount(transaction)
    if sent and not incoming:
        if amount is None or amount >= 0:
            return False

    if incoming and not sent:
        amount = _get_payment_amount(transaction)
        if amount is None or amount < 0:
            return False

    try:
        return period_start <= operation_datetime <= period_end
    except TypeError as error:
        logger.warning(
            "Пропущена транзакция с несопоставимой датой %r: %s",
            operation_datetime,
            error,
        )
        return False


def get_greeting(date_time: str) -> list[Greeting]:
    """Вернуть приветствие, соответствующее времени суток."""
    logger.debug("Формирование приветствия для даты и времени: %r", date_time)

    try:
        parsed_date_time = datetime.strptime(date_time, DATE_TIME_FORMAT)
    except (TypeError, ValueError) as error:
        logger.exception("Некорректная дата и время для приветствия %r: %s", date_time, error)
        raise

    hour = parsed_date_time.hour

    if 5 <= hour < 12:
        greeting = "Доброе утро"
    elif 12 <= hour < 18:
        greeting = "Добрый день"
    elif 18 <= hour < 23:
        greeting = "Добрый вечер"
    else:
        greeting = "Доброй ночи"

    result = [{"greeting": greeting}]
    logger.info("Сформировано приветствие: %s", greeting)
    return result


def get_transactions() -> list[Transaction]:
    """Загрузить транзакции из ``data/operations.xlsx``."""
    logger.debug("Загрузка транзакций из файла: %s", OPERATIONS_PATH)

    try:
        transactions = get_transactions_from_xls(OPERATIONS_PATH)
    except (ImportError, OSError, ValueError) as error:
        logger.exception("Не удалось загрузить транзакции из %s: %s", OPERATIONS_PATH, error)
        return []

    if not isinstance(transactions, list):
        logger.error(
            "Функция чтения %s вернула %s вместо списка",
            OPERATIONS_PATH,
            type(transactions).__name__,
        )
        return []

    logger.info("Загружено транзакций: %d", len(transactions))
    return transactions


def get_transactions_view(
    date_time: str, sent: bool = True, incoming: bool = False, date_range: str = "M"
) -> list[Transaction]:
    """Вернуть успешные транзакции с начала месяца по указанный момент.

    Args:
        date_time: Дата и время в формате ``YYYY-MM-DD HH:MM:SS``.
        sent: Если ``True``, вернуть только расходные операции.

    Returns:
        Исходные словари транзакций со статусом ``OK``, дата и время операции
        которых входят в закрытый интервал от первого дня месяца в
        ``00:00:01`` до указанного момента включительно.
        Если подходящих транзакций нет, возвращается пустой список.

    Raises:
        TypeError: Если ``date_time`` не является строкой.
        TypeError: Если ``sent`` не является логическим значением.
        ValueError: Если значение не соответствует требуемому формату.
    """
    logger.debug("Фильтрация транзакций на момент %r; только расходы: %r", date_time, sent)

    if not isinstance(sent, bool):
        logger.error("Параметр sent должен иметь тип bool, получено: %r", sent)
        raise TypeError("sent должен иметь тип bool")

    try:
        parsed_date_time = datetime.strptime(date_time, DATE_TIME_FORMAT)
    except (TypeError, ValueError) as error:
        logger.exception("Некорректная дата окончания периода %r: %s", date_time, error)
        raise

    period_end = parsed_date_time
    if date_range.upper() == "W":
        period_start = (period_end - timedelta(days=period_end.weekday())).replace(
            hour=0, minute=0, second=1, microsecond=0
        )
    elif date_range.upper() == "M":
        period_start = period_end.replace(day=1, hour=0, minute=0, second=0)
    elif date_range.upper() == "Y":
        period_start = period_end.replace(month=1, day=1, hour=0, minute=0, second=0)
    else:
        period_start = period_end.replace(year=1900, month=1, day=1, hour=0, minute=0, second=0)

    transactions = get_transactions()
    filtered_transactions = [
        transaction
        for transaction in transactions
        if _transaction_matches_view(transaction, period_start, period_end, sent, incoming)
    ]

    logger.info(
        "За период с %s по %s отобрано транзакций: %d",
        period_start,
        period_end,
        len(filtered_transactions),
    )
    return filtered_transactions


def get_cards_summary(date_time: str) -> list[Transaction]:
    """Вернуть расходы и кешбэк по каждой банковской карте."""
    logger.debug("Формирование сводки по картам на момент: %r", date_time)
    transactions = get_transactions_view(date_time)
    summaries: dict[str, Transaction] = {}

    for transaction in transactions:
        amount = _get_payment_amount(transaction)
        if amount is None or amount >= 0:
            continue

        last_digits = _get_last_digits(get_field_value(transaction, "card_number", FIELD_ALIASES))
        if last_digits is None:
            continue

        if last_digits not in summaries:
            summaries[last_digits] = {
                "last_digits": last_digits,
                "total_spent": 0.0,
                "cashback": 0.0,
                "count": 0,
            }

        summaries[last_digits]["total_spent"] += amount
        summaries[last_digits]["count"] += 1

    result: list[Transaction] = []
    for summary in summaries.values():
        total_spent = abs(round(float(summary["total_spent"]), 2))
        total_count = summary["count"]
        result.append(
            {
                "last_digits": summary["last_digits"],
                "total_spent": total_spent,
                "cashback": round(total_spent / 100, 2),
                "count": total_count,
            }
        )

    logger.info("Сформирована сводка для банковских карт: %d", len(result))
    return result


def get_top_transactions(date_time: str, count_top: int) -> list[Transaction]:
    """Вернуть самые крупные успешные транзакции по модулю суммы."""
    logger.debug("Формирование топа транзакций на момент %r; количество: %r", date_time, count_top)

    if isinstance(count_top, bool) or not isinstance(count_top, int):
        logger.error("Некорректный тип count_top: %r", count_top)
        raise TypeError("count_top должен быть целым числом")

    if count_top < 0:
        logger.error("Получено отрицательное значение count_top: %d", count_top)
        raise ValueError("count_top не может быть отрицательным")

    if count_top == 0:
        logger.info("Запрошено ноль транзакций, возвращён пустой список")
        return []

    transactions = get_transactions_view(date_time)
    valid_transactions: list[tuple[Transaction, float]] = []

    for transaction in transactions:
        amount = _get_payment_amount(transaction)
        if amount is None:
            continue

        valid_transactions.append((transaction, amount))

    valid_transactions.sort(key=lambda item: abs(item[1]), reverse=True)

    result: list[Transaction] = []
    for transaction, amount in valid_transactions[:count_top]:
        result.append(
            {
                "date": get_field_value(transaction, "date_payment", FIELD_ALIASES),
                "amount": abs(amount),
                "category": get_field_value(transaction, "category", FIELD_ALIASES),
                "description": get_field_value(transaction, "descript", FIELD_ALIASES),
            }
        )

    logger.info("Сформирован топ транзакций: %d", len(result))
    return result


def _validate_category_arguments(
    transactions: list[dict[str, Any]],
    count_top: int,
    expenses: bool,
) -> None:
    """Проверить аргументы расчёта категорий."""
    if not isinstance(transactions, list):
        raise TypeError("transactions должен быть списком")

    if isinstance(count_top, bool) or not isinstance(count_top, int):
        raise TypeError("count_top должен быть целым числом")

    if count_top < 0:
        raise ValueError("count_top не может быть отрицательным")

    if not isinstance(expenses, bool):
        raise TypeError("expenses должен иметь тип bool")


def _get_category_amount(
    transaction: Any,
    index: int,
    expenses: bool,
) -> tuple[str, Decimal] | None:
    """Получить категорию и сумму подходящей транзакции."""
    if not isinstance(transaction, dict):
        logger.warning(
            "Транзакция %d пропущена: ожидался словарь",
            index,
        )
        return None

    category = get_field_value(transaction, "category", FIELD_ALIASES)
    raw_amount = get_field_value(transaction, "amount_payment", FIELD_ALIASES)

    if not isinstance(category, str) or not category.strip():
        logger.warning(
            "Транзакция %d пропущена: некорректная категория %r",
            index,
            category,
        )
        return None

    if isinstance(raw_amount, bool) or raw_amount is None:
        logger.warning(
            "Транзакция %d пропущена: некорректная сумма %r",
            index,
            raw_amount,
        )
        return None

    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, ValueError):
        logger.warning(
            "Транзакция %d пропущена: некорректная сумма %r",
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

    is_required_operation = amount < 0 if expenses else amount > 0

    if not is_required_operation:
        return None

    return category.strip(), abs(amount)


def _collect_category_totals(
    transactions: list[dict[str, Any]],
    expenses: bool,
) -> tuple[
    defaultdict[str, Decimal],
    defaultdict[str, int],
]:
    """Рассчитать сумму и количество транзакций по каждой категории."""
    category_totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    category_counts: defaultdict[str, int] = defaultdict(int)

    for index, transaction in enumerate(transactions):
        category_amount = _get_category_amount(
            transaction,
            index,
            expenses,
        )

        if category_amount is None:
            continue

        category, amount = category_amount
        category_totals[category] += amount
        category_counts[category] += 1

    return category_totals, category_counts


def _build_category_result(
    category_totals: defaultdict[str, Decimal],
    category_counts: defaultdict[str, int],
    count_top: int,
    digit_round: int = 0,
) -> list[CategoryResult]:
    """Сформировать топ категорий и категорию «Остальное»."""
    other_total = category_totals.pop("Остальное", Decimal("0"))
    other_count = category_counts.get("Остальное", 0)

    sorted_categories = sorted(
        ((category, amount) for category, amount in category_totals.items() if category != "Остальное"),
        key=lambda item: (-item[1], item[0]),
    )

    top_categories = sorted_categories[:count_top]
    remaining_categories = sorted_categories[count_top:]

    for category, amount in remaining_categories:
        other_total += amount
        other_count += category_counts.get(category, 0)

    result: list[CategoryResult] = [
        {
            "category": category,
            "amount": float(round(amount, digit_round)),
            "count": category_counts.get(category, 0),
        }
        for category, amount in top_categories
    ]

    if other_total > 0 or other_count > 0:
        result.append(
            {
                "category": "Остальное",
                "amount": float(round(other_total, digit_round)),
                "count": other_count,
            }
        )

    return result


def get_category_summary(
    date_time: str,
    date_range: str = "M",
    count_top: int = 7,
    expenses: bool = True,
) -> tuple[list[CategoryResult], float, int]:
    """Вернуть топ категорий расходов или поступлений."""
    if expenses:
        transactions = get_transactions_view(date_time, True, False, date_range)
    else:
        transactions = get_transactions_view(date_time, False, True, date_range)

    logger.debug(
        "Начало расчёта по категориям: " "транзакций=%d, count_top=%r, expenses=%s",
        len(transactions) if isinstance(transactions, list) else 0,
        count_top,
        expenses,
    )

    try:
        _validate_category_arguments(
            transactions,
            count_top,
            expenses,
        )
    except (TypeError, ValueError) as error:
        logger.error(
            "Некорректные аргументы расчёта категорий: %s",
            error,
        )
        raise

    category_totals, category_counts = _collect_category_totals(
        transactions,
        expenses,
    )

    result = _build_category_result(
        category_totals,
        category_counts,
        count_top,
    )

    result_total = sum(
        (float(item["amount"]) for item in result),
        start=0.0,
    )

    result_count = sum(
        (item["count"] for item in result),
        start=0,
    )

    logger.info(
        "Расчёт категорий завершён: возвращено элементов=%d",
        len(result),
    )

    return result, result_total, result_count
