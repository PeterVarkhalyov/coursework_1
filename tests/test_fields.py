"""Тесты поиска полей и загрузки пользовательских настроек."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src import fields


def test_get_by_path_returns_literal_key_with_priority() -> None:
    """Буквальный ключ с точкой имеет приоритет над вложенным путём."""
    item = {
        "currency.code": "USD",
        "currency": {"code": "RUB"},
    }

    assert fields.get_by_path(item, "currency.code") == "USD"


def test_get_by_path_returns_nested_value() -> None:
    """Значение доступно по пути с разделителем-точкой."""
    item = {"operation": {"currency": {"code": "RUB"}}}

    assert fields.get_by_path(item, "operation.currency.code") == "RUB"


def test_get_by_path_raises_key_error_for_missing_key() -> None:
    """Отсутствующий путь приводит к KeyError с исходным путём."""
    with pytest.raises(KeyError) as error:
        fields.get_by_path({}, "operation.currency.code")

    assert error.value.args == ("operation.currency.code",)


def test_get_by_path_wraps_type_error_as_key_error() -> None:
    """Невозможность продолжить обход вложенности преобразуется в KeyError."""
    with pytest.raises(KeyError) as error:
        fields.get_by_path({"currency": "RUB"}, "currency.code")

    assert error.value.args == ("currency.code",)


def test_get_field_value_returns_first_available_alias() -> None:
    """Поиск переходит к следующему псевдониму после отсутствующего пути."""
    transaction = {"operation": {"category": "Супермаркеты"}}
    aliases = {
        "category": [
            "Категория",
            "operation.category",
            "category",
        ]
    }

    assert fields.get_field_value(transaction, "category", aliases) == "Супермаркеты"


def test_get_field_value_returns_empty_list_for_unknown_field() -> None:
    """Неизвестное внутреннее имя поля даёт пустой результат."""
    assert fields.get_field_value({}, "missing", {}) == []


@pytest.mark.parametrize("aliases", [{"category": ["missing"]}, {"category": []}])
def test_get_field_value_returns_empty_list_when_transaction_has_no_alias(
    aliases: dict[str, list[str]],
) -> None:
    """Отсутствие всех вариантов поля даёт пустой результат."""
    assert fields.get_field_value({}, "category", aliases) == []


def test_load_user_settings_returns_expected_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Настройки возвращаются в установленном порядке."""
    payload = {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "MSFT"],
        "user_currency_quote": "RUB",
    }
    loader = Mock(return_value=payload)
    monkeypatch.setattr(fields, "get_fields_from_json", loader)
    path = Path("configs/user_settings.json")

    result = fields.load_user_settings(path)

    assert result == (["USD", "EUR"], ["AAPL", "MSFT"], "RUB")
    loader.assert_called_once_with(path)


def test_load_user_settings_raises_key_error_for_missing_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Отсутствие обязательной настройки не маскируется."""
    monkeypatch.setattr(
        fields,
        "get_fields_from_json",
        Mock(return_value={"user_currencies": [], "user_stocks": []}),
    )

    with pytest.raises(KeyError, match="user_currency_quote"):
        fields.load_user_settings("settings.json")


def test_load_user_settings_raises_type_error_for_invalid_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректный тип корневой структуры не маскируется."""
    monkeypatch.setattr(fields, "get_fields_from_json", Mock(return_value=[]))

    with pytest.raises(TypeError):
        fields.load_user_settings("settings.json")
