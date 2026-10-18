"""Тесты общих функций обращения к внешним API."""

from unittest.mock import Mock

import pytest
import requests

from src import api_responses


def test_get_api_key_returns_environment_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """API-ключ возвращается из указанной переменной окружения."""
    monkeypatch.setenv("TEST_API_KEY", "secret-key")

    assert api_responses.get_api_key("TEST_API_KEY") == "secret-key"


@pytest.mark.parametrize("value", [None, ""])
def test_get_api_key_returns_none_for_missing_or_empty_value(
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
) -> None:
    """Отсутствующий и пустой ключ считаются некорректными."""
    if value is None:
        monkeypatch.delenv("TEST_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TEST_API_KEY", value)

    assert api_responses.get_api_key("TEST_API_KEY") is None


def test_get_response_returns_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Корректный JSON-объект возвращается без изменений."""
    response = Mock()
    response.json.return_value = {"result": "success", "value": 42}
    request = Mock(return_value=response)
    monkeypatch.setattr(api_responses.requests, "get", request)

    result = api_responses.get_response(
        "https://example.test/data",
        {"symbol": "AAPL", "amount": 10.5},
    )

    assert result == {"result": "success", "value": 42}
    request.assert_called_once_with(
        "https://example.test/data",
        params={"symbol": "AAPL", "amount": 10.5},
        timeout=api_responses.API_TIMEOUT_SECONDS,
    )


def test_get_response_returns_none_for_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ответ, который нельзя декодировать как JSON, отклоняется."""
    response = Mock()
    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "invalid JSON",
        "not-json",
        0,
    )
    monkeypatch.setattr(api_responses.requests, "get", Mock(return_value=response))

    assert api_responses.get_response("https://example.test/data", {}) is None


@pytest.mark.parametrize("payload", [[], [1, 2], "text", 10, None])
def test_get_response_returns_none_when_json_root_is_not_object(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    """Корневым элементом ответа должен быть JSON-объект."""
    response = Mock()
    response.json.return_value = payload
    monkeypatch.setattr(api_responses.requests, "get", Mock(return_value=response))

    assert api_responses.get_response("https://example.test/data", {}) is None


def test_get_response_propagates_request_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сетевые исключения должен обрабатывать вызывающий модуль."""
    monkeypatch.setattr(
        api_responses.requests,
        "get",
        Mock(side_effect=requests.Timeout("request timed out")),
    )

    with pytest.raises(requests.Timeout, match="request timed out"):
        api_responses.get_response("https://example.test/data", {})
