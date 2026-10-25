"""Тесты получения и преобразования котировок акций."""

from typing import Any, cast
from unittest.mock import Mock

import pytest
import requests

from src import stocks


def test_get_stock_rates_from_api_rejects_empty_ticker_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Для пустого списка тикеров запрос не выполняется."""
    get_key = Mock()
    monkeypatch.setattr(stocks, "get_api_key", get_key)

    assert stocks._get_stock_rates_from_api([]) is None
    get_key.assert_not_called()


def test_get_stock_rates_from_api_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Без API-ключа котировки получить невозможно."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value=None))
    get_response = Mock()
    monkeypatch.setattr(stocks, "get_response", get_response)

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None
    get_response.assert_not_called()


def test_get_stock_rates_from_api_handles_request_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сетевые ошибки преобразуются в отсутствие результата."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(
        stocks,
        "get_response",
        Mock(side_effect=requests.ConnectionError("unavailable")),
    )

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None


@pytest.mark.parametrize("response", [None, {}])
def test_get_stock_rates_from_api_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
    response: object,
) -> None:
    """Пустой ответ API не содержит котировок."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(stocks, "get_response", Mock(return_value=response))

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None


def test_get_stock_rates_from_api_rejects_message_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Поле message рассматривается как ошибка внешнего API."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(
        stocks,
        "get_response",
        Mock(return_value={"message": "invalid request"}),
    )

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None


def test_get_stock_rates_from_api_rejects_error_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Поле error рассматривается как ошибка внешнего API."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(
        stocks,
        "get_response",
        Mock(return_value={"error": {"code": 101}}),
    )

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None


@pytest.mark.parametrize("data", [None, {}, "wrong", 10])
def test_get_stock_rates_from_api_rejects_non_list_data(
    monkeypatch: pytest.MonkeyPatch,
    data: object,
) -> None:
    """Поле data должно содержать список котировок."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(
        stocks,
        "get_response",
        Mock(return_value={"data": data}),
    )

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None


def test_get_stock_rates_from_api_rejects_non_dictionary_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Каждая котировка в поле data должна быть словарём."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(
        stocks,
        "get_response",
        Mock(return_value={"data": [{"symbol": "AAPL"}, "wrong"]}),
    )

    assert stocks._get_stock_rates_from_api(["AAPL"]) is None


def test_get_stock_rates_from_api_returns_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Корректный список котировок возвращается без преобразований."""
    payload = [
        {"symbol": "AAPL", "adj_close": 200.0},
        {"symbol": "MSFT", "adj_close": 400.0},
    ]
    get_response = Mock(return_value={"data": payload})
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(stocks, "get_response", get_response)

    result = stocks._get_stock_rates_from_api(["AAPL", "MSFT"])

    assert result == payload
    get_response.assert_called_once_with(
        stocks.RATE_STOCKS_API,
        {
            "symbols": "AAPL,MSFT",
            "access_key": "secret",
        },
    )


