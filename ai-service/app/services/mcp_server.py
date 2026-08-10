"""MCP Server implementation for WMS read-only tools.

Uses the official Anthropic MCP Python SDK to expose six WMS query tools
that AI assistants (Claude, Cursor, etc.) can discover and invoke.

SDK API pattern (mcp>=1.0):
  - @server.list_tools()  → returns tool catalog for discovery
  - @server.call_tool()   → handles tool invocation by name + arguments

Phase 1 V1 tools (all read-only):
  - wms.stock.get
  - wms.asn.list
  - wms.asn.get
  - wms.user.list
  - wms.location.list
  - wms.putaway.get
"""

import json
import logging

import httpx

from app.clients.core_service import core_client
from app.config import settings

logger = logging.getLogger(__name__)

# ── MCP SDK imports ──────────────────────────────────────────────────────
try:
    from mcp.server import Server
    import mcp.types as types

    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    Server = None
    types = None
    logger.warning("MCP SDK not installed. Install: pip install mcp>=1.0")

# ── Build server ─────────────────────────────────────────────────────────
if MCP_SDK_AVAILABLE:
    mcp_server = Server(settings.MCP_SERVER_NAME)
else:
    mcp_server = None


# ── Tool schemas ───────────────────────────────────────────────────────
_TOOL_SCHEMAS = [
    types.Tool(
        name="wms.stock.get",
        description="Get current stock levels for a warehouse, optionally filtered by item or bin.",
        inputSchema={
            "type": "object",
            "properties": {
                "warehouse_id": {"type": "string", "format": "uuid"},
                "item_id": {"type": "string", "format": "uuid"},
                "bin_id": {"type": "string", "format": "uuid"},
            },
            "required": ["warehouse_id"],
        },
    ),
    types.Tool(
        name="wms.asn.list",
        description="List ASN orders for a warehouse, optionally filtered by status.",
        inputSchema={
            "type": "object",
            "properties": {
                "warehouse_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": ["draft", "confirmed", "partially_delivered", "delivered", "closed", "cancelled"]},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["warehouse_id"],
        },
    ),
    types.Tool(
        name="wms.asn.get",
        description="Get a single ASN order by ID with all line items.",
        inputSchema={
            "type": "object",
            "properties": {
                "asn_order_id": {"type": "string", "format": "uuid"},
            },
            "required": ["asn_order_id"],
        },
    ),
    types.Tool(
        name="wms.user.list",
        description="List users assigned to a warehouse, optionally filtered by role.",
        inputSchema={
            "type": "object",
            "properties": {
                "warehouse_id": {"type": "string", "format": "uuid"},
                "role": {"type": "string", "enum": ["supervisor", "manager", "operator", "coordinator"]},
            },
            "required": ["warehouse_id"],
        },
    ),
    types.Tool(
        name="wms.location.list",
        description="List warehouse locations (zones, aisles, bays, bins).",
        inputSchema={
            "type": "object",
            "properties": {
                "warehouse_id": {"type": "string", "format": "uuid"},
                "type": {"type": "string", "enum": ["zone", "aisle", "bay", "level", "bin"]},
            },
            "required": ["warehouse_id"],
        },
    ),
    types.Tool(
        name="wms.putaway.get",
        description="Get a put-away task by ID with items and target bin details.",
        inputSchema={
            "type": "object",
            "properties": {
                "put_away_list_id": {"type": "string", "format": "uuid"},
            },
            "required": ["put_away_list_id"],
        },
    ),
]


# ── Helper ───────────────────────────────────────────────────────────────
def _text_content(data: dict) -> list:
    """Serialize a dict to JSON wrapped in MCP TextContent."""
    return [types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _error_content(message: str) -> list:
    """Return an MCP error response."""
    return [types.TextContent(type="text", text=json.dumps({"error": message}))]


# ── Tool dispatcher ────────────────────────────────────────────────────────
async def _dispatch_tool(name: str, arguments: dict) -> list:
    """Route tool calls to the appropriate core_client method."""
    try:
        if name == "wms.stock.get":
            warehouse_id = arguments.get("warehouse_id")
            if not warehouse_id:
                return _error_content("warehouse_id is required")
            result = await core_client.get_stock(
                warehouse_id=str(warehouse_id),
                item_id=arguments.get("item_id"),
                bin_id=arguments.get("bin_id"),
            )
            return _text_content(result)

        elif name == "wms.asn.list":
            warehouse_id = arguments.get("warehouse_id")
            if not warehouse_id:
                return _error_content("warehouse_id is required")
            result = await core_client.get_asn_orders(
                warehouse_id=str(warehouse_id),
                status=arguments.get("status"),
                limit=arguments.get("limit", 20),
            )
            return _text_content(result)

        elif name == "wms.asn.get":
            asn_order_id = arguments.get("asn_order_id")
            if not asn_order_id:
                return _error_content("asn_order_id is required")
            result = await core_client.get_asn_order(str(asn_order_id))
            return _text_content(result)

        elif name == "wms.user.list":
            warehouse_id = arguments.get("warehouse_id")
            if not warehouse_id:
                return _error_content("warehouse_id is required")
            result = await core_client.get_users(
                warehouse_id=str(warehouse_id),
                role=arguments.get("role"),
            )
            target_role = arguments.get("role")
            if target_role and isinstance(result, dict) and "users" in result:
                result["users"] = [u for u in result["users"] if u.get("role") == target_role]
            return _text_content(result)

        elif name == "wms.location.list":
            warehouse_id = arguments.get("warehouse_id")
            if not warehouse_id:
                return _error_content("warehouse_id is required")
            result = await core_client.get_locations(
                warehouse_id=str(warehouse_id),
                type_=arguments.get("type"),
            )
            return _text_content(result)

        elif name == "wms.putaway.get":
            put_away_list_id = arguments.get("put_away_list_id")
            if not put_away_list_id:
                return _error_content("put_away_list_id is required")
            result = await core_client.get_put_away(str(put_away_list_id))
            return _text_content(result)

        else:
            return _error_content(f"Unknown tool: {name}")

    except httpx.HTTPStatusError as e:
        logger.exception("MCP tool HTTP error: %s", name)
        return _error_content(f"core-service returned {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.exception("MCP tool failed: %s", name)
        return _error_content(str(e))


# ── Register MCP handlers (only when SDK is present) ─────────────────────
if MCP_SDK_AVAILABLE:

    @mcp_server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Return the catalog of available tools for discovery."""
        return _TOOL_SCHEMAS

    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle a tool invocation from an MCP client."""
        return await _dispatch_tool(name, arguments)
