from app.core.exceptions import AppError, NotFoundError, ValidationError


def test_app_error_fields():
    error = NotFoundError("missing project")
    assert error.status_code == 404
    assert error.code == "not_found"
    assert error.message == "missing project"


def test_validation_error_status():
    error = ValidationError("invalid payload")
    assert error.status_code == 422
    assert error.code == "validation_error"


def test_app_error_custom():
    error = AppError("busy", status_code=503, code="gpu_busy")
    assert error.status_code == 503
    assert error.code == "gpu_busy"
