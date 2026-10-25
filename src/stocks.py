"""Функции обработки информации, полученной от внешних API для котировок акций."""

import logging
from pathlib import Path
from typing import Any

import requests

from src.api_responses import get_api_key, get_response
from src.currencies import _get_currency_rates_from_api
from src.fields import load_user_settings

Transaction = dict[str, Any]

RATE_STOCKS_API = "https://api.apilayer.net/marketstack/v2/eod/latest"


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("stocks")
logger.setLevel(logging.DEBUG)
logger.propagate = False

file_handler = logging.FileHandler(
    LOG_DIR / "stocks.log",
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)

file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def _get_stock_rates_from_api(
    stocks: list[str],
) -> list[Transaction] | None:
    """Получает словарь котировок от API.

    Args:
        stocks - список акций для которых необходимо получить котировки

    Returns:
        Список котировок акций

    """
    if not stocks:
        logger.error("Список тикеров акций пуст")
        return None

    api_key = get_api_key("RATES_API_KEY")

    if not api_key:
        logger.error("Не найден API-ключ для получения котировок")
        return None

    request_param: dict[str, str | float] = {
        "symbols": ",".join(stocks),
        "access_key": api_key,
    }

    try:
        data_json = get_response(
            RATE_STOCKS_API,
            request_param,
        )
    except requests.RequestException as error:
        logger.exception(
            "Ошибка запроса котировок акций по адресу %s: %s",
            RATE_STOCKS_API,
            error,
        )
        return None

    if not data_json:
        logger.error("API не вернул данные о котировках акций")
        return None

    api_message = data_json.get("message")

    if api_message:
        logger.error(
            "API вернул ошибку: %s",
            data_json.get("message"),
        )
        return None

    api_error = data_json.get("error")

    if api_error:
        logger.error("API вернул ошибку: %s", api_error)
        return None

    stock_rates = data_json.get("data")

    if not isinstance(stock_rates, list):
        logger.error(
            "Поле data отсутствует или имеет неверный формат %r",
            stock_rates,
        )
        return None

    if not all(isinstance(stock, dict) for stock in stock_rates):
        logger.error("Поле data содержит элементы неверного формата")
        return None

    logger.info(
        "Получены котировки для акций: %s",
        ", ".join(stocks),
    )

    return stock_rates


def _convert_stock_price(
    price: Any,
    source_currency: Any,
    target_currency: str,
    currency_rates: dict[str, Any],
    digit: int,
) -> float | None:
    """Переводит цену акции в целевую валюту."""
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        logger.warning("Некорректная цена акции: %r", price)
        return None

    if price < 0:
        logger.warning("Цена акции не может быть отрицательной: %s", price)
        return None

    if not isinstance(source_currency, str) or not source_currency.strip():
        source_currency = "USD"

    source_currency = source_currency.strip().upper()

    if source_currency == target_currency:
        return round(float(price), digit)

    rate = currency_rates.get(source_currency)

    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
        logger.warning(
            "Отсутствует корректный курс %s относительно %s: %r",
            source_currency,
            target_currency,
            rate,
        )
        return None

    return round(float(price) / rate, digit)


def _calculate_stock_rates(
    currency: str,
    stock_rates: list[Transaction],
    digit: int,
) -> list[Transaction] | None:
    """Формирует котировки акций в указанной валюте.

    Args:
        currency: Код целевой валюты.
        stock_rates: Список котировок акций.
        digit: Количество знаков после запятой.

    Returns:
        Список котировок или None, если корректных данных нет.
    """
    if not isinstance(currency, str):
        logger.error("Некорректный код валюты: %r", currency)
        return None

    if isinstance(digit, bool) or not isinstance(digit, int) or digit < 0:
        logger.error(
            "Некорректное количество знаков после запятой: %r",
            digit,
        )
        return None

    if not stock_rates:
        logger.error("Список котировок акций пуст")
        return None

    target_currency = currency.strip().upper()
    currency_rates = _get_currency_rates_from_api(target_currency)

    if not isinstance(currency_rates, dict):
        logger.error(
            "Не удалось получить курсы относительно валюты %s",
            target_currency,
        )
        return None

    stocks: list[Transaction] = []

    for stock in stock_rates:
        if not isinstance(stock, dict):
            logger.warning(
                "Котировка имеет неверный формат: %r",
                stock,
            )
            continue

        symbol = stock.get("symbol")
        converted_price = _convert_stock_price(
            price=stock.get("adj_close"),
            source_currency=stock.get("price_currency"),
            target_currency=target_currency,
            currency_rates=currency_rates,
            digit=digit,
        )

        if converted_price is None:
            logger.warning(
                "Котировка акции %s пропущена",
                symbol,
            )
            continue

        stock_name = stock.get("name")

        stocks.append(
            {
                "symbol": symbol,
                "stock_name": stock_name,
                "price_currency": target_currency,
                "adj_close": converted_price,
            }
        )

    if not stocks:
        logger.error("Не найдено корректных котировок акций")
        return None

    logger.info(
        "Рассчитано котировок в валюте %s: %d",
        target_currency,
        len(stocks),
    )

    return stocks


def get_stock_rates() -> list[Transaction] | None:
    """Возвращает список котировок акций."""
    settings_path = Path(__file__).resolve().parent.parent / "configs" / "user_settings.json"

    try:
        _, user_stocks, user_currency_quote = load_user_settings(settings_path)
    except (KeyError, TypeError, ValueError, OSError) as error:
        logger.exception(
            "Не удалось загрузить настройки из %s: %s",
            settings_path,
            error,
        )
        return None

    if not user_stocks:
        logger.error("Список пользовательских акций пуст")
        return None

    if not user_currency_quote:
        logger.error("Не указана базовая валюта")
        return None

    logger.info(
        "Запрашиваются котировки акций %s в валюте %s",
        user_stocks,
        user_currency_quote,
    )

    stock_rates = _get_stock_rates_from_api(user_stocks)

    if not stock_rates:
        logger.error("API вернул пустой список")
        return None

    converted_stocks = _calculate_stock_rates(user_currency_quote, stock_rates, 2)

    if not converted_stocks:
        logger.error("Не получено ни одной котировки акций")
        return None

    final_stock_rates: list[Transaction] = []

    for stock in converted_stocks:
        final_stock_rates.append({"stock": stock.get("symbol"), "price": stock.get("adj_close")})

    logger.info("Получены котировки акций: %s", len(final_stock_rates))
    return final_stock_rates
