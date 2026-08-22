"""Application lifecycle regression tests."""

import asyncio

import pytest

from app import main
from app.core import audit_listener


@pytest.mark.asyncio
async def test_lifespan_starts_and_cancels_bin_reservation_cleanup(monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def cleanup_loop() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(main, "ensure_single_master_organization", None)
    monkeypatch.setattr(main, "_bin_reservation_cleanup_loop", cleanup_loop)
    monkeypatch.setattr(audit_listener, "register_audit_listeners", lambda: None)

    async with main.lifespan(main.app):
        await asyncio.wait_for(started.wait(), timeout=1)

    assert cancelled.is_set()
