"""
@Author NIUNIU_AI
@Date 2026/05/23 16:00
@Version 1.0
@Description 应用统一异常定义
"""


class AppError(Exception):
    """业务异常基类"""

    def __init__(self, message: str, status_code: int = 400, code: str = "app_error") -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """资源不存在"""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404, code="not_found")


class ValidationError(AppError):
    """参数或业务校验失败"""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422, code="validation_error")


class ServiceUnavailableError(AppError):
    """外部服务不可用"""

    def __init__(self, message: str = "Service unavailable") -> None:
        super().__init__(message, status_code=503, code="service_unavailable")
