"""Pick idempotency service (PR-04 / T-04, NFR-003 + EX-017).

Wraps the idempotent pick mutations (``scan`` / ``complete`` / ``cancel``):

- ``derive_key`` builds a deterministic server-side key from the operation,
  task and request payload when the caller omits the ``Idempotency-Key``
  header (EX-017 recovery / NFR-003).
- ``get_replay`` returns the stored successful response for a key, so a replay
  short-circuits and never re-executes the mutation.
- ``record`` persists the successful response keyed by (org, operation, key),
  upserting so concurrent retries converge on one stored outcome.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.pick_idempotency import PickIdempotencyKey

logger = logging.getLogger(__name__)

#: Idempotent pick operations covered by this layer.
OPERATION_SCAN = "scan"
OPERATION_COMPLETE = "complete"
OPERATION_CANCEL = "cancel"

_COMPLETED = "completed"


class PickIdempotencyService:
    """Record and replay idempotent pick mutations."""

    def __init__(self, db: Session):
        self.db = db

    # -- key derivation ------------------------------------------------------

    @staticmethod
    def derive_key(
        operation: str, pick_list_id: UUID, payload: str | None = None
    ) -> str:
        """Build a deterministic server-side idempotency key.

        For ``scan`` the key incorporates a hash of the request payload so
        that distinct scans are distinct keys while an identical retry maps to
        the same key. For ``complete``/``cancel`` the key is the operation plus
        the pick list id (a terminal, naturally idempotent transition).
        """
        base = f"{operation}:{pick_list_id}"
        if payload:
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
            base = f"{base}:{digest}"
        return base

    @staticmethod
    def request_hash(payload: str | None) -> str | None:
        """SHA-256 of the canonical request payload (audit/debug)."""
        if payload is None:
            return None
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # -- replay / record -----------------------------------------------------

    def get_replay(
        self, organization_id: UUID, operation: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        """Return the stored successful response for a key, if any."""
        row = (
            self.db.query(PickIdempotencyKey)
            .filter(
                PickIdempotencyKey.organization_id == organization_id,
                PickIdempotencyKey.operation == operation,
                PickIdempotencyKey.idempotency_key == idempotency_key,
                PickIdempotencyKey.status == _COMPLETED,
            )
            .first()
        )
        return row.response_json if row is not None else None

    def record(
        self,
        organization_id: UUID,
        operation: str,
        idempotency_key: str,
        pick_list_id: UUID,
        request_hash: str | None,
        response: dict[str, Any],
    ) -> PickIdempotencyKey:
        """Upsert the successful response for a key.

        An existing row (e.g. written by a concurrent retry) is updated in
        place rather than duplicated, keeping the (org, operation, key)
        unique constraint satisfied.
        """
        row = (
            self.db.query(PickIdempotencyKey)
            .filter(
                PickIdempotencyKey.organization_id == organization_id,
                PickIdempotencyKey.operation == operation,
                PickIdempotencyKey.idempotency_key == idempotency_key,
            )
            .first()
        )
        if row is None:
            row = PickIdempotencyKey(
                organization_id=organization_id,
                operation=operation,
                idempotency_key=idempotency_key,
                pick_list_id=pick_list_id,
                request_hash=request_hash,
                response_json=response,
                status=_COMPLETED,
            )
            self.db.add(row)
        else:
            row.response_json = response
            row.status = _COMPLETED
            if request_hash:
                row.request_hash = request_hash
        self.db.commit()
        return row


__all__ = [
    "PickIdempotencyService",
    "OPERATION_SCAN",
    "OPERATION_COMPLETE",
    "OPERATION_CANCEL",
]
