""" "Получение информации через внешний API."""

import logging
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

API_TIMEOUT_SECONDS = 10

load_dotenv()

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("api_responses")
logger.setLevel(logging.DEBUG)
logger.propagate = False

file_handler = logging.FileHandler(
    LOG_DIR / "api_responses.log",
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)

file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def get_api_key(code_key: str) -> str | None:
    """Функция возвращает API ключ по параметру ключа `code_key`"""

    api_key = os.getenv(code_key)

    if not api_key:
        logger.error("Ключ %s отсутствует", code_key)
        return None

    return api_key


def get_response(url: str, params: dict[str, str | float]) -> Any | None:
    """Функция возвращает ответ API в виде JSON.

    Args:
        url: URL метода API.
        params: Параметры запроса.

    Returns:
        Ответ API в виде JSON.

    Raises:
        RuntimeError: Если API вернул ошибку или данные
            неожиданного формата.
        requests.HTTPError: Если API вернул ошибочный
            HTTP-статус без описания в JSON.
    """

    response = requests.get(
        url,
        params=params,
        timeout=API_TIMEOUT_SECONDS,
    )

    try:
        response_data: Any = response.json()
    except requests.exceptions.JSONDecodeError as error:
        logger.error("API вернул ответ не в формате JSON для %s: %s", url, error)
        return None

    if not isinstance(response_data, dict):
        logger.error("API вернул ответ в неожиданном формате для %s", url)
        return None

    return response_data
