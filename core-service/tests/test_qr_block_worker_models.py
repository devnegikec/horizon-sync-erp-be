"""Celery worker ORM-registration regression tests."""

from sqlalchemy.orm import configure_mappers


def test_qr_block_worker_registers_all_related_models():
    import app.qr_block_tasks  # noqa: F401

    configure_mappers()
