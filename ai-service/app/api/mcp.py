"""MCP (Model Context Protocol) endpoints for AI Service.

Exposes the WMS MCP server over two transports:
  1. SSE (Server-Sent Events) — for remote/cloud AI assistants
  2. stdio — for local desktop apps like Claude Desktop

Protocol flow over SSE:
  1. Client opens GET /mcp/sse → server sends an endpoint event with a session URL
  2. Client POSTs JSON-RPC messages to that session URL
  3. Server processes via MCP SDK and streams responses back through SSE
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.services.mcp_server import MCP_SDK_AVAILABLE, mcp_server

logger = logging.getLogger(__name__)
router = APIRouter()

# ── SSE Transport (only available when MCP SDK is installed) ───────────
if MCP_SDK_AVAILABLE:
    try:
        from mcp.server.sse import SseServerTransport

        mcp_transport = SseServerTransport("/mcp/messages/")
    except ImportError:
        logger.warning("MCP SSE transport not available in this SDK version")
        mcp_transport = None
else:
    mcp_transport = None


@router.get("/sse")
async def mcp_sse_endpoint(request: Request):
    """Server-Sent Events endpoint for MCP clients.

    This is the entrypoint for remote AI assistants (cloud-hosted Claude,
    custom agents) to connect to the WMS MCP server over HTTP.
    """
    if not MCP_SDK_AVAILABLE or mcp_server is None:
        return PlainTextResponse(
            "MCP SDK not installed. Run: pip install mcp>=1.0",
            status_code=503,
        )

    if mcp_transport is None:
        return PlainTextResponse(
            "MCP SSE transport unavailable. Check SDK version.",
            status_code=503,
        )

    # Bridge ASGI scope/receive/send to MCP SSE transport
    async with mcp_transport.connect_sse(
        request.scope, request.receive, request.send
    ) as (read_stream, write_stream):
        init_options = (
            mcp_server.create_initialization_options()
            if hasattr(mcp_server, "create_initialization_options")
            else None
        )
        await mcp_server.run(read_stream, write_stream, init_options)


@router.post("/messages/")
async def mcp_messages_endpoint(request: Request):
    """Receive JSON-RPC messages from MCP clients via POST.

    The SSE transport routes inbound messages here; the server processes them
    and sends responses back through the SSE stream.
    """
    if not MCP_SDK_AVAILABLE or mcp_transport is None:
        return PlainTextResponse("MCP not available", status_code=503)

    body = await request.body()
    # The transport injects the message into the read stream.
    # Exact method name depends on MCP SDK version; adjust if needed.
    if hasattr(mcp_transport, "handle_post_message"):
        await mcp_transport.handle_post_message(body)
    else:
        logger.warning("MCP transport.handle_post_message not found — "
                       "SDK API may have changed. Check MCP SDK docs.")
    return PlainTextResponse("ok")
