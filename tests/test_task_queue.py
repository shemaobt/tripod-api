import pytest


def test_task_queue_module_lazy_imports():
    from app.core import task_queue

    assert hasattr(task_queue, "get_task_app")
    assert hasattr(task_queue, "init_task_queue")
    assert hasattr(task_queue, "close_task_queue")


def test_generate_bcd_task_function_exists():
    from app.tasks.generate_bcd import generate_bcd_task

    assert callable(generate_bcd_task)


def test_generate_bcd_task_is_async():
    import asyncio
    from app.tasks.generate_bcd import generate_bcd_task

    assert asyncio.iscoroutinefunction(generate_bcd_task)


def test_get_task_app_requires_psycopg():
    try:
        import psycopg  # noqa: F401
        has_psycopg = True
    except ImportError:
        has_psycopg = False

    if not has_psycopg:
        with pytest.raises(ImportError):
            from app.core.task_queue import get_task_app
            get_task_app()
