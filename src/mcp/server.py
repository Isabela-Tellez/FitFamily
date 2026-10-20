"""MCP server for the FitFamily research module.

Publishes the `get_area_statistics` tool via the official MCP SDK.
This tool queries locally documented data and returns a structured response.

The server is designed to be run locally and discovered by the MCP client.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

logger = logging.getLogger(__name__)

# Module-level data store for statistics
# In a real deployment, this would be populated from real data sources
_STATISTICS_DATA: Dict[str, Any] = {
    "description": (
        "Estadísticas locales documentadas para El Cañaveral (distrito de Vicálvaro, Madrid). "
        "Fuentes primarias: Padrón Municipal de Habitantes (Ayuntamiento de Madrid / datos.madrid.es) "
        "y Wikipedia (citando INE/Padrón). Los valores son observados, no estimados."
    ),
    "source": (
        "Ayuntamiento de Madrid - Padrón Municipal de Habitantes "
        "(https://datos.madrid.es/.../Padrón) y Wikipedia 'El Cañaveral' "
        "(ed. 6 sep 2026, citando INE/Padrón)."
    ),
    "geo_scope": "El Cañaveral, distrito de Vicálvaro, Madrid",
    "period": (
        "Población: agosto 2026; hogares: enero 2026; negocios: junio 2025; "
        "pirámide de población: 2021"
    ),
    "indicators": {
        "population_total": {
            "value": 27014,
            "unit": "habitantes",
            "limitations": (
                "Población empadronada en agosto de 2026 (Wikipedia, citando Padrón). "
                "No equivale necesariamente a residentes efectivos; cifra en crecimiento "
                "(17 193 hab. en 2024 según INE)."
            ),
        },
        "households_total": {
            "value": 9224,
            "unit": "hogares",
            "limitations": (
                "Hogares empadronados a 1 de enero de 2026, con media de 2,70 personas por vivienda "
                "(Padrón, vía Instagram del barrio)."
            ),
        },
        "average_household_size": {
            "value": 2.70,
            "unit": "personas por hogar",
            "limitations": "Dato del Padrón a 1 de enero de 2026.",
        },
        "population_under_20_share": {
            "value": 25.46,
            "unit": "porcentaje",
            "limitations": (
                "Porcentaje de población menor de 20 años según la pirámide de población de 2021. "
                "Indicador de potencial de familias con hijos; no es un conteo de familias."
            ),
        },
        "businesses_open": {
            "value": 126,
            "unit": "negocios",
            "limitations": (
                "Negocios abiertos en El Cañaveral a 1 de junio de 2025 (Wikipedia, citando datos municipales). "
                "Incluye todo tipo de actividad, no solo ocio/deporte."
            ),
        },
        "families_with_children": {
            "value": None,
            "unit": "familias",
            "limitations": (
                "No se encontró un censo directo de familias con hijos. "
                "Referencia indirecta: 25,46 % de la población es menor de 20 años (2021)."
            ),
        },
        "gyms_registered": {
            "value": None,
            "unit": "centros",
            "limitations": (
                "No se encontró censo municipal publicado de centros deportivos. "
                "Centros localizados manualmente en la web (no censo oficial): "
                "9F Cañaveral, Énergie Fitness, One More Cañaveral, Nine Fitness, "
                "Winfit, Sano Center, Brooklyn Fitboxing, Silva Training Center "
                "(y Dreamfit en Valdebernardo, limítrofe)."
            ),
        },
        "gyms_with_ludoteca": {
            "value": None,
            "unit": "centros",
            "limitations": (
                "No se encontró censo municipal. Ninguno de los centros localizados "
                "publica ludoteca de forma verificable en su web; confirmar por contacto directo."
            ),
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
    async def list_tools() -> List[Tool]:
        """List available tools published by this MCP server."""
        return [
            Tool(
                name="get_area_statistics",
                description=(
                    "Estadísticas locales para un área geográfica específica. "
                    "Consulta datos documentados sobre población, familias, "
                    "y centros deportivos con ludoteca."
                ),
                inputSchema={
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
            )
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