from __future__ import annotations

import httpx
import pytest
from openai import APIError

from app.infrastructure.providers.openai_provider import (
    LLMProviderError,
    OpenAIProvider,
    OpenAIProviderConfig,
)
from app.shared.strict_model import StrictModel


class _OutputModel(StrictModel):
    value: str


class _FakeParsedResponse:
    def __init__(self, parsed: object) -> None:
        self.output_parsed = parsed
        self.incomplete_details = None
        self.output: list[object] = []
        self.usage = None
        self.model = "gpt-test"
        self.status = "completed"


class _FakeResponsesClient:
    def __init__(self, parsed: object | None = None, exc: Exception | None = None) -> None:
        self._parsed = parsed
        self._exc = exc

    def parse(self, **kwargs):
        del kwargs
        if self._exc is not None:
            raise self._exc
        return _FakeParsedResponse(self._parsed)


class _FakeOpenAIClient:
    def __init__(self, responses_client: _FakeResponsesClient) -> None:
        self.responses = responses_client


def _api() -> OpenAIProvider:
    provider = OpenAIProvider(
        OpenAIProviderConfig(
            api_key="test-key",
            model="gpt-test",
            base_url="https://example.test/v1",
            timeout_sec=1.0,
            max_tokens=256,
            retry_count=1,
            retry_backoff_ms=1,
        )
    )
    return provider


def test_openai_api_returns_content() -> None:
    provider = _api()
    provider.client = _FakeOpenAIClient(_FakeResponsesClient(parsed={"value": "ok"}))  # type: ignore[assignment]

    output = provider.complete(
        system_prompt="system",
        user_prompt="user",
        output_model=_OutputModel,
    )

    assert output == '{"value":"ok"}'


def test_openai_api_wraps_sdk_errors() -> None:
    provider = _api()
    provider.client = _FakeOpenAIClient(
        _FakeResponsesClient(
            exc=APIError(
                "boom",
                request=httpx.Request("POST", "https://example.test/v1/responses"),
                body=None,
            )
        )
    )  # type: ignore[assignment]

    with pytest.raises(LLMProviderError):
        provider.complete(
            system_prompt="system",
            user_prompt="user",
            output_model=_OutputModel,
        )
