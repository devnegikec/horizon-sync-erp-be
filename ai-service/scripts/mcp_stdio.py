"""stdio entrypoint for the WMS MCP server.

Usage (for Claude Desktop, Cursor, or any local MCP client):
    python scripts/mcp_stdio.py

This speaks the MCP protocol over stdin/stdout so desktop AI assistants
can discover and call WMS tools without running a web server.
"""

import asyncio
import logging
import sys

sys.path.insert(0, ".")

from app.services.mcp_server import MCP_SDK_AVAILABLE, mcp_server

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)


async def main():
    if not MCP_SDK_AVAILABLE or mcp_server is None:
        print("MCP SDK not installed. Run: pip install mcp>=1.0", file=sys.stderr)
        sys.exit(1)

    logger.info("Starting WMS MCP server on stdio...")
    try:
        from mcp.server.stdio import stdio_server
    except ImportError:
        logger.error("mcp.server.stdio not found — SDK API may have changed")
        sys.exit(1)

    async with stdio_server() as (read_stream, write_stream):
        init_options = (
            mcp_server.create_initialization_options()
            if hasattr(mcp_server, "create_initialization_options")
            else None
        )
        await mcp_server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
