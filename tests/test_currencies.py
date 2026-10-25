"""Тесты получения и расчёта валютных котировок."""

from unittest.mock import Mock

import pytest
import requests

from src import currencies


def test_get_currency_rates_from_api_returns_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Корректное поле rates возвращается вызывающему коду."""
    response = {
        "result": "success",
        "rates": {"USD": 0.0125, "EUR": 0.01},
    }
    get_response = Mock(return_value=response)
    monkeypatch.setattr(currencies, "get_response", get_response)

    result = currencies._get_currency_rates_from_api("RUB")

    assert result == {"USD": 0.0125, "EUR": 0.01}
    get_response.assert_called_once_with(
        currencies.RATES_CURRENCY_API + "RUB",
        {},
    )


def test_get_currency_rates_from_api_handles_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сетевая ошибка преобразуется в отсутствие результата."""
    monkeypatch.setattr(
        currencies,
        "get_response",
        Mock(side_effect=requests.Timeout("timeout")),
    )

    assert currencies._get_currency_rates_from_api("RUB") is None


@pytest.mark.parametrize("response", [None, {}])
def test_get_currency_rates_from_api_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
    response: object,
) -> None:
    """Пустой ответ API не содержит котировок."""
    monkeypatch.setattr(currencies, "get_response", Mock(return_value=response))

    assert currencies._get_currency_rates_from_api("RUB") is None


@pytest.mark.parametrize(
    "response",
    [
        {"result": "error", "error-type": "unsupported-code"},
        {"result": "error"},
    ],
)
def test_get_currency_rates_from_api_rejects_api_error(
    monkeypatch: pytest.MonkeyPatch,
    response: dict[str, str],
) -> None:
    """Сообщение об ошибке внешнего сервиса обрабатывается явно."""
    monkeypatch.setattr(currencies, "get_response", Mock(return_value=response))

    assert currencies._get_currency_rates_from_api("RUB") is None


@pytest.mark.parametrize("rates", [None, [], "wrong", 10])
def test_get_currency_rates_from_api_rejects_invalid_rates(
    monkeypatch: pytest.MonkeyPatch,
    rates: object,
) -> None:
    """Поле rates должно быть словарём."""
    monkeypatch.setattr(
        currencies,
        "get_response",
        Mock(return_value={"result": "success", "rates": rates}),
    )

    assert currencies._get_currency_rates_from_api("RUB") is None


def test_calculate_currency_quote_returns_inverse_rate() -> None:
    """Прямой курс преобразуется в обратный и округляется."""
    result = currencies._calculate_currency_quote(
        "USD",
        {"USD": 0.0123},
        2,
    )

    assert result == {"currency": "USD", "rate": 81.3}


def test_calculate_currency_quote_rejects_negative_precision() -> None:
    """Отрицательная точность округления недопустима."""
    assert currencies._calculate_currency_quote("USD", {"USD": 1.0}, -1) is None


def test_calculate_currency_quote_returns_none_for_missing_currency() -> None:
    """Отсутствующий код валюты пропускается."""
    assert currencies._calculate_currency_quote("USD", {}, 2) is None


@pytest.mark.parametrize("rate", [True, False, "0.01", [], {}])
def test_calculate_currency_quote_rejects_non_numeric_rate(rate: object) -> None:
    """Логические и другие нечисловые значения не являются курсами."""
    assert currencies._calculate_currency_quote("USD", {"USD": rate}, 2) is None


@pytest.mark.parametrize("rate", [0, 0.0, -0.01, -1])
def test_calculate_currency_quote_rejects_non_positive_rate(rate: int | float) -> None:
    """Нулевой и отрицательный курс недопустимы."""
    assert currencies._calculate_currency_quote("USD", {"USD": rate}, 2) is None


