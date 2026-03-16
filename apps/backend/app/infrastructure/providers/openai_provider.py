from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
from pydantic import BaseModel, ValidationError

from app.application.ports.llm_provider import (
    LLMConfigurationError,
    LLMProvider,
    LLMProviderError,
)
from app.core.settings import settings

OPENAI_MODEL = "gpt-4.1-mini"
TRIP_SUMMARY_PROMPT_ID = "pmpt_69b3532d1fd8819687dc37a3e611c07e061da3bdb50845a0"
TRIP_SUMMARY_PROMPT_VERSION = "4"
TRIP_SUMMARY_MAX_OUTPUT_TOKENS = 5000
MODEL_PRICING_USD_PER_1M_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-5-nano": (0.05, 0.40),
}
logger = logging.getLogger(__name__)


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
    def from_settings(cls) -> OpenAIProviderConfig:
        api_key = settings.openai_api_key

        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is missing")

        return cls(
            api_key=api_key,
            model=OPENAI_MODEL,
            base_url=settings.openai_base_url,
            timeout_sec=settings.openai_timeout_sec,
            max_tokens=1000,
            retry_count=settings.openai_retry_count,
            retry_backoff_ms=settings.openai_retry_backoff_ms,
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, config: OpenAIProviderConfig) -> None:
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_sec,
            max_retries=config.retry_count,
        )

    @classmethod
    def from_settings(cls) -> OpenAIProvider:
        return cls(config=OpenAIProviderConfig.from_settings())

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
    ) -> str:
        prompt_chars = len(system_prompt) + len(user_prompt)
        logger.info(
            "openai_responses_parse_request model=%s schema=%s prompt_chars=%s",
            self.config.model,
            output_model.__name__,
            prompt_chars,
        )
        try:
            response = self.client.responses.parse(
                model=self.config.model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}],
                    },
                ],
                text_format=output_model,
                max_output_tokens=self.config.max_tokens,
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise LLMProviderError(str(exc)) from exc

        self._log_response_metadata(
            operation="responses.parse",
            response=response,
            prompt_chars=prompt_chars,
        )
        if response.incomplete_details is not None:
            raise LLMProviderError(
                f"provider response incomplete: {response.incomplete_details.reason}"
            )

        parsed = response.output_parsed
        if parsed is None:
            output_types = ",".join(item.type for item in response.output)
            raise LLMProviderError(
                f"provider response has unexpected shape: output_types={output_types or 'none'}"
            )

        try:
            validated = output_model.model_validate(parsed)
        except ValidationError as exc:
            raise LLMProviderError("provider response has unexpected shape") from exc

        return validated.model_dump_json()

    def render_trip_summary(
        self,
        *,
        city: str,
        num_days: int,
        themes: str,
    ) -> str:
        prompt_chars = len(city) + len(str(num_days)) + len(themes)
        logger.info(
            (
                "openai_responses_prompt_request prompt_id=%s version=%s city=%s "
                "num_days=%s themes=%s prompt_chars=%s max_output_tokens=%s"
            ),
            TRIP_SUMMARY_PROMPT_ID,
            TRIP_SUMMARY_PROMPT_VERSION,
            city,
            num_days,
            themes,
            prompt_chars,
            TRIP_SUMMARY_MAX_OUTPUT_TOKENS,
        )
        try:
            response = self.client.responses.create(
                prompt={
                    "id": TRIP_SUMMARY_PROMPT_ID,
                    "version": TRIP_SUMMARY_PROMPT_VERSION,
                    "variables": {
                        "num_days": str(num_days),
                        "city": city,
                        "themes": themes,
                    },
                },
                max_output_tokens=TRIP_SUMMARY_MAX_OUTPUT_TOKENS,
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise LLMProviderError(str(exc)) from exc

        self._log_response_metadata(
            operation="responses.create",
            response=response,
            prompt_chars=prompt_chars,
        )
        if response.incomplete_details is not None:
            raise LLMProviderError(
                f"provider response incomplete: {response.incomplete_details.reason}"
            )

        content = response.output_text.strip()
        if not content:
            raise LLMProviderError("provider response content is empty")
        return content

    def _log_response_metadata(
        self,
        *,
        operation: str,
        response: object,
        prompt_chars: int,
    ) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            logger.info(
                "openai_response_meta operation=%s model=%s prompt_chars=%s usage=missing",
                operation,
                getattr(response, "model", "unknown"),
                prompt_chars,
            )
            return

        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens) or 0
        input_details = getattr(usage, "input_tokens_details", None)
        output_details = getattr(usage, "output_tokens_details", None)
        cached_input_tokens = getattr(input_details, "cached_tokens", 0) or 0
        reasoning_tokens = getattr(output_details, "reasoning_tokens", 0) or 0
        model_name = str(getattr(response, "model", "unknown") or "unknown")
        estimated_cost_usd = self._estimate_cost_usd(
            model_name=model_name,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
        )
        finish_reason = self._finish_reason(response)

        logger.info(
            (
                "openai_response_meta operation=%s model=%s "
                "status=%s finish_reason=%s prompt_chars=%s "
                "input_tokens=%s cached_input_tokens=%s output_tokens=%s "
                "reasoning_tokens=%s total_tokens=%s estimated_cost_usd=%s"
            ),
            operation,
            model_name,
            getattr(response, "status", "unknown"),
            finish_reason,
            prompt_chars,
            input_tokens,
            cached_input_tokens,
            output_tokens,
            reasoning_tokens,
            total_tokens,
            (f"{estimated_cost_usd:.6f}" if estimated_cost_usd is not None else "unknown"),
        )

    def _estimate_cost_usd(
        self,
        *,
        model_name: str,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        pricing = self._pricing_for_model(model_name)
        if pricing is None:
            return None

        input_price_per_1m, output_price_per_1m = pricing
        billable_input_tokens = max(0, input_tokens - cached_input_tokens)
        return (
            billable_input_tokens * input_price_per_1m + output_tokens * output_price_per_1m
        ) / 1_000_000

    def _pricing_for_model(self, model_name: str) -> tuple[float, float] | None:
        normalized = model_name.lower()
        for prefix, pricing in MODEL_PRICING_USD_PER_1M_TOKENS.items():
            if normalized.startswith(prefix):
                return pricing
        return None

    def _finish_reason(self, response: object) -> str:
        incomplete_details = getattr(response, "incomplete_details", None)
        if incomplete_details is not None:
            reason = getattr(incomplete_details, "reason", None)
            if reason:
                return str(reason)

        output = getattr(response, "output", None)
        if isinstance(output, list):
            for item in output:
                if getattr(item, "type", None) == "message":
                    status = getattr(item, "status", None)
                    if status:
                        return str(status)

        status = getattr(response, "status", None)
        if status:
            return str(status)
        return "unknown"
