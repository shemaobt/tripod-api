import logging

from app.core.logging import setup_logging


def test_setup_logging_configures_root_logger():
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) > 0
    assert root.level == logging.INFO


def test_setup_logging_suppresses_noisy_loggers():
    setup_logging()
    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING
