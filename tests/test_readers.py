"""Тесты загрузки данных из Excel и JSON."""

import json
from pathlib import Path
from unittest.mock import Mock
from zipfile import BadZipFile

import pandas as pd
import pytest

from src import readers


def test_get_transactions_from_xls_returns_non_empty_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Полностью пустые строки пропускаются, остальные возвращаются."""
    data_frame = pd.DataFrame(
        [
            {"Описание": "Покупка", "Сумма": 100.0},
            {"Описание": "   ", "Сумма": float("nan")},
            {"Описание": None, "Сумма": 0.0},
        ]
    )
    read_excel = Mock(return_value=data_frame)
    monkeypatch.setattr(readers.pd, "read_excel", read_excel)

    result = readers.get_transactions_from_xls("operations.xlsx")

    assert len(result) == 2
    assert result[0]["Описание"] == "Покупка"
    assert result[1]["Сумма"] == 0.0
    read_excel.assert_called_once_with(
        "operations.xlsx",
        sheet_name="Отчет по операциям",
    )


def test_get_transactions_from_xls_returns_empty_list_for_empty_sheet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустой Excel-лист преобразуется в пустой список."""
    monkeypatch.setattr(readers.pd, "read_excel", Mock(return_value=pd.DataFrame()))

    assert readers.get_transactions_from_xls("empty.xlsx") == []


def test_get_transactions_from_xls_returns_rows_without_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Непустой лист без пустых строк возвращается полностью."""
    data_frame = pd.DataFrame(
        [
            {"Описание": "Покупка", "Сумма": 100.0},
            {"Описание": "Перевод", "Сумма": 250.0},
        ]
    )
    monkeypatch.setattr(readers.pd, "read_excel", Mock(return_value=data_frame))

    result = readers.get_transactions_from_xls("operations.xlsx")

    assert result == [
        {"Описание": "Покупка", "Сумма": 100.0},
        {"Описание": "Перевод", "Сумма": 250.0},
    ]


@pytest.mark.parametrize(
    "error",
    [
        OSError("file unavailable"),
        ValueError("sheet is missing"),
        ImportError("engine is missing"),
        BadZipFile("broken workbook"),
    ],
)
def test_get_transactions_from_xls_handles_expected_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Ожидаемые ошибки чтения Excel не выходят за границы функции."""
    monkeypatch.setattr(readers.pd, "read_excel", Mock(side_effect=error))

    assert readers.get_transactions_from_xls("broken.xlsx") == []


def test_get_fields_from_json_returns_dictionary(tmp_path: Path) -> None:
    """JSON-объект успешно загружается в словарь."""
    file_path = tmp_path / "settings.json"
    payload = {"currency": "RUB", "stocks": ["AAPL", "MSFT"]}
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    assert readers.get_fields_from_json(file_path) == payload


def test_get_fields_from_json_returns_empty_dictionary(tmp_path: Path) -> None:
    """Пустой JSON-объект является корректным результатом."""
    file_path = tmp_path / "empty-object.json"
    file_path.write_text("{}", encoding="utf-8")

    assert readers.get_fields_from_json(file_path) == {}


@pytest.mark.parametrize("payload", [[], [1], "text", 42, None])
def test_get_fields_from_json_rejects_non_object_root(
    tmp_path: Path,
    payload: object,
) -> None:
    """Корневым значением конфигурационного JSON должен быть объект."""
    file_path = tmp_path / "wrong-root.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    assert readers.get_fields_from_json(file_path) == []


def test_get_fields_from_json_handles_missing_file(tmp_path: Path) -> None:
    """Отсутствующий файл приводит к пустому результату."""
    assert readers.get_fields_from_json(tmp_path / "missing.json") == []


def test_get_fields_from_json_handles_invalid_json(tmp_path: Path) -> None:
    """Синтаксически некорректный JSON приводит к пустому результату."""
    file_path = tmp_path / "invalid.json"
    file_path.write_text("{invalid", encoding="utf-8")

    assert readers.get_fields_from_json(file_path) == []


def test_get_fields_from_json_handles_invalid_utf8(tmp_path: Path) -> None:
    """Файл в неподдерживаемой кодировке приводит к пустому результату."""
    file_path = tmp_path / "invalid-utf8.json"
    file_path.write_bytes(b"\xff\xfe\xfa")

    assert readers.get_fields_from_json(file_path) == []
