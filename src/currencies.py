"""Функции обработки информации, полученной от внешних API для курсов валют."""

import logging
from pathlib import Path
from typing import Any

import requests

from src.api_responses import get_response
from src.fields import load_user_settings

Transaction = dict[str, Any]

RATES_CURRENCY_API = "https://open.er-api.com/v6/latest/"


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("currencies")
logger.setLevel(logging.DEBUG)
logger.propagate = False

file_handler = logging.FileHandler(
    LOG_DIR / "currencies.log",
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)

file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def _get_currency_rates_from_api(
    currency_quote: str,
) -> dict[str, Any] | None:
    """Получает словарь курсов валют от API.

    Args:
        currency_quote - базовая валюта в запросе

    Returns:
        Список котировок валют по отношению к базовой валюте

    """

    url = RATES_CURRENCY_API + currency_quote

    try:
        data_json = get_response(url, {})
    except requests.RequestException as error:
        logger.exception(
            "Ошибка запроса курсов валют по адресу %s: %s",
            url,
            error,
        )
        return None

    if not data_json:
        logger.error("API не вернул данные о курсах валют")
        return None

    if data_json.get("result") == "error":
        logger.error(
            "API вернул ошибку: %s",
            data_json.get("error-type", "причина не указана"),
        )
        return None

    currency_rates = data_json.get("rates")

    if not isinstance(currency_rates, dict):
        logger.error("Поле rates отсутствует или имеет неверный формат")
        return None

    return currency_rates


def _calculate_currency_quote(currency: str, currency_rates: dict[str, Any], digit: int) -> Transaction | None:
    """Рассчитывает обратный курс одной валюты.

    Args:
        currency - код валюты для которой будет рассчитан обратный курс валюты
        currency_rates - список курсов валют

    Returns:
          Обратный курс валюты, округленный до digit знаков после запятой
    """
    if digit < 0:
        logger.warning(
            "Получено недопуное значение для округления %s: %s",
            currency,
            digit,
        )
        return None

    rate = currency_rates.get(currency)

    if rate is None:
        logger.warning(
            "Курс валюты %s отсутствует в ответе API",
            currency,
        )
        return None

    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        logger.warning(
            "Курс валюты %s имеет неверный формат: %r",
            currency,
            rate,
        )
        return None

    if rate <= 0:
        logger.warning(
            "Получен недопустимый курс валюты %s: %s",
            currency,
            rate,
        )
        return None

    return {"currency": currency, "rate": round(1 / rate, digit)}


def _build_currency_quotes(
    user_currencies: list[str], currency_rates: dict[str, Any], digit: int
) -> list[Transaction]:
    """Формирует список рассчитанных курсов.

    Args:
        user_currencies - список валют, которые определы для пользователя
        currency_rates - список обратных курсов ввалют
        digit - точность округления

    Returns:
          Список курсов валют, определенных для пользователя
    """
    currency_quotes: list[Transaction] = []

    for currency in user_currencies:
        currency_quote = _calculate_currency_quote(
            currency,
            currency_rates,
            digit,
        )

        if currency_quote is not None:
            currency_quotes.append(currency_quote)

    return currency_quotes


def get_currency_rates() -> list[Transaction] | None:
    """Возвращает список курсов валют."""
    settings_path = Path(__file__).resolve().parent.parent / "configs" / "user_settings.json"

    try:
        user_currencies, _, user_currency_quote = load_user_settings(settings_path)
    except (KeyError, TypeError, ValueError, OSError) as error:
        logger.exception(
            "Не удалось загрузить настройки из %s: %s",
            settings_path,
            error,
        )
        return None

    if not user_currencies:
        logger.error("Список пользовательских валют пуст")
        return None

    if not user_currency_quote:
        logger.error("Не указана базовая валюта")
        return None

    logger.info(
        "Запрашиваются курсы %s относительно %s",
        user_currencies,
        user_currency_quote,
    )

    currency_rates = _get_currency_rates_from_api(user_currency_quote)

    if currency_rates is None:
        return None

    currency_quotes = _build_currency_quotes(
        user_currencies,
        currency_rates,
        2,
    )

    if not currency_quotes:
        logger.error("Не получено ни одного корректного курса")
        return None

    logger.info("Получены курсы валют: %s", currency_quotes)
    return currency_quotes
