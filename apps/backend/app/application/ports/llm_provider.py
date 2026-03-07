from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.core import errors as core_errors

LLMConfigurationError = core_errors.LLMConfigurationError
LLMProviderError = core_errors.LLMProviderError


class LLMProvider(Protocol):
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
    ) -> str: ...