def test_get_stock_rates_from_api_allows_empty_data_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустое поле data имеет правильный формат и возвращается как список."""
    monkeypatch.setattr(stocks, "get_api_key", Mock(return_value="secret"))
    monkeypatch.setattr(stocks, "get_response", Mock(return_value={"data": []}))

    assert stocks._get_stock_rates_from_api(["AAPL"]) == []


@pytest.mark.parametrize("price", [True, False, None, "10", [], {}])
def test_convert_stock_price_rejects_non_numeric_price(price: object) -> None:
    """Цена должна быть числом, но не логическим значением."""
    assert stocks._convert_stock_price(price, "USD", "RUB", {"USD": 0.01}, 2) is None


@pytest.mark.parametrize("price", [-0.01, -1, -100.0])
def test_convert_stock_price_rejects_negative_price(price: float) -> None:
    """Отрицательная стоимость акции недопустима."""
    assert stocks._convert_stock_price(price, "USD", "RUB", {"USD": 0.01}, 2) is None


@pytest.mark.parametrize("source_currency", [None, 10, "", "   "])
def test_convert_stock_price_uses_usd_for_missing_source_currency(
    source_currency: object,
) -> None:
    """Отсутствующий код исходной валюты заменяется на USD."""
    result = stocks._convert_stock_price(
        10.0,
        source_currency,
        "RUB",
        {"USD": 0.01},
        2,
    )

    assert result == 1000.0


def test_convert_stock_price_only_rounds_matching_currency() -> None:
    """При совпадении валют пересчёт не требуется."""
    result = stocks._convert_stock_price(
        123.456,
        " rub ",
        "RUB",
        {},
        2,
    )

    assert result == 123.46


@pytest.mark.parametrize("rate", [None, True, False, "0.01", [], 0, 0.0, -0.01])
def test_convert_stock_price_rejects_invalid_exchange_rate(rate: object) -> None:
    """Для пересчёта требуется положительный числовой курс."""
    assert stocks._convert_stock_price(10.0, "USD", "RUB", {"USD": rate}, 2) is None


def test_convert_stock_price_converts_and_rounds_value() -> None:
    """Стоимость пересчитывается в целевую валюту и округляется."""
    result = stocks._convert_stock_price(
        100.0,
        " usd ",
        "RUB",
        {"USD": 0.0123},
        2,
    )

    assert result == 8130.08


def test_calculate_stock_rates_rejects_non_string_currency() -> None:
    """Код целевой валюты должен быть строкой."""
    result = stocks._calculate_stock_rates(
        cast(Any, None),
        [{"symbol": "AAPL"}],
        2,
    )

    assert result is None


@pytest.mark.parametrize("digit", [True, False, 2.0, "2", -1])
def test_calculate_stock_rates_rejects_invalid_precision(digit: object) -> None:
    """Точность должна быть неотрицательным целым числом, но не bool."""
    result = stocks._calculate_stock_rates(
        "RUB",
        [{"symbol": "AAPL"}],
        cast(Any, digit),
    )

    assert result is None


def test_calculate_stock_rates_rejects_empty_quote_list() -> None:
    """Пустой список котировок невозможно обработать."""
    assert stocks._calculate_stock_rates("RUB", [], 2) is None


@pytest.mark.parametrize("rates", [None, [], "wrong", 10])
def test_calculate_stock_rates_requires_currency_rate_dictionary(
    monkeypatch: pytest.MonkeyPatch,
    rates: object,
) -> None:
    """Валютные курсы должны быть представлены словарём."""
    monkeypatch.setattr(
        stocks,
        "_get_currency_rates_from_api",
        Mock(return_value=rates),
    )

    result = stocks._calculate_stock_rates(
        " rub ",
        [{"symbol": "AAPL"}],
        2,
    )

    assert result is None


def test_calculate_stock_rates_converts_valid_items_and_skips_invalid_ones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Некорректные элементы пропускаются без потери корректных котировок."""
    monkeypatch.setattr(
        stocks,
        "_get_currency_rates_from_api",
        Mock(return_value={"USD": 0.0125}),
    )
    source_data = [
        "wrong",
        {
            "symbol": "BROKEN",
            "name": "Broken Corp.",
            "adj_close": "100",
            "price_currency": "USD",
        },
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "adj_close": 100.0,
            "price_currency": "USD",
        },
    ]

    result = stocks._calculate_stock_rates(
        " rub ",
        cast(Any, source_data),
        2,
    )

    assert result == [
        {
            "symbol": "AAPL",
            "stock_name": "Apple Inc.",
            "price_currency": "RUB",
            "adj_close": 8000.0,
        }
    ]


def test_calculate_stock_rates_returns_none_if_every_item_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Отсутствие корректных котировок обозначается значением None."""
    monkeypatch.setattr(
        stocks,
        "_get_currency_rates_from_api",
        Mock(return_value={"USD": 0.01}),
    )

    result = stocks._calculate_stock_rates(
        "RUB",
        [{"symbol": "BROKEN", "adj_close": None}],
        2,
    )

    assert result is None


@pytest.mark.parametrize(
    "error",
    [
        KeyError("setting"),
        TypeError("wrong type"),
        ValueError("wrong value"),
        OSError("unavailable"),
    ],
)
def test_get_stock_rates_handles_settings_error(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Ошибки пользовательских настроек не выходят за границы функции."""
    monkeypatch.setattr(stocks, "load_user_settings", Mock(side_effect=error))

    assert stocks.get_stock_rates() is None


