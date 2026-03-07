from __future__ import annotations

import json
from urllib.error import URLError

import pytest
from pydantic import BaseModel

from app.infrastructure.providers.openai_provider import (
    LLMProviderError,
    OpenAIProvider,
    OpenAIProviderConfig,
)


class _OutputModel(BaseModel):
    value: str


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    def read(self) -> bytes:
        return self._body.encode("utf-8")


def _api() -> OpenAIProvider:
    return OpenAIProvider(
        OpenAIProviderConfig(
            provider="openai",
            api_key="test-key",
            model="gpt-test",
            base_url="https://example.test",
            timeout_sec=1.0,
            max_tokens=256,
            retry_count=1,
            retry_backoff_ms=1,
        )
    )


def test_openai_api_returns_content(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_body = {"choices": [{"message": {"content": '{"value":"ok"}'}}]}
    monkeypatch.setattr(
        "app.infrastructure.providers.openai_provider.urlopen",
        lambda request, timeout: _FakeResponse(json.dumps(provider_body)),
    )

    output = _api().complete(
        system_prompt="system",
        user_prompt="user",
        output_model=_OutputModel,
    )

    assert output == '{"value":"ok"}'


def test_openai_api_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.infrastructure.providers.openai_provider.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("timeout")),
    )
    monkeypatch.setattr("app.infrastructure.providers.openai_provider.time.sleep", lambda _: None)

    with pytest.raises(LLMProviderError):
        _api().complete(
            system_prompt="system",
            user_prompt="user",
            output_model=_OutputModel,
        )
