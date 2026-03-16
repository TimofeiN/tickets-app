class AppError(Exception):
    error_code = "app_error"
    status_code = 400
    public_message = "Application error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class DomainInvariantError(AppError):
    error_code = "domain_invariant"
    status_code = 500
    public_message = "Internal service error"


class LLMError(AppError):
    error_code = "llm_error"
    status_code = 503
    public_message = "AI service is temporarily unavailable"


class LLMConfigurationError(LLMError):
    error_code = "llm_configuration_error"


class LLMProviderError(LLMError):
    error_code = "llm_provider_error"


class LLMRankingError(LLMError):
    error_code = "llm_ranking_error"


class LLMResponseValidationError(LLMRankingError):
    error_code = "llm_response_validation_error"


class ProviderUnavailableError(AppError):
    error_code = "provider_unavailable"
    status_code = 503
    public_message = "Flight provider is temporarily unavailable"


class DataAccessError(AppError):
    error_code = "data_access_error"
    status_code = 503
    public_message = "Data service is temporarily unavailable"
