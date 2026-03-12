from __future__ import annotations

import httpx
import pytest

from app.infrastructure.providers.openai_provider import (
    LLMProviderError,
    OpenAIProvider,
    OpenAIProviderConfig,
)
from app.shared.strict_model import StrictModel


class _OutputModel(StrictModel):
    value: str


class _FakeAsyncClient:
    def __init__(self, responses):  # noqa: ANN001
        self._responses = list(responses)

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    async def post(self, path: str, json: dict[str, object]):  # noqa: ANN001, A002
        del path, json
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _api() -> OpenAIProvider:
    return OpenAIProvider(
        OpenAIProviderConfig(
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
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    response = httpx.Response(200, request=request, json=provider_body)
    monkeypatch.setattr(
        "app.infrastructure.providers.openai_provider.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient([response]),  # noqa: ARG005
    )

    output = _api().complete(
        system_prompt="system",
        user_prompt="user",
        output_model=_OutputModel,
    )

    assert output == '{"value":"ok"}'


def test_openai_api_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    monkeypatch.setattr(
        "app.infrastructure.providers.openai_provider.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(  # noqa: ARG005
            [
                httpx.ConnectError("timeout", request=request),
                httpx.ConnectError("timeout", request=request),
            ]
        ),
    )
    monkeypatch.setattr("app.infrastructure.providers.openai_provider.time.sleep", lambda _: None)

    with pytest.raises(LLMProviderError):
        _api().complete(
            system_prompt="system",
            user_prompt="user",
            output_model=_OutputModel,
        )
