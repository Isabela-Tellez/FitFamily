"""End-to-end MCP integration test (Persona 1 - Juan).

This test starts the real local MCP server as a subprocess over stdio,
discovers its tools, and invokes `get_area_statistics` through the protocol.

It requires no internet access and no API keys. It is slower than the unit
tests because it spawns a Python subprocess.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp.client import run_mcp_integration_test


def test_mcp_end_to_end_over_stdio():
    """Connect, list tools, and call get_area_statistics for real."""
    result = asyncio.run(run_mcp_integration_test())

    assert result["connected"] is True, f"connection failed: {result['error']}"
    assert result["tools_found"] == 1
    assert result["error"] is None

    stats = result["area_statistics_call"]
    assert stats is not None
    assert "error" not in stats
    assert stats["area_id"] == "el-cañaveral"
    assert "gyms_with_ludoteca" in stats["results"]

    # Placeholder data must be declared, not invented.
    assert stats["results"]["gyms_with_ludoteca"]["value"] is None
    assert stats["results"]["gyms_with_ludoteca"]["limitations"]
