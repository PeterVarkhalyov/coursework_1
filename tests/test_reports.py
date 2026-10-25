"""Тесты формирования и сохранения отчётов."""

import importlib
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from src import reports


@pytest.fixture(autouse=True)
def isolate_reports_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    """Направить автоматически создаваемые отчёты во временный каталог."""
    reports_directory = tmp_path / "reports"
    monkeypatch.setattr(reports, "REPORTS_DIR", reports_directory)
    return reports_directory


@pytest.fixture
def transactions() -> pd.DataFrame:
    """Вернуть операции для проверки фильтрации и расчётов отчётов."""
    return pd.DataFrame(
        [
            {
                "Дата операции": "31.12.2023 09:00:00",
                "Сумма платежа": -50.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "Граница периода",
            },
            {
                "Дата операции": "01.01.2024 10:00:00",
                "Сумма платежа": -100.0,
                "Категория": " Супермаркеты ",
                "Статус": "OK",
                "Описание": "Первый понедельник",
            },
            {
                "Дата операции": "08.01.2024 11:00:00",
                "Сумма платежа": -300.0,
                "Категория": "супермаркеты",
                "Статус": "OK",
                "Описание": "Второй понедельник",
            },
            {
                "Дата операции": "02.01.2024 12:00:00",
                "Сумма платежа": -200.0,
                "Категория": "Транспорт",
                "Статус": "OK",
                "Описание": "Вторник",
            },
            {
                "Дата операции": "06.01.2024 13:00:00",
                "Сумма платежа": -400.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "Суббота",
            },
            {
                "Дата операции": "31.03.2024 23:59:59",
                "Сумма платежа": -150.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "Конец периода",
            },
            {
                "Дата операции": "30.12.2023 23:59:59",
                "Сумма платежа": -1000.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "До периода",
            },
            {
                "Дата операции": "01.04.2024 00:00:00",
                "Сумма платежа": -1000.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "После периода",
            },
            {
                "Дата операции": "10.01.2024 10:00:00",
                "Сумма платежа": 500.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "Поступление",
            },
            {
                "Дата операции": "11.01.2024 10:00:00",
                "Сумма платежа": -500.0,
                "Категория": "Супермаркеты",
                "Статус": "FAILED",
                "Описание": "Отклонённая операция",
            },
            {
                "Дата операции": "не дата",
                "Сумма платежа": -500.0,
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "Некорректная дата",
            },
            {
                "Дата операции": "12.01.2024 10:00:00",
                "Сумма платежа": "не сумма",
                "Категория": "Супермаркеты",
                "Статус": "OK",
                "Описание": "Некорректная сумма",
            },
        ]
    )


def test_report_to_file_without_parentheses_uses_default_filename(
    isolate_reports_directory: Path,
) -> None:
    """Декоратор без параметров сохраняет результат под стандартным именем."""

    @reports.report_to_file
    def sample_report() -> dict[str, str]:
        return {"сообщение": "готово"}

    assert sample_report() == {"сообщение": "готово"}

    report_path = isolate_reports_directory / "sample_report_report.json"
    assert json.loads(report_path.read_text(encoding="utf-8")) == {"сообщение": "готово"}


def test_report_to_file_with_positional_filename_saves_generic_result(tmp_path: Path) -> None:
    """Позиционный параметр декоратора определяет путь JSON-файла."""
    report_path = tmp_path / "custom" / "result.json"

    @reports.report_to_file(report_path)
    def sample_report() -> list[int]:
        return [1, 2, 3]

    assert sample_report() == [1, 2, 3]
    assert json.loads(report_path.read_text(encoding="utf-8")) == [1, 2, 3]


def test_report_to_file_with_keyword_filename_saves_result(tmp_path: Path) -> None:
    """Именованный параметр декоратора также определяет путь файла."""
    report_path = tmp_path / "keyword.json"

    @reports.report_to_file(filename=report_path)
    def sample_report() -> dict[str, int]:
        return {"count": 2}

    sample_report()

    assert json.loads(report_path.read_text(encoding="utf-8")) == {"count": 2}


