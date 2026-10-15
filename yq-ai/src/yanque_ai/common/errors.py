"""统一异常。"""

from __future__ import annotations


class AIServiceError(Exception):
    """AI 服务对外抛出的统一异常。"""

    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ConfigMissingError(AIServiceError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFIG_MISSING", message, status_code=500)


class UpstreamTimeoutError(AIServiceError):
    def __init__(self, message: str = "模型调用超时，请稍后重试") -> None:
        super().__init__("UPSTREAM_TIMEOUT", message, status_code=504)


class UpstreamRateLimitError(AIServiceError):
    def __init__(self, message: str = "模型调用过于频繁，请稍后重试") -> None:
        super().__init__("UPSTREAM_RATE_LIMITED", message, status_code=429)


class UpstreamAuthError(AIServiceError):
    def __init__(self, message: str = "模型 API Key 无效或无权限") -> None:
        super().__init__("UPSTREAM_UNAUTHORIZED", message, status_code=502)


class UpstreamCallError(AIServiceError):
    def __init__(self, message: str) -> None:
        super().__init__("UPSTREAM_ERROR", message, status_code=502)


class PromptLoadError(AIServiceError):
    def __init__(self, message: str) -> None:
        super().__init__("PROMPT_LOAD_FAILED", message, status_code=502)