def test_get_stock_rates_rejects_empty_ticker_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Без пользовательских тикеров запрос не выполняется."""
    monkeypatch.setattr(
        stocks,
        "load_user_settings",
        Mock(return_value=(["USD"], [], "RUB")),
    )
    api_request = Mock()
    monkeypatch.setattr(stocks, "_get_stock_rates_from_api", api_request)

    assert stocks.get_stock_rates() is None
    api_request.assert_not_called()


def test_get_stock_rates_rejects_empty_target_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без целевой валюты цены невозможно преобразовать."""
    monkeypatch.setattr(
        stocks,
        "load_user_settings",
        Mock(return_value=([], ["AAPL"], "")),
    )
    api_request = Mock()
    monkeypatch.setattr(stocks, "_get_stock_rates_from_api", api_request)

    assert stocks.get_stock_rates() is None
    api_request.assert_not_called()


@pytest.mark.parametrize("quotes", [None, []])
def test_get_stock_rates_returns_none_for_empty_api_result(
    monkeypatch: pytest.MonkeyPatch,
    quotes: object,
) -> None:
    """Пустой результат API не передаётся на конвертацию."""
    monkeypatch.setattr(
        stocks,
        "load_user_settings",
        Mock(return_value=([], ["AAPL"], "RUB")),
    )
    monkeypatch.setattr(
        stocks,
        "_get_stock_rates_from_api",
        Mock(return_value=quotes),
    )
    converter = Mock()
    monkeypatch.setattr(stocks, "_calculate_stock_rates", converter)

    assert stocks.get_stock_rates() is None
    converter.assert_not_called()


@pytest.mark.parametrize("converted", [None, []])
def test_get_stock_rates_returns_none_for_empty_conversion_result(
    monkeypatch: pytest.MonkeyPatch,
    converted: object,
) -> None:
    """Отсутствие рассчитанных котировок обозначается значением None."""
    raw_quotes = [{"symbol": "AAPL", "adj_close": 100.0}]
    monkeypatch.setattr(
        stocks,
        "load_user_settings",
        Mock(return_value=([], ["AAPL"], "RUB")),
    )
    monkeypatch.setattr(
        stocks,
        "_get_stock_rates_from_api",
        Mock(return_value=raw_quotes),
    )
    monkeypatch.setattr(
        stocks,
        "_calculate_stock_rates",
        Mock(return_value=converted),
    )

    assert stocks.get_stock_rates() is None


def test_get_stock_rates_returns_simplified_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Публичный результат содержит только тикер и рассчитанную цену."""
    raw_quotes = [
        {"symbol": "AAPL", "adj_close": 100.0},
        {"symbol": "MSFT", "adj_close": 200.0},
    ]
    converted_quotes = [
        {"symbol": "AAPL", "stock_name": "Apple", "price_currency": "RUB", "adj_close": 8000.0},
        {"symbol": "MSFT", "stock_name": "Microsoft", "price_currency": "RUB", "adj_close": 16000.0},
    ]
    load_settings = Mock(return_value=([], ["AAPL", "MSFT"], "RUB"))
    get_quotes = Mock(return_value=raw_quotes)
    convert_quotes = Mock(return_value=converted_quotes)
    monkeypatch.setattr(stocks, "load_user_settings", load_settings)
    monkeypatch.setattr(stocks, "_get_stock_rates_from_api", get_quotes)
    monkeypatch.setattr(stocks, "_calculate_stock_rates", convert_quotes)

    result = stocks.get_stock_rates()

    assert result == [
        {"stock": "AAPL", "price": 8000.0},
        {"stock": "MSFT", "price": 16000.0},
    ]
    get_quotes.assert_called_once_with(["AAPL", "MSFT"])
    convert_quotes.assert_called_once_with("RUB", raw_quotes, 2)
