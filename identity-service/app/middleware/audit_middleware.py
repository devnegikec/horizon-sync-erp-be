"""Middleware that populates the AuditContext ContextVar for every request."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.audit_context import AuditContext, _audit_context_var, set_audit_context
from app.core.security import decode_token

logger = logging.getLogger(__name__)


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Extract user/request metadata and store it in the audit ContextVar."""

    async def dispatch(self, request: Request, call_next) -> Response:
        user_id: str | None = None
        organization_id: str | None = None
        ip_address: str | None = None
        user_agent: str | None = None

        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                raw_token = auth_header[7:]
                payload = decode_token(raw_token)
                if payload:
                    user_id = payload.get("sub")
                    organization_id = payload.get("organization_id")
        except Exception:
            logger.debug("AuditContextMiddleware: failed to decode JWT", exc_info=True)

        try:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host
        except Exception:
            pass

        user_agent = request.headers.get("user-agent")

        ctx = AuditContext(
            user_id=user_id,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        token = set_audit_context(ctx)
        try:
            response: Response = await call_next(request)
            return response
        finally:
            _audit_context_var.reset(token)