def test_report_to_file_serializes_dataframe(
    isolate_reports_directory: Path,
) -> None:
    """Датафрейм сохраняется как JSON-массив записей с датами ISO."""

    @reports.report_to_file()
    def sample_report() -> pd.DataFrame:
        return pd.DataFrame([{"Дата": pd.Timestamp("2024-01-01"), "Сумма": 10.5}])

    result = sample_report()
    payload = json.loads((isolate_reports_directory / "sample_report_report.json").read_text(encoding="utf-8"))

    assert isinstance(result, pd.DataFrame)
    assert payload == [{"Дата": "2024-01-01T00:00:00.000", "Сумма": 10.5}]


def test_report_to_file_propagates_saving_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ошибка записи журналируется и передаётся вызывающему коду."""
    save_report_result = Mock(side_effect=OSError("нет доступа"))
    monkeypatch.setattr(reports, "_save_report_result", save_report_result)

    @reports.report_to_file(tmp_path / "unavailable.json")
    def sample_report() -> list[int]:
        return [1]

    with pytest.raises(OSError, match="нет доступа"):
        sample_report()

    save_report_result.assert_called_once()


def test_get_report_end_date_uses_current_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """При отсутствии даты используется текущий календарный день."""
    datetime_mock = Mock()
    datetime_mock.now.return_value = datetime(2024, 5, 20, 18, 30, 45)
    monkeypatch.setattr(reports, "datetime", datetime_mock)

    assert reports._get_report_end_date(None) == pd.Timestamp("2024-05-20")


def test_get_report_end_date_removes_time_zone() -> None:
    """Дата отчёта нормализуется до начала дня без часового пояса."""
    result = reports._get_report_end_date("2024-05-20T18:30:00+03:00")

    assert result == pd.Timestamp("2024-05-20")
    assert result.tzinfo is None


@pytest.mark.parametrize(
    ("date_value", "error_type", "message"),
    [
        (20240101, TypeError, "date должен иметь тип str или None"),
        ("   ", ValueError, "date не может быть пустой строкой"),
        ("некорректная дата", ValueError, "Не удалось распознать дату отчёта"),
        ("NaT", ValueError, "Не удалось распознать дату отчёта"),
    ],
)
def test_get_report_end_date_rejects_invalid_value(
    date_value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """Некорректная дата приводит к понятному исключению."""
    with pytest.raises(error_type, match=message):
        reports._get_report_end_date(date_value)  # type: ignore[arg-type]


def test_validate_report_columns_rejects_non_dataframe() -> None:
    """Отчёт принимает транзакции только в формате DataFrame."""
    with pytest.raises(TypeError, match="transactions должен иметь тип pandas.DataFrame"):
        reports._validate_report_columns([], {reports.DATE_COLUMN})  # type: ignore[arg-type]


def test_validate_report_columns_lists_missing_columns() -> None:
    """В исключении перечисляются отсутствующие обязательные столбцы."""
    with pytest.raises(ValueError, match="Категория, Сумма платежа"):
        reports._validate_report_columns(
            pd.DataFrame({"Дата операции": []}),
            {reports.DATE_COLUMN, reports.AMOUNT_COLUMN, reports.CATEGORY_COLUMN},
        )


def test_filter_expenses_without_status_column_includes_negative_amounts() -> None:
    """При отсутствии статуса фильтруются только дата и знак суммы."""
    source = pd.DataFrame(
        [
            {"Дата операции": "15.02.2024", "Сумма платежа": -25},
            {"Дата операции": "15.02.2024", "Сумма платежа": 30},
        ]
    )

    result = reports._filter_expenses_for_period(source, "2024-03-31")

    assert len(result) == 1
    assert result.iloc[0][reports.REPORT_EXPENSE_COLUMN] == 25


def test_filter_expenses_requires_category_when_requested() -> None:
    """Категория обязательна только для соответствующего отчёта."""
    source = pd.DataFrame([{"Дата операции": "15.02.2024", "Сумма платежа": -25}])

    with pytest.raises(ValueError, match="Категория"):
        reports._filter_expenses_for_period(
            source,
            "2024-03-31",
            require_category=True,
        )


def test_spending_by_category_filters_period_status_sign_and_category(
    transactions: pd.DataFrame,
    isolate_reports_directory: Path,
) -> None:
    """Отчёт возвращает только подходящие расходы выбранной категории."""
    result = reports.spending_by_category(
        transactions,
        "  СУПЕРМАРКЕТЫ ",
        "2024-03-31 10:30:00",
    )

    assert result["Описание"].tolist() == [
        "Граница периода",
        "Первый понедельник",
        "Второй понедельник",
        "Суббота",
        "Конец периода",
    ]
    assert result.index.tolist() == [0, 1, 2, 3, 4]
    assert not any(column.startswith("__report_") for column in result.columns)

    payload = json.loads((isolate_reports_directory / "spending_by_category_report.json").read_text(encoding="utf-8"))
    assert len(payload) == 5


@pytest.mark.parametrize(
    ("category", "error_type", "message"),
    [
        (10, TypeError, "category должен иметь тип str"),
        ("   ", ValueError, "category не может быть пустой строкой"),
    ],
)
def test_spending_by_category_rejects_invalid_category(
    transactions: pd.DataFrame,
    category: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """Категория должна быть непустой строкой."""
    with pytest.raises(error_type, match=message):
        reports.spending_by_category(
            transactions,
            category,  # type: ignore[arg-type]
            "2024-03-31",
        )


def test_spending_by_weekday_returns_all_weekdays(
    transactions: pd.DataFrame,
    isolate_reports_directory: Path,
) -> None:
    """Средняя сумма одной операции рассчитывается для каждого дня недели."""
    result = reports.spending_by_weekday(transactions, "2024-03-31")

    assert result.to_dict(orient="records") == [
        {"День недели": "Понедельник", "Средние траты": 200.0},
        {"День недели": "Вторник", "Средние траты": 200.0},
        {"День недели": "Среда", "Средние траты": 0.0},
        {"День недели": "Четверг", "Средние траты": 0.0},
        {"День недели": "Пятница", "Средние траты": 0.0},
        {"День недели": "Суббота", "Средние траты": 400.0},
        {"День недели": "Воскресенье", "Средние траты": 100.0},
    ]
    assert (isolate_reports_directory / "spending_by_weekday_report.json").is_file()


def test_spending_by_weekday_returns_zeroes_for_empty_period(transactions: pd.DataFrame) -> None:
    """Дни без расходных операций присутствуют в отчёте с нулём."""
    result = reports.spending_by_weekday(transactions, "2020-03-31")

    assert result["Средние траты"].tolist() == [0.0] * 7


def test_spending_by_workday_returns_workday_and_weekend_averages(
    transactions: pd.DataFrame,
    isolate_reports_directory: Path,
) -> None:
    """Рабочие и выходные дни рассчитываются по отдельным группам."""
    result = reports.spending_by_workday(transactions, "2024-03-31")

    assert result.to_dict(orient="records") == [
        {"Тип дня": "Рабочий день", "Средние траты": 200.0},
        {"Тип дня": "Выходной день", "Средние траты": 200.0},
    ]
    assert (isolate_reports_directory / "spending_by_workday_report.json").is_file()


def test_spending_by_workday_returns_zeroes_for_empty_period(transactions: pd.DataFrame) -> None:
    """При отсутствии расходов обе группы возвращаются с нулевыми значениями."""
    result = reports.spending_by_workday(transactions, "2020-03-31")

    assert result["Средние траты"].tolist() == [0.0, 0.0]


def test_module_reload_does_not_add_duplicate_log_handler() -> None:
    """Повторная загрузка модуля не добавляет второй обработчик логов."""
    handlers_before = list(reports.logger.handlers)

    reloaded_reports = importlib.reload(reports)

    assert reloaded_reports.logger.handlers == handlers_before