def test_build_currency_quotes_keeps_only_valid_values() -> None:
    """В итоговый список входят только успешно рассчитанные валюты."""
    result = currencies._build_currency_quotes(
        ["USD", "EUR", "CNY"],
        {"USD": 0.01, "EUR": 0, "CNY": 0.1},
        2,
    )

    assert result == [
        {"currency": "USD", "rate": 100.0},
        {"currency": "CNY", "rate": 10.0},
    ]


def test_build_currency_quotes_returns_empty_list_for_empty_input() -> None:
    """Пустой список валют создаёт пустой список котировок."""
    assert currencies._build_currency_quotes([], {"USD": 0.01}, 2) == []


@pytest.mark.parametrize(
    "error",
    [
        KeyError("setting"),
        TypeError("wrong type"),
        ValueError("wrong value"),
        OSError("unavailable"),
    ],
)
def test_get_currency_rates_handles_settings_error(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Ошибки загрузки настроек приводят к отсутствию результата."""
    monkeypatch.setattr(currencies, "load_user_settings", Mock(side_effect=error))

    assert currencies.get_currency_rates() is None


def test_get_currency_rates_rejects_empty_currency_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Для пустого списка пользовательских валют запрос не выполняется."""
    monkeypatch.setattr(
        currencies,
        "load_user_settings",
        Mock(return_value=([], ["AAPL"], "RUB")),
    )
    api_request = Mock()
    monkeypatch.setattr(currencies, "_get_currency_rates_from_api", api_request)

    assert currencies.get_currency_rates() is None
    api_request.assert_not_called()


def test_get_currency_rates_rejects_empty_base_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без базовой валюты котировки рассчитать нельзя."""
    monkeypatch.setattr(
        currencies,
        "load_user_settings",
        Mock(return_value=(["USD"], [], "")),
    )
    api_request = Mock()
    monkeypatch.setattr(currencies, "_get_currency_rates_from_api", api_request)

    assert currencies.get_currency_rates() is None
    api_request.assert_not_called()


def test_get_currency_rates_returns_none_when_api_has_no_rates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Отсутствие курсов от API передаётся как None."""
    monkeypatch.setattr(
        currencies,
        "load_user_settings",
        Mock(return_value=(["USD"], [], "RUB")),
    )
    monkeypatch.setattr(
        currencies,
        "_get_currency_rates_from_api",
        Mock(return_value=None),
    )

    assert currencies.get_currency_rates() is None


def test_get_currency_rates_returns_none_when_no_quote_can_be_calculated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустой результат расчёта считается ошибкой."""
    monkeypatch.setattr(
        currencies,
        "load_user_settings",
        Mock(return_value=(["USD"], [], "RUB")),
    )
    monkeypatch.setattr(
        currencies,
        "_get_currency_rates_from_api",
        Mock(return_value={"USD": 0.01}),
    )
    monkeypatch.setattr(
        currencies,
        "_build_currency_quotes",
        Mock(return_value=[]),
    )

    assert currencies.get_currency_rates() is None


def test_get_currency_rates_returns_calculated_quotes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Публичная функция возвращает подготовленный список котировок."""
    load_settings = Mock(return_value=(["USD", "EUR"], ["AAPL"], "RUB"))
    get_rates = Mock(return_value={"USD": 0.01, "EUR": 0.008})
    build_quotes = Mock(
        return_value=[
            {"currency": "USD", "rate": 100.0},
            {"currency": "EUR", "rate": 125.0},
        ]
    )
    monkeypatch.setattr(currencies, "load_user_settings", load_settings)
    monkeypatch.setattr(currencies, "_get_currency_rates_from_api", get_rates)
    monkeypatch.setattr(currencies, "_build_currency_quotes", build_quotes)

    result = currencies.get_currency_rates()

    assert result == [
        {"currency": "USD", "rate": 100.0},
        {"currency": "EUR", "rate": 125.0},
    ]
    get_rates.assert_called_once_with("RUB")
    build_quotes.assert_called_once_with(
        ["USD", "EUR"],
        {"USD": 0.01, "EUR": 0.008},
        2,
    )
