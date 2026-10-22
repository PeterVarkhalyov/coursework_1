"""Формирование и сохранение отчётов по банковским транзакциям."""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar, cast, overload

import pandas as pd

TransactionResult = TypeVar("TransactionResult")
ReportParameters = ParamSpec("ReportParameters")

DATE_COLUMN = "Дата операции"
AMOUNT_COLUMN = "Сумма платежа"
CATEGORY_COLUMN = "Категория"
STATUS_COLUMN = "Статус"

REPORT_DATE_COLUMN = "__report_date"
REPORT_AMOUNT_COLUMN = "__report_amount"
REPORT_EXPENSE_COLUMN = "__report_expense"

WEEKDAY_NAMES = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]
DAY_TYPE_NAMES = ["Рабочий день", "Выходной день"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("reports")
logger.setLevel(logging.DEBUG)
logger.propagate = False

if not logger.handlers:
    file_handler = logging.FileHandler(
        LOG_DIR / "reports.log",
        mode="w",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - " "%(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)


def _save_report_result(result: Any, file_path: Path) -> None:
    """Сохранить результат отчёта в JSON-файл."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(result, pd.DataFrame):
        result.to_json(
            file_path,
            orient="records",
            force_ascii=False,
            date_format="iso",
            indent=2,
        )
        return

    with file_path.open("w", encoding="utf-8") as report_file:
        json.dump(
            result,
            report_file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def _decorate_report(
    function: Callable[ReportParameters, TransactionResult],
    filename: str | Path | None,
) -> Callable[ReportParameters, TransactionResult]:
    """Обернуть функцию записью возвращаемого результата в файл."""

    @wraps(function)
    def wrapper(
        *args: ReportParameters.args,
        **kwargs: ReportParameters.kwargs,
    ) -> TransactionResult:
        result = function(*args, **kwargs)
        report_path = Path(filename) if filename is not None else REPORTS_DIR / f"{function.__name__}_report.json"

        try:
            _save_report_result(result, report_path)
        except (OSError, TypeError, ValueError) as error:
            logger.exception(
                "Не удалось сохранить отчёт %s в %s: %s",
                function.__name__,
                report_path,
                error,
            )
            raise

        logger.info(
            "Отчёт %s сохранён в %s",
            function.__name__,
            report_path,
        )
        return result

    return wrapper


@overload
def report_to_file(
    function_or_filename: Callable[ReportParameters, TransactionResult],
    *,
    filename: None = None,
) -> Callable[ReportParameters, TransactionResult]:
    pass  # pragma: no cover - декларация типа, во время выполнения недоступна


@overload
def report_to_file(
    function_or_filename: str | Path | None = None,
    *,
    filename: str | Path | None = None,
) -> Callable[
    [Callable[ReportParameters, TransactionResult]],
    Callable[ReportParameters, TransactionResult],
]:
    pass  # pragma: no cover - декларация типа, во время выполнения недоступна


def report_to_file(
    function_or_filename: Callable[..., Any] | str | Path | None = None,
    *,
    filename: str | Path | None = None,
) -> Callable[..., Any]:
    """Сохранить результат функции-отчёта в JSON.

    Поддерживаемые варианты применения::

        @report_to_file
        @report_to_file()
        @report_to_file("custom_report.json")
        @report_to_file(filename="custom_report.json")
    """
    if callable(function_or_filename):
        return _decorate_report(function_or_filename, filename)

    report_filename = filename if filename is not None else cast(str | Path | None, function_or_filename)

    def decorator(
        function: Callable[ReportParameters, TransactionResult],
    ) -> Callable[ReportParameters, TransactionResult]:
        return _decorate_report(function, report_filename)

    return decorator


def _get_report_end_date(date_value: str | None) -> pd.Timestamp:
    """Вернуть конечную календарную дату отчётного периода."""
    if date_value is None:
        return pd.Timestamp(datetime.now()).normalize()

    if not isinstance(date_value, str):
        raise TypeError("date должен иметь тип str или None")

    normalized_date = date_value.strip()
    if not normalized_date:
        raise ValueError("date не может быть пустой строкой")

    try:
        report_date = pd.Timestamp(normalized_date)
    except (TypeError, ValueError) as error:
        raise ValueError("Не удалось распознать дату отчёта") from error

    if pd.isna(report_date):
        raise ValueError("Не удалось распознать дату отчёта")

    if report_date.tzinfo is not None:
        report_date = report_date.tz_localize(None)

    return report_date.normalize()


def _validate_report_columns(
    transactions: pd.DataFrame,
    required_columns: set[str],
) -> None:
    """Проверить тип таблицы и наличие обязательных столбцов."""
    if not isinstance(transactions, pd.DataFrame):
        raise TypeError("transactions должен иметь тип pandas.DataFrame")

    missing_columns = required_columns.difference(transactions.columns)
    if missing_columns:
        missing_names = ", ".join(sorted(missing_columns))
        raise ValueError(f"В transactions отсутствуют столбцы: {missing_names}")


def _filter_expenses_for_period(
    transactions: pd.DataFrame,
    date_value: str | None,
    *,
    require_category: bool = False,
) -> pd.DataFrame:
    """Отобрать успешные расходы за три месяца по конечную дату включительно."""
    required_columns = {DATE_COLUMN, AMOUNT_COLUMN}
    if require_category:
        required_columns.add(CATEGORY_COLUMN)

    _validate_report_columns(transactions, required_columns)
    period_end = _get_report_end_date(date_value)
    period_start = period_end - pd.DateOffset(months=3)
    period_end_exclusive = period_end + pd.Timedelta(days=1)

    prepared = transactions.copy()
    prepared[REPORT_DATE_COLUMN] = pd.to_datetime(
        prepared[DATE_COLUMN],
        errors="coerce",
        dayfirst=True,
    )
    prepared[REPORT_AMOUNT_COLUMN] = pd.to_numeric(
        prepared[AMOUNT_COLUMN],
        errors="coerce",
    )

    period_mask = prepared[REPORT_DATE_COLUMN].ge(period_start) & prepared[REPORT_DATE_COLUMN].lt(period_end_exclusive)
    expense_mask = prepared[REPORT_AMOUNT_COLUMN].lt(0)
    result_mask = period_mask & expense_mask

    if STATUS_COLUMN in prepared.columns:
        status_mask = prepared[STATUS_COLUMN].astype("string").str.strip().eq("OK").fillna(False)
        result_mask &= status_mask

    result = prepared.loc[result_mask].copy()
    result[REPORT_EXPENSE_COLUMN] = result[REPORT_AMOUNT_COLUMN].abs()

    logger.debug(
        "За период %s—%s отобрано расходов: %d",
        period_start.date(),
        period_end.date(),
        len(result),
    )
    return result


@report_to_file()
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: str | None = None,
) -> pd.DataFrame:
    """Вернуть траты по категории за последние три месяца."""
    if not isinstance(category, str):
        raise TypeError("category должен иметь тип str")

    normalized_category = category.strip().casefold()
    if not normalized_category:
        raise ValueError("category не может быть пустой строкой")

    expenses = _filter_expenses_for_period(
        transactions,
        date,
        require_category=True,
    )
    category_mask = (
        expenses[CATEGORY_COLUMN].astype("string").str.strip().str.casefold().eq(normalized_category).fillna(False)
    )
    result = expenses.loc[category_mask].drop(
        columns=[
            REPORT_DATE_COLUMN,
            REPORT_AMOUNT_COLUMN,
            REPORT_EXPENSE_COLUMN,
        ]
    )

    logger.info(
        "Для категории %r сформирован отчёт из %d транзакций",
        category,
        len(result),
    )
    return result.reset_index(drop=True)


@report_to_file()
def spending_by_weekday(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> pd.DataFrame:
    """Вернуть средние траты по дням недели за последние три месяца."""
    expenses = _filter_expenses_for_period(transactions, date)
    weekday_numbers = expenses[REPORT_DATE_COLUMN].dt.dayofweek
    average_expenses = (
        expenses.assign(__weekday=weekday_numbers)
        .groupby("__weekday", observed=False)[REPORT_EXPENSE_COLUMN]
        .mean()
        .reindex(range(7), fill_value=0.0)
    )

    result = pd.DataFrame(
        {
            "День недели": WEEKDAY_NAMES,
            "Средние траты": [round(float(amount), 2) for amount in average_expenses.tolist()],
        }
    )

    logger.info("Сформирован отчёт по дням недели")
    return result


@report_to_file()
def spending_by_workday(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> pd.DataFrame:
    """Вернуть средние траты в рабочие и выходные дни за три месяца."""
    expenses = _filter_expenses_for_period(transactions, date)
    day_types = expenses[REPORT_DATE_COLUMN].dt.dayofweek.map(
        lambda weekday: DAY_TYPE_NAMES[0] if weekday < 5 else DAY_TYPE_NAMES[1]
    )
    average_expenses = (
        expenses.assign(__day_type=day_types)
        .groupby("__day_type", observed=False)[REPORT_EXPENSE_COLUMN]
        .mean()
        .reindex(DAY_TYPE_NAMES, fill_value=0.0)
    )

    result = pd.DataFrame(
        {
            "Тип дня": DAY_TYPE_NAMES,
            "Средние траты": [round(float(amount), 2) for amount in average_expenses.tolist()],
        }
    )

    logger.info("Сформирован отчёт по рабочим и выходным дням")
    return result
