# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""MCP server entrypoint.

Expose Linear tools via Dedalus MCP framework.
OAuth credentials provided by DAuth at runtime.
"""

import os

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from linear.config import linear
from tools import linear_tools


def _disable_auto_output_schemas(server: MCPServer) -> None:
    # pylint: disable=protected-access
    server.tools._build_output_schema = lambda _fn: None  # type: ignore[assignment]


def create_server() -> MCPServer:
    """Create MCP server with current env config.

    Returns:
        Configured MCPServer instance.

    """
    as_url = os.getenv("DEDALUS_AS_URL", "https://as.dedaluslabs.ai")
    server = MCPServer(
        name="linear-mcp",
        connections=[linear],
        http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        streamable_http_stateless=True,
        authorization_server=as_url,
    )
    _disable_auto_output_schemas(server)
    return server


async def main() -> None:
    """Start MCP server."""
    server = create_server()
    server.collect(*linear_tools)
    await server.serve(port=8080)
