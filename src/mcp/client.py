"""MCP client for the FitFamily research module.

Connects to the local MCP server, discovers available tools,
and invokes `get_area_statistics` to verify the protocol works.

Responsibilities:
- connect_mcp(): Connect to the local MCP server.
- list_mcp_tools(): Discover available tools.
- call_area_statistics(): Invoke get_area_statistics through the protocol.
"""

from __future__ import annotations

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp.types import Tool, TextContent

from src.schemas import ResearchResult

logger = logging.getLogger(__name__)


async def connect_mcp() -> Optional[ClientSession]:
    """Connect to the local MCP server via stdio.

    Returns:
        A connected ClientSession instance, or None if connection fails.
    """
    try:
        # Configure stdio parameters for local server
        params = {
            "command": "python",
            "args": [
                "-c",
                (
                    "import sys\n"
                    "sys.path.insert(0, '.')\n"
                    "from src.mcp.server import run_mcp_server\n"
                    "# Just verify the server module can be imported\n"
                    "print('SERVER_OK')\n"
                ),
            ],
            "env": None,
        }

        # Create a stdio client transport
        async with stdio_client(params) as (read, write):
            # Create session
            session = ClientSession(read, write)

            # Initialize the session
            await session.initialize()

            logger.info("Connected to MCP server successfully")
            return session

    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        return None


async def list_mcp_tools(session: ClientSession) -> List[Tool]:
    """List available tools from the MCP server.

    Args:
        session: An connected ClientSession.

    Returns:
        List of available Tool descriptors.
    """
    try:
        result = await session.list_tools()
        tools = result.tools if hasattr(result, "tools") else []
        logger.info(f"Found {len(tools)} tools on MCP server")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description[:60]}...")
        return tools
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return []


async def call_area_statistics(
    session: ClientSession,
    area_id: str,
    indicators: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Invoke get_area_statistics through the MCP protocol.

    Args:
        session: An connected ClientSession.
        area_id: Identifier for the area.
        indicators: Optional list of indicator names.

    Returns:
        The result dictionary from get_area_statistics.
    """
    try:
        # Call the tool
        result = await session.call_tool(
            name="get_area_statistics",
            arguments={
                "area_id": area_id,
                "indicators": indicators or [],
            },
        )

        # Extract text from the result
        # The result is a ToolResult with content
        if result.content and len(result.content) > 0:
            # Try to get the text content
            content = result.content[0]
            if hasattr(content, "text"):
                text = content.text
                # Try to parse as JSON
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"raw_text": text}
            elif hasattr(content, "name"):
                return {"name": content.name, "text": str(content.text)[:200]}

        # Fallback: return what we have
        return {"raw_result": str(result)[:200]}

    except Exception as e:
        logger.error(f"Failed to call get_area_statistics: {e}")
        return {"error": str(e)}


async def run_mcp_integration_test() -> Dict[str, Any]:
    """Run a full MCP integration test.

    This function:
    1. Connects to the local MCP server
    2. Lists available tools
    3. Calls get_area_statistics
    4. Returns the results

    Returns:
        Dictionary with test results.
    """
    result: Dict[str, Any] = {
        "connected": False,
        "tools_found": 0,
        "area_statistics_call": None,
        "error": None,
    }

    # Step 1: Connect to MCP server
    session = await connect_mcp()
    if session is None:
        result["error"] = "Could not connect to MCP server"
        return result

    result["connected"] = True

    # Step 2: List tools
    tools = await list_mcp_tools(session)
    result["tools_found"] = len(tools) if tools else 0

    # Check if get_area_statistics is available
    tool_names = [t.name for t in tools] if tools else []
    if "get_area_statistics" not in tool_names:
        result["error"] = "get_area_statistics tool not found on server"
        return result

    # Step 3: Call get_area_statistics
    stats_result = await call_area_statistics(
        session,
        area_id="el-cañaveral",
        indicators=["gyms_with_ludoteca", "population_total"],
    )
    result["area_statistics_call"] = stats_result

    return result


def main():
    """Synchronous entry point for running the MCP integration test."""
    try:
        # Run the async test
        test_result = asyncio.run(run_mcp_integration_test())

        print("=" * 60)
        print("MCP INTEGRATION TEST RESULTS")
        print("=" * 60)
        print(f"Connected to MCP server: {test_result['connected']}")
        print(f"Tools found: {test_result['tools_found']}")
        print()

        if test_result["area_statistics_call"]:
            stats = test_result["area_statistics_call"]
            print("get_area_statistics result:")
            print(f"  area_id: {stats.get('area_id')}")
            print(f"  indicators_requested: {stats.get('indicators_requested')}")
            print(f"  results count: {len(stats.get('results', {}))}")
            print(f"  source: {stats.get('source')}")
            print(f"  geo_scope: {stats.get('geo_scope')}")
            print(f"  period: {stats.get('period')}")
            print()
            if "error" in stats:
                print(f"  ERROR: {stats['error']}")
        else:
            print(f"Error: {test_result.get('error', 'Unknown error')}")

        print("=" * 60)

    except Exception as e:
        print(f"MCP integration test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()