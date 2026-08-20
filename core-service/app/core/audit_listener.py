"""SQLAlchemy event listener for automated field-level audit logging.

Intercepts after_insert, after_update, and after_delete ORM events on models
marked with ``__audited__ = True`` and creates AuditLog entries in the same
transaction.  Sensitive fields declared via ``__audit_exclude__`` (or present
in the global default list) are omitted entirely from snapshots.

All listener logic is wrapped in try/except so that audit failures never
propagate to the caller — business operations must not break because of
audit logging.
"""

import enum
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import event, insert, inspect
from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import get_history

from app.core.audit_context import get_audit_context

logger = logging.getLogger(__name__)

# ── Global sensitive-field exclusion list ────────────────────────────────────

GLOBAL_EXCLUDE_FIELDS: set[str] = {
    "password",
    "password_hash",
    "api_key",
    "secret_key",
    "token",
    "refresh_token",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_excluded_fields(model_class) -> set[str]:
    """Return the union of global and model-level excluded fields."""
    model_exclude = getattr(model_class, "__audit_exclude__", set())
    return GLOBAL_EXCLUDE_FIELDS | set(model_exclude)


def _serialize_value(value) -> Any:
    """Convert *value* to a JSON-safe representation."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, bytes):
        return "[binary]"
    try:
        return str(value)
    except Exception:
        logger.warning("Could not serialize value of type %s", type(value).__name__)
        return "[unserializable]"


def _get_model_values(instance, excluded_fields: set[str]) -> dict:
    """Return a dict of non-excluded column values, serialized for JSON."""
    values: dict[str, Any] = {}
    mapper = inspect(instance).mapper
    for attr in mapper.column_attrs:
        if attr.key in excluded_fields:
            continue
        raw = getattr(instance, attr.key)
        values[attr.key] = _serialize_value(raw)
    return values


def _get_record_id(target) -> uuid.UUID | None:
    """Extract the primary-key value from *target*."""
    mapper = inspect(target).mapper
    pk_cols = mapper.primary_key
    if pk_cols:
        pk_value = getattr(target, pk_cols[0].key)
        if isinstance(pk_value, uuid.UUID):
            return pk_value
        if pk_value is not None:
            return uuid.UUID(str(pk_value))
    return None


# ── Audit entry helper ───────────────────────────────────────────────────────

def _create_audit_entry(
    connection,
    action: str,
    table_name: str,
    record_id: uuid.UUID | None,
    old_values: dict | None,
    new_values: dict | None,
    changed_fields: list[str] | None,
) -> None:
    """Insert an AuditLog row directly on the connection.

    Writing via Core ``insert()`` (rather than ``session.add``) is the
    supported way to write audit rows from ``after_insert``/``after_update``/
    ``after_delete`` events, which fire during the flush/execution stage.
    """
    from app.models.audit_log import AuditLog

    ctx = get_audit_context()

    connection.execute(
        insert(AuditLog.__table__).values(
            id=uuid.uuid4(),
            user_id=uuid.UUID(ctx.user_id) if ctx.user_id else None,
            organization_id=uuid.UUID(ctx.organization_id) if ctx.organization_id else None,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
            created_at=datetime.now(UTC),
        )
    )


# ── Event handlers ───────────────────────────────────────────────────────────

def _after_insert(mapper, connection, target):  # noqa: ARG001
    """Handle after_insert — record a CREATE audit entry."""
    try:
        excluded = _get_excluded_fields(target.__class__)
        new_values = _get_model_values(target, excluded)
        record_id = _get_record_id(target)
        table_name = target.__tablename__

        session = object_session(target)
        if session is None:
            logger.warning("No session found for %s; skipping audit.", table_name)
            return

        _create_audit_entry(
            connection=connection,
            action="CREATE",
            table_name=table_name,
            record_id=record_id,
            old_values=None,
            new_values=new_values,
            changed_fields=None,
        )
    except Exception:
        logger.exception("Audit listener error on INSERT for %s", getattr(target, "__tablename__", "?"))


def _after_update(mapper, connection, target):  # noqa: ARG001
    """Handle after_update — record an UPDATE audit entry with field diffs."""
    try:
        excluded = _get_excluded_fields(target.__class__)
        insp = inspect(target)

        old_values: dict[str, Any] = {}
        new_values: dict[str, Any] = {}
        changed_fields: list[str] = []

        for attr in insp.mapper.column_attrs:
            if attr.key in excluded:
                continue
            history = get_history(target, attr.key)
            if history.has_changes():
                old_val = history.deleted[0] if history.deleted else None
                new_val = history.added[0] if history.added else None
                old_values[attr.key] = _serialize_value(old_val)
                new_values[attr.key] = _serialize_value(new_val)
                changed_fields.append(attr.key)

        if not changed_fields:
            return  # nothing actually changed

        record_id = _get_record_id(target)
        table_name = target.__tablename__

        session = object_session(target)
        if session is None:
            logger.warning("No session found for %s; skipping audit.", table_name)
            return

        _create_audit_entry(
            connection=connection,
            action="UPDATE",
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
        )
    except Exception:
        logger.exception("Audit listener error on UPDATE for %s", getattr(target, "__tablename__", "?"))


def _after_delete(mapper, connection, target):  # noqa: ARG001
    """Handle after_delete — record a DELETE audit entry."""
    try:
        excluded = _get_excluded_fields(target.__class__)
        old_values = _get_model_values(target, excluded)
        record_id = _get_record_id(target)
        table_name = target.__tablename__

        session = object_session(target)
        if session is None:
            logger.warning("No session found for %s; skipping audit.", table_name)
            return

        _create_audit_entry(
            connection=connection,
            action="DELETE",
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=None,
            changed_fields=None,
        )
    except Exception:
        logger.exception("Audit listener error on DELETE for %s", getattr(target, "__tablename__", "?"))


# ── Registration ─────────────────────────────────────────────────────────────

def register_audit_listeners() -> None:
    """Attach audit event listeners to every model with ``__audited__ = True``.

    Call this once at application startup (e.g. in FastAPI lifespan).
    """
    from app.database import Base

    count = 0
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__audited__", False):
            event.listen(cls, "after_insert", _after_insert)
            event.listen(cls, "after_update", _after_update)
            event.listen(cls, "after_delete", _after_delete)
            count += 1
            logger.debug("Registered audit listeners for %s", cls.__name__)

    logger.info("Audit listeners registered for %d model(s).", count)
