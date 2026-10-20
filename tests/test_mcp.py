"""Unit tests for the MCP module (Persona 1 - Juan).

These tests do not start a server subprocess and do not require internet.
The real stdio end-to-end check lives in `test_mcp_integration.py`.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp.server import get_area_statistics
from src.mcp.client import (
    mcp_server_params,
    call_area_statistics,
    _first_text,
)


# --- Server function tests ---

def test_get_area_statistics_returns_dict():
    """Test that get_area_statistics returns a dict with area data."""
    stats = get_area_statistics("el-cañaveral", ["gyms_with_ludoteca"])
    assert isinstance(stats, dict)
    assert "area_id" in stats
    assert stats["area_id"] == "el-cañaveral"


def test_get_area_statistics_with_multiple_indicators():
    """Test that multiple indicators can be queried."""
    indicators = ["gyms_with_ludoteca", "population_density", "average_income"]
    stats = get_area_statistics("el-cañaveral", indicators)
    assert isinstance(stats, dict)
    assert stats["area_id"] == "el-cañaveral"
    assert set(stats["indicators_requested"]) == set(indicators)
    assert set(stats["results"]) == set(indicators)


def test_get_area_statistics_unknown_indicator_is_declared_missing():
    """Unknown indicators must be reported as unavailable, never invented."""
    stats = get_area_statistics("el-cañaveral", ["does_not_exist"])
    entry = stats["results"]["does_not_exist"]
    assert entry["value"] is None
    assert "does_not_exist" in entry["limitations"]


def test_get_area_statistics_placeholder_data():
    """Test that MCP data is clearly marked as placeholder."""
    stats = get_area_statistics("el-cañaveral", ["gyms_with_ludoteca"])
    assert stats["results"]["gyms_with_ludoteca"]["value"] is None


def test_get_area_statistics_different_areas():
    """Test that different areas return different area identifiers."""
    stats1 = get_area_statistics("el-cañaveral", ["gyms_with_ludoteca"])
    stats2 = get_area_statistics("valdebebas", ["gyms_with_ludoteca"])
    assert stats1["area_id"] == "el-cañaveral"
    assert stats2["area_id"] == "valdebebas"


def test_get_area_statistics_empty_indicators_returns_all():
    """An empty indicator list must return every available indicator."""
    stats = get_area_statistics("el-cañaveral", [])
    assert stats["area_id"] == "el-cañaveral"
    # The four original indicators must remain available.
    for key in ("population_total", "families_with_children", "gyms_registered", "gyms_with_ludoteca"):
        assert key in stats["results"]
    assert len(stats["results"]) >= 4


def test_get_area_statistics_rejects_empty_area():
    """Empty area identifiers must be rejected."""
    import pytest
    with pytest.raises(ValueError):
        get_area_statistics("   ", ["gyms_with_ludoteca"])


# --- Client tests (no subprocess) ---

def test_mcp_server_params_launch_server_module():
    """The client must launch the real server module from the repo root."""
    params = mcp_server_params()
    assert params.command == sys.executable
    assert params.args == ["-m", "src.mcp.server"]
    assert params.cwd is not None


class _FakeContent:
    def __init__(self, text):
        self.text = text


class _FakeResult:
    def __init__(self, text, is_error=False):
        self.content = [_FakeContent(text)]
        self.structuredContent = None
        self.isError = is_error


class _FakeSession:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


def test_call_area_statistics_parses_json_content():
    """The client must decode the JSON payload returned over MCP."""
    payload = {"area_id": "el-cañaveral", "results": {"population_total": 1}}
    session = _FakeSession(_FakeResult(json.dumps(payload)))

    result = asyncio.run(
        call_area_statistics(session, "el-cañaveral", ["population_total"])
    )

    assert result == payload
    assert session.calls == [
        (
            "get_area_statistics",
            {"area_id": "el-cañaveral", "indicators": ["population_total"]},
        )
    ]


def test_call_area_statistics_returns_error_dict_on_tool_error():
    """Tool errors must be surfaced, not silently swallowed."""
    session = _FakeSession(_FakeResult("boom", is_error=True))

    result = asyncio.run(call_area_statistics(session, "el-cañaveral"))

    assert result == {"error": "boom"}


def test_call_area_statistics_omits_empty_indicators():
    """Empty indicators must not be sent as an explicit empty list."""
    session = _FakeSession(_FakeResult(json.dumps({"area_id": "x"})))

    asyncio.run(call_area_statistics(session, "x", None))

    assert session.calls == [("get_area_statistics", {"area_id": "x"})]


def test_first_text_returns_none_without_content():
    """A result without content blocks must not raise."""
    class _Empty:
        content = []

    assert _first_text(_Empty()) is None
