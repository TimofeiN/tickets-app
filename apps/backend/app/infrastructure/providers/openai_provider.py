from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from app.application.ports.llm_provider import LLMConfigurationError, LLMProvider, LLMProviderError


@dataclass(frozen=True)
class OpenAIProviderConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    timeout_sec: float
    max_tokens: int
    retry_count: int
    retry_backoff_ms: int

    @classmethod
    def from_env(cls) -> "OpenAIProviderConfig":
        provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()

        if not provider:
            raise LLMConfigurationError("LLM_PROVIDER is missing")
        if provider not in {"openai"}:
            raise LLMConfigurationError(f"unsupported LLM_PROVIDER: {provider}")
        if not api_key:
            raise LLMConfigurationError("LLM_API_KEY is missing")
        if not model:
            raise LLMConfigurationError("LLM_MODEL is missing")

        timeout_sec = _float_env("LLM_TIMEOUT_SEC", default=5.0, min_value=0.5)
        max_tokens = _int_env("LLM_MAX_TOKENS", default=300, min_value=64, max_value=1500)
        retry_count = _int_env("LLM_RETRY_COUNT", default=1, min_value=0, max_value=3)
        retry_backoff_ms = _int_env(
            "LLM_RETRY_BACKOFF_MS",
            default=150,
            min_value=50,
            max_value=5000,
        )

        return cls(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com").rstrip("/"),
            timeout_sec=timeout_sec,
            max_tokens=max_tokens,
            retry_count=retry_count,
            retry_backoff_ms=retry_backoff_ms,
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, config: OpenAIProviderConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenAIProvider":
        return cls(config=OpenAIProviderConfig.from_env())

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
        body = json.dumps(request_body, ensure_ascii=True).encode("utf-8")
        request = Request(
            url=f"{self.config.base_url}/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        total_attempts = self.config.retry_count + 1
        for attempt in range(1, total_attempts + 1):
            try:
                with urlopen(request, timeout=self.config.timeout_sec) as response:
                    raw_response = response.read().decode("utf-8")
                return _extract_content(raw_response)
            except (HTTPError, URLError, TimeoutError) as exc:
                if attempt >= total_attempts:
                    raise LLMProviderError(str(exc)) from exc
                self._sleep_before_retry(attempt)

        raise LLMProviderError("unexpected provider error")

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


def _float_env(name: str, default: float, min_value: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(value, min_value)


def _int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min(value, max_value), min_value)
