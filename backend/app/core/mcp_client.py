"""Gmail MCP client. Real Model Context Protocol stdio transport.

Spawns the configured Gmail MCP server as a subprocess (stdio) and invokes the
`create_draft` tool with the email payload. The user must run an MCP-compliant
Gmail server; the command + args are configured via env vars:

  GMAIL_MCP_COMMAND  e.g. "npx" or "python"
  GMAIL_MCP_ARGS     comma-separated args, e.g. "-y,@modelcontextprotocol/server-gmail"

The tool name (`create_draft`) and its argument shape match common Gmail MCP
servers; if the chosen server differs, override `GMAIL_MCP_TOOL_NAME` or
adjust `_build_tool_args`.

This client is invoked only after the admin approves an email pending_action
(R-APPROVE1). No drafts are created without approval.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)

DEFAULT_TOOL_NAME = "create_draft"


def _command_args() -> tuple[str, list[str]]:
    cmd = settings.gmail_mcp_command
    if not cmd:
        raise RuntimeError("GMAIL_MCP_COMMAND not configured")
    args = [a for a in (settings.gmail_mcp_args or "").split(",") if a]
    return cmd, args


def _build_tool_args(*, payload: dict[str, Any], to: str) -> dict[str, Any]:
    """Map our internal email payload to the MCP tool argument shape."""
    return {
        "to": to,
        "subject": payload.get("subject", ""),
        "body": payload.get("body", ""),
    }


async def create_draft(*, payload: dict[str, Any], to: str) -> dict[str, Any]:
    """Create a Gmail draft via the configured MCP server.

    payload keys: subject, body, market_context, booking_code (the body already
    has Market Context interpolated by services/voice/post_call).

    Returns the MCP server's tool response (typically `{ "draftId": "...", ... }`).
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    cmd, args = _command_args()
    server_params = StdioServerParameters(command=cmd, args=args)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_args = _build_tool_args(payload=payload, to=to)
            log.info("mcp.create_draft tool=%s to=%s", DEFAULT_TOOL_NAME, to)
            result = await session.call_tool(DEFAULT_TOOL_NAME, tool_args)
            # mcp >=1.0 returns a CallToolResult with .content list
            return _extract_result(result)


def _extract_result(result: Any) -> dict[str, Any]:
    """Best-effort flatten of an MCP CallToolResult into a JSON-serialisable dict."""
    if isinstance(result, dict):
        return result
    out: dict[str, Any] = {}
    is_error = getattr(result, "isError", None)
    if is_error is not None:
        out["isError"] = bool(is_error)
    content = getattr(result, "content", None)
    if content:
        out["content"] = [
            getattr(item, "model_dump", lambda: getattr(item, "__dict__", {}))()
            for item in content
        ]
    return out


def create_draft_sync(*, payload: dict[str, Any], to: str) -> dict[str, Any]:
    """Sync convenience for callers that aren't already in an event loop."""
    return asyncio.run(create_draft(payload=payload, to=to))
