class AppError(Exception):
    pass


class ConfigError(AppError):
    pass


class InputError(AppError):
    pass


class LLMError(AppError):
    pass
