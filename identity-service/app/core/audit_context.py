"""Audit context propagation via contextvars.

Provides a thread-safe ContextVar to carry user/request metadata into
SQLAlchemy event listeners that run outside the normal FastAPI dependency
injection scope.
"""

import contextvars
from dataclasses import dataclass


@dataclass
class AuditContext:
    """Request-scoped audit metadata populated by AuditContextMiddleware."""

    user_id: str | None = None
    organization_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


_audit_context_var: contextvars.ContextVar[AuditContext] = contextvars.ContextVar(
    "audit_context", default=AuditContext()
)


def get_audit_context() -> AuditContext:
    """Return the current request's AuditContext."""
    return _audit_context_var.get()


def set_audit_context(ctx: AuditContext) -> contextvars.Token:
    """Store *ctx* in the ContextVar and return a reset token."""
    return _audit_context_var.set(ctx)
