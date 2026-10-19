"""MCP server for the FitFamily research module.

Publishes the `get_area_statistics` tool via the official MCP SDK.
This tool queries locally documented data and returns a structured response.

The server is designed to be run locally and discovered by the MCP client.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.schemas import (
    ResearchBrief,
    Evidence,
    Competitor,
    ResearchResult,
)

logger = logging.getLogger(__name__)

# Module-level data store for statistics
# In a real deployment, this would be populated from real data sources
_STATISTICS_DATA: Dict[str, Any] = {
    "description": "Estadísticas locales documentadas para El Cañaveral y alrededores.",
    "source": "Datos municipales y fuentes abiertas consultadas durante la investigación.",
    "geo_scope": "El Cañaveral, Madrid",
    "period": "2020-2024 (últimos datos disponibles)",
    "indicators": {
        "population_total": {
            "value": None,
            "unit": "habitantes",
            "limitations": "Dato no disponible en fuentes consultadas.",
        },
        "families_with_children": {
            "value": None,
            "unit": "familias",
            "limitations": "Dato no disponible en fuentes consultadas.",
        },
        "gyms_registered": {
            "value": None,
            "unit": "centros",
            "limitations": "Dato no disponible en fuentes consultadas.",
        },
        "gyms_with_ludoteca": {
            "value": None,
            "unit": "centros",
            "limitations": "Dato no disponible en fuentes consultadas.",
        },
    },
}


def _load_statistics() -> Dict[str, Any]:
    """Load statistics data from the module's data store.

    Returns:
        Dictionary with the statistics data.
    """
    return _STATISTICS_DATA


def get_area_statistics(area_id: str, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """Query local statistics for a given area and indicators.

    This tool must be published via MCP and is callable by the MCP client.

    Args:
        area_id: Identifier for the area (e.g., "el-cañaveral", "madrid").
        indicators: Optional list of indicator names to retrieve.
                  If None or empty, all available indicators are returned.

    Returns:
        A dictionary with:
        - area_id: The requested area identifier.
        - indicators_requested: List of indicators actually requested.
        - results: Dictionary of indicator name -> value/data.
        - source: Source of the data.
        - geo_scope: Geographic scope.
        - period: Period to which data refers.
        - limitations: Known limitations of the data.

    Raises:
        ValueError: If the area_id is empty or invalid.
    """
    # Validate area_id
    if not area_id or not isinstance(area_id, str) or not area_id.strip():
        raise ValueError("area_id must be a non-empty string.")

    stripped_area = area_id.strip().lower()

    # Load data
    data = _load_statistics()
    indicators_available = data.get("indicators", {})
    geo_scope = data.get("geo_scope", area_id)
    period = data.get("period", "desconocido")
    source = data.get("source", "fuente desconocida")

    # Build results based on requested indicators
    results: Dict[str, Any] = {}
    indicators_requested: List[str] = []

    if indicators:
        # User specified which indicators they want
        indicators_requested = [ind.strip() for ind in indicators if ind.strip()]
        for ind_name in indicators_requested:
            if ind_name in indicators_available:
                results[ind_name] = indicators_available[ind_name]
            else:
                results[ind_name] = {
                    "value": None,
                    "unit": None,
                    "limitations": f"Indicador '{ind_name}' no disponible en los datos locales."
                }
    else:
        # Return all available indicators
        indicators_requested = list(indicators_available.keys())
        for ind_name, ind_data in indicators_available.items():
            results[ind_name] = ind_data

    # Build response
    response: Dict[str, Any] = {
        "area_id": stripped_area,
        "indicators_requested": indicators_requested,
        "results": results,
        "source": source,
        "geo_scope": geo_scope,
        "period": period,
        "limitations": data.get("description", ""),
    }

    logger.info(
        f"get_area_statistics called: area='{stripped_area}', "
        f"indicators={indicators_requested}, results_keys={list(results.keys())}"
    )

    return response


def run_mcp_server() -> None:
    """Run the MCP server using stdio transport.

    This function starts the MCP server that listens on stdio,
    making it discoverable by MCP clients in the same process.

    The server publishes the `get_area_statistics` tool.
    """
    server = Server("fitfamily-research-mcp")

    @server.list_tools()
    async def list_tools() -> list:
        """List available tools published by this MCP server."""
        return [
            {
                "name": "get_area_statistics",
                "description": (
                    "Estadísticas locales para un área geográfica específica. "
                    "Consulta datos documentados sobre población, familias, "
                    "y centros deportivos con ludotela."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "area_id": {
                            "type": "string",
                            "description": "Identifier for the area (e.g., 'el-cañaveral')."
                        },
                        "indicators": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of indicator names to retrieve.",
                        },
                    },
                    "required": ["area_id"],
                },
            }
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> Any:
        """Handle tool calls from MCP clients."""
        if name == "get_area_statistics":
            area_id = arguments.get("area_id", "")
            indicators = arguments.get("indicators", None)
            return get_area_statistics(area_id, indicators)
        else:
            raise ValueError(f"Unknown tool: {name}")

    # Run the server
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    """Entry point: run the MCP server."""
    logger.info("Starting FitFamily MCP server...")
    run_mcp_server()