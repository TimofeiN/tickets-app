from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Coroutine
from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from app.application.ports.llm_provider import (
    LLMConfigurationError,
    LLMProvider,
    LLMProviderError,
)
from app.core.settings import settings


@dataclass(frozen=True)
class OpenAIProviderConfig:
    api_key: str
    model: str
    base_url: str
    timeout_sec: float
    max_tokens: int
    retry_count: int
    retry_backoff_ms: int

    @classmethod
    def from_settings(cls) -> "OpenAIProviderConfig":
        api_key = settings.openai_api_key
        model = settings.openai_model

        if not api_key:
            raise LLMConfigurationError("LLM_API_KEY is missing")
        if not model:
            raise LLMConfigurationError("LLM_MODEL is missing")

        return cls(
            api_key=api_key,
            model=model,
            base_url=settings.openai_base_url,
            timeout_sec=settings.openai_timeout_sec,
            max_tokens=settings.openai_max_tokens,
            retry_count=settings.openai_retry_count,
            retry_backoff_ms=settings.openai_retry_backoff_ms,
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, config: OpenAIProviderConfig) -> None:
        self.config = config

    @classmethod
    def from_settings(cls) -> "OpenAIProvider":
        return cls(config=OpenAIProviderConfig.from_settings())

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
    ) -> str:
        request_body = {
            "model": self.config.model,
            "temperature": 0.2,
            "max_tokens": self.config.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "provider_response",
                    "strict": True,
                    "schema": output_model.model_json_schema(),
                },
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        return self._run_async(
            self._complete_async(request_body=request_body),
        )

    async def _complete_async(self, *, request_body: dict[str, object]) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        total_attempts = self.config.retry_count + 1
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_sec,
            headers=headers,
        ) as client:
            for attempt in range(1, total_attempts + 1):
                try:
                    response = await client.post("/v1/chat/completions", json=request_body)
                    response.raise_for_status()
                    return _extract_content(response.text)
                except httpx.HTTPStatusError as exc:
                    if attempt >= total_attempts:
                        raise LLMProviderError(str(exc)) from exc
                    self._sleep_before_retry(attempt)
                except (httpx.TimeoutException, httpx.RequestError) as exc:
                    if attempt >= total_attempts:
                        raise LLMProviderError(str(exc)) from exc
                    self._sleep_before_retry(attempt)

        raise LLMProviderError("unexpected provider error")

    def _run_async(self, coroutine: Coroutine[object, object, str]) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise LLMProviderError("cannot run async LLM provider inside active event loop")

    def _sleep_before_retry(self, attempt: int) -> None:
        delay_sec = (self.config.retry_backoff_ms / 1000.0) * attempt
        time.sleep(delay_sec)


def _extract_content(raw_response: str) -> str:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("provider returned malformed json") from exc

    try:
        content = parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("provider response has unexpected shape") from exc

    if not isinstance(content, str):
        raise LLMProviderError("provider response content is not text")
    return content
