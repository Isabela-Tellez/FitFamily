"""MCP client for the FitFamily research module.

Connects to the local MCP server over stdio, discovers available tools,
and invokes `get_area_statistics` to verify the protocol works.

Responsibilities:
- `connect_mcp()`: async context manager that keeps a local MCP session open.
- `list_mcp_tools()`: discover available tools.
- `call_area_statistics()`: invoke get_area_statistics through the protocol.

The stdio transport is tied to the lifetime of the session, so the session
must be used inside `async with connect_mcp() as session:`. A session cannot
be created and returned from a plain coroutine: closing the context manager
also closes the server subprocess.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

logger = logging.getLogger(__name__)

# Repository root: src/mcp/client.py -> src/mcp -> src -> root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def mcp_server_params() -> StdioServerParameters:
    """Build the stdio parameters used to launch the local MCP server.

    The server is started as a Python module from the repository root so
    that `from src.schemas import ...` resolves correctly in the subprocess.
    """
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp.server"],
        cwd=str(PROJECT_ROOT),
        env=None,
    )


@asynccontextmanager
async def connect_mcp() -> AsyncIterator[ClientSession]:
    """Open a session against the local MCP server via stdio.

    Usage:
        async with connect_mcp() as session:
            tools = await list_mcp_tools(session)

    Yields:
        An initialized ClientSession, valid only inside the context.

    Raises:
        RuntimeError: If the server cannot be started or initialized.
    """
    params = mcp_server_params()
    logger.info(
        "Starting local MCP server: %s %s (cwd=%s)",
        params.command,
        " ".join(params.args),
        params.cwd,
    )

    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("Connected to MCP server successfully")
                yield session
    except Exception as e:
        logger.error("MCP session failed: %s", e)
        raise RuntimeError(f"Could not start or initialize MCP server: {e}") from e


async def list_mcp_tools(session: ClientSession) -> List[Tool]:
    """List available tools from the MCP server.

    Args:
        session: An initialized ClientSession.

    Returns:
        List of available Tool descriptors (empty list on failure).
    """
    try:
        result = await session.list_tools()
        tools = result.tools if hasattr(result, "tools") else []
        logger.info("Found %d tools on MCP server", len(tools))
        for tool in tools:
            logger.info("  - %s: %s...", tool.name, (tool.description or "")[:60])
        return tools
    except Exception as e:
        logger.error("Failed to list tools: %s", e)
        return []


async def call_area_statistics(
    session: ClientSession,
    area_id: str,
    indicators: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Invoke get_area_statistics through the MCP protocol.

    Args:
        session: An initialized ClientSession.
        area_id: Identifier for the area.
        indicators: Optional list of indicator names.

    Returns:
        The result dictionary from get_area_statistics, or a dict with an
        `error` key if the call fails.
    """
    arguments: Dict[str, Any] = {"area_id": area_id}
    if indicators:
        arguments["indicators"] = indicators

    try:
        result = await session.call_tool(
            name="get_area_statistics",
            arguments=arguments,
        )

        if getattr(result, "isError", False):
            message = _first_text(result) or "unknown MCP tool error"
            logger.error("get_area_statistics returned an error: %s", message)
            return {"error": message}

        # Prefer structured content when the SDK provides it.
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict) and structured:
            return structured

        text = _first_text(result)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_text": text}

        return {"raw_result": str(result)[:500]}

    except Exception as e:
        logger.error("Failed to call get_area_statistics: %s", e)
        return {"error": str(e)}


def _first_text(result: Any) -> Optional[str]:
    """Return the first text block of a CallToolResult, if any."""
    for content in getattr(result, "content", None) or []:
        text = getattr(content, "text", None)
        if text:
            return text
    return None


async def run_mcp_integration_test() -> Dict[str, Any]:
    """Run a full MCP integration test against the real local server.

    Returns:
        Dictionary with the connection status, discovered tools, and the
        result of calling `get_area_statistics`.
    """
    result: Dict[str, Any] = {
        "connected": False,
        "tools_found": 0,
        "area_statistics_call": None,
        "error": None,
    }

    try:
        async with connect_mcp() as session:
            result["connected"] = True

            tools = await list_mcp_tools(session)
            result["tools_found"] = len(tools)
            tool_names = [t.name for t in tools]
            if "get_area_statistics" not in tool_names:
                result["error"] = "get_area_statistics tool not found on server"
                return result

            result["area_statistics_call"] = await call_area_statistics(
                session,
                area_id="el-cañaveral",
                indicators=["gyms_with_ludoteca", "population_total"],
            )
    except Exception as e:
        result["error"] = str(e)

    return result


def main() -> None:
    """Synchronous entry point for running the MCP integration test."""
    test_result = asyncio.run(run_mcp_integration_test())

    print("=" * 60)
    print("MCP INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Connected to MCP server: {test_result['connected']}")
    print(f"Tools found: {test_result['tools_found']}")
    print()

    stats = test_result["area_statistics_call"]
    if stats:
        print("get_area_statistics result:")
        print(f"  area_id: {stats.get('area_id')}")
        print(f"  indicators_requested: {stats.get('indicators_requested')}")
        print(f"  results count: {len(stats.get('results', {}))}")
        print(f"  source: {stats.get('source')}")
        print(f"  geo_scope: {stats.get('geo_scope')}")
        print(f"  period: {stats.get('period')}")
        if "error" in stats:
            print(f"  ERROR: {stats['error']}")
    elif test_result["error"]:
        print(f"Error: {test_result['error']}")
    else:
        print("No statistics returned.")

    print("=" * 60)


if __name__ == "__main__":
    main()
