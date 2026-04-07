"""SQLAlchemy event listener for automated field-level audit logging.

Intercepts after_insert, after_update, and after_delete ORM events on models
marked with ``__audited__ = True`` and creates EntityAuditLog entries in the
same transaction.
"""

import enum
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import get_history

from app.core.audit_context import get_audit_context

logger = logging.getLogger(__name__)

GLOBAL_EXCLUDE_FIELDS: set[str] = {
    "password",
    "password_hash",
    "api_key",
    "secret_key",
    "token",
    "refresh_token",
}


def _get_excluded_fields(model_class) -> set[str]:
    model_exclude = getattr(model_class, "__audit_exclude__", set())
    return GLOBAL_EXCLUDE_FIELDS | set(model_exclude)


def _serialize_value(value) -> Any:
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
        return "[unserializable]"


def _get_model_values(instance, excluded_fields: set[str]) -> dict:
    values: dict[str, Any] = {}
    mapper = inspect(instance).mapper
    for attr in mapper.column_attrs:
        if attr.key in excluded_fields:
            continue
        raw = getattr(instance, attr.key)
        values[attr.key] = _serialize_value(raw)
    return values


def _get_record_id(target) -> uuid.UUID | None:
    mapper = inspect(target).mapper
    pk_cols = mapper.primary_key
    if pk_cols:
        pk_value = getattr(target, pk_cols[0].key)
        if isinstance(pk_value, uuid.UUID):
            return pk_value
        if pk_value is not None:
            return uuid.UUID(str(pk_value))
    return None


def _create_audit_entry(
    session, action: str, table_name: str, record_id, old_values, new_values, changed_fields
) -> None:
    from app.models.entity_audit_log import EntityAuditLog

    ctx = get_audit_context()
    audit_log = EntityAuditLog(
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
    )
    session.add(audit_log)


def _after_insert(mapper, connection, target):
    try:
        excluded = _get_excluded_fields(target.__class__)
        new_values = _get_model_values(target, excluded)
        record_id = _get_record_id(target)
        session = object_session(target)
        if session is None:
            return
        _create_audit_entry(session, "CREATE", target.__tablename__, record_id, None, new_values, None)
    except Exception:
        logger.exception("Audit listener error on INSERT for %s", getattr(target, "__tablename__", "?"))


def _after_update(mapper, connection, target):
    try:
        excluded = _get_excluded_fields(target.__class__)
        insp = inspect(target)
        old_values, new_values, changed_fields = {}, {}, []
        for attr in insp.mapper.column_attrs:
            if attr.key in excluded:
                continue
            history = get_history(target, attr.key)
            if history.has_changes():
                old_values[attr.key] = _serialize_value(history.deleted[0] if history.deleted else None)
                new_values[attr.key] = _serialize_value(history.added[0] if history.added else None)
                changed_fields.append(attr.key)
        if not changed_fields:
            return
        session = object_session(target)
        if session is None:
            return
        _create_audit_entry(session, "UPDATE", target.__tablename__, _get_record_id(target), old_values, new_values, changed_fields)
    except Exception:
        logger.exception("Audit listener error on UPDATE for %s", getattr(target, "__tablename__", "?"))


def _after_delete(mapper, connection, target):
    try:
        excluded = _get_excluded_fields(target.__class__)
        old_values = _get_model_values(target, excluded)
        session = object_session(target)
        if session is None:
            return
        _create_audit_entry(session, "DELETE", target.__tablename__, _get_record_id(target), old_values, None, None)
    except Exception:
        logger.exception("Audit listener error on DELETE for %s", getattr(target, "__tablename__", "?"))


def register_audit_listeners() -> None:
    """Attach audit event listeners to every model with ``__audited__ = True``."""
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
