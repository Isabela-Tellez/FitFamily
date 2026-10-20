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
        "Población y pirámide de edad verificadas contra el Padrón Municipal (datos.madrid.es, "
        "octubre 2026). Hogares y negocios proceden de fuentes secundarias no verificadas."
    ),
    "source": (
        "Padrón Municipal de Habitantes (Ayuntamiento de Madrid, datos.madrid.es), "
        "actualizado el 6 de octubre de 2026, cobertura hasta el 30 de septiembre de 2026. "
        "URL padrón: https://datos.madrid.es/dataset/200076-0-padron. "
        "Verificación independiente: población sumada desde el CSV oficial (barrio 'EL CAÑAVERAL', "
        "distrito 19 Vicálvaro)."
    ),
    "geo_scope": "El Cañaveral, distrito de Vicálvaro, Madrid",
    "period": (
        "Población y pirámide: 1 de octubre de 2026; "
        "hogares (no verificado): enero 2026; negocios (no verificado): junio 2025"
    ),
    "indicators": {
        "population_total": {
            "value": 27480,
            "unit": "habitantes",
            "reference_period": "1 de octubre de 2026",
            "source_url": "https://datos.madrid.es/dataset/200076-0-padron",
            "consulted_at": "2026-10-20",
            "verification_status": "verified",
            "limitations": (
                "Población empadronada a 1 de octubre de 2026, calculada sumando todas las "
                "edades del barrio 'EL CAÑAVERAL' en el Padrón Municipal (datos.madrid.es, "
                "archivo CSV). Cifra en crecimiento: 24.963 hab. en enero de 2026 "
                "(Nuevosureste) y 17.193 hab. en 2024 (INE)."
            ),
        },
        "households_total": {
            "value": None,
            "unit": "hogares",
            "reference_period": None,
            "source_url": None,
            "consulted_at": "2026-10-20",
            "verification_status": "unverified",
            "limitations": (
                "Cifra secundaria no verificada: 9.224 hogares (enero 2026), publicada por el "
                "barrio en Instagram citando el Padrón. No se pudo contrastar contra la fuente "
                "primaria: el dataset oficial (datos.madrid.es/300438-0-hogares-tamano) solo cubre "
                "hasta el 1 de enero de 2025 y se organiza por distrito y sección censal, no por "
                "barrio. Para verificar: descargar el XLSX 2025 y agregar las secciones censales "
                "correspondientes a El Cañaveral."
            ),
        },
        "average_household_size": {
            "value": None,
            "unit": "personas por hogar",
            "reference_period": None,
            "source_url": None,
            "consulted_at": "2026-10-20",
            "verification_status": "unverified",
            "limitations": (
                "Cifra secundaria no verificada: 2,70 personas por hogar (enero 2026), publicada "
                "por el barrio en Instagram citando el Padrón. Sin respaldo de fuente primaria "
                "para 2026."
            ),
        },
        "population_under_20_share": {
            "value": 28.29,
            "unit": "porcentaje",
            "reference_period": "1 de octubre de 2026",
            "source_url": "https://datos.madrid.es/dataset/200076-0-padron",
            "consulted_at": "2026-10-20",
            "verification_status": "verified",
            "limitations": (
                "Porcentaje de población menor de 20 años calculado a partir del Padrón Municipal "
                "(octubre 2026): 7.774 de 27.480 habitantes. "
                "Indicador de potencial de familias con hijos; no es un conteo de familias."
            ),
        },
        "businesses_open": {
            "value": 234,
            "unit": "locales abiertos",
            "reference_period": "20 de octubre de 2026 (dataset actualizado diariamente)",
            "source_url": "https://datos.madrid.es/dataset/200085-0-censo-locales",
            "consulted_at": "2026-10-20",
            "verification_status": "verified",
            "limitations": (
                "Locales con situación 'Abierto' en El Cañaveral según el Censo de Locales "
                "del Ayuntamiento de Madrid (datos.madrid.es/200085-0-censo-locales, CSV, "
                "actualizado diariamente). 'Locales' (premises) no equivale a 'negocios' "
                "(establecimientos): un local puede albergar varias actividades. "
                "Cifra secundaria previa no verificada: 126 'negocios' (Wikipedia, junio 2025)."
            ),
        },
        "families_with_children": {
            "value": None,
            "unit": "familias",
            "reference_period": None,
            "source_url": None,
            "consulted_at": "2026-10-20",
            "verification_status": "unavailable",
            "limitations": (
                "No se encontró un censo directo de familias con hijos. "
                "Referencia indirecta verificada: 28,29 % de la población es menor de 20 años "
                "(Padrón municipal, octubre 2026)."
            ),
        },
        "gyms_registered": {
            "value": None,
            "unit": "centros",
            "reference_period": None,
            "source_url": None,
            "consulted_at": "2026-10-20",
            "verification_status": "unavailable",
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
            "reference_period": None,
            "source_url": None,
            "consulted_at": "2026-10-20",
            "verification_status": "unavailable",
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
    # Normalize common variants.
    canonical = stripped_area.replace(" ", "-").replace("_", "-")
    is_supported = canonical in {"el-cañaveral", "el-canaveral", "canaveral"}

    # Load data
    data = _load_statistics()
    indicators_available = data.get("indicators", {})
    geo_scope = data.get("geo_scope", area_id) if is_supported else area_id.strip()
    period = data.get("period", "desconocido")
    source = data.get("source", "fuente desconocida")

    # Build results based on requested indicators
    results: Dict[str, Any] = {}
    indicators_requested: List[str] = []

    if indicators:
        indicators_requested = [ind.strip() for ind in indicators if ind.strip()]
    else:
        indicators_requested = list(indicators_available.keys())

    for ind_name in indicators_requested:
        if not is_supported:
            results[ind_name] = {
                "value": None,
                "unit": None,
                "reference_period": None,
                "source_url": None,
                "consulted_at": None,
                "limitations": (
                    f"Datos no disponibles para '{area_id.strip()}'. "
                    "El almacén actual solo cubre El Cañaveral (Vicálvaro, Madrid)."
                ),
            }
        elif ind_name in indicators_available:
            results[ind_name] = indicators_available[ind_name]
        else:
            results[ind_name] = {
                "value": None,
                "unit": None,
                "limitations": f"Indicador '{ind_name}' no disponible en los datos locales."
            }

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