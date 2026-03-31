"""
Celery tasks module for async operations.
"""
from app.tasks.qr_generation import generate_qr_block_task

__all__ = ["generate_qr_block_task"]
