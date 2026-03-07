class AppError(Exception):
    pass


class DomainInvariantError(AppError):
    pass


class LLMConfigurationError(AppError):
    pass


class LLMProviderError(AppError):
    pass


class LLMRankingError(AppError):
    pass


class LLMResponseValidationError(LLMRankingError):
    pass


class ProviderUnavailableError(AppError):
    pass


class DataAccessError(AppError):
    pass
