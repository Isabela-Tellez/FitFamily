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

import csv
import io
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-level data store for statistics
# In a real deployment, this would be populated from real data sources
_STATISTICS_DATA: Dict[str, Any] = {
    "description": (
        "Estadísticas locales documentadas para El Cañaveral (distrito de Vicálvaro, Madrid). "
        "Población y pirámide de edad verificadas contra el Padrón Municipal (datos.madrid.es, "
        "octubre 2026). Hogares y tamaño medio del hogar verificados contra el fichero oficial "
        "de hogares (datos.madrid.es/300438, referencia 1 de enero de 2025) agregado sobre las "
        "secciones censales que la cartografía oficial asigna al barrio. Locales abiertos "
        "verificados contra el Censo de Locales (octubre 2026)."
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
        "locales abiertos: descarga del 20 de octubre de 2026; "
        "población, hogares y tamaño medio del hogar: 1 de enero de 2025"
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
        "population_total_2025": {
            "value": 21492,
            "unit": "habitantes",
            "reference_period": "1 de enero de 2025",
            "source_url": "https://datos.madrid.es/dataset/300438-0-hogares-tamano",
            "consulted_at": "2026-10-20",
            "verification_status": "verified",
            "limitations": (
                "Población a 1 de enero de 2025 incluida en el fichero oficial de hogares "
                "(datos.madrid.es/300438-0-hogares-tamano). Coincide exactamente con la "
                "población oficial de El Cañaveral a esa fecha del dataset 'Población por "
                "distrito y barrio a 1 de enero' (21.492). Se publica para que los "
                "indicadores de hogares (referencia 1 ene 2025) y de población actual "
                "(referencia oct 2026) no se combinen entre sí."
            ),
        },
        "households_total": {
            "value": 8140,
            "unit": "hogares",
            "reference_period": "1 de enero de 2025",
            "source_url": "https://datos.madrid.es/dataset/300438-0-hogares-tamano",
            "consulted_at": "2026-10-20",
            "verification_status": "verified",
            "limitations": (
                "Suma exacta de los hogares de las 9 secciones censales que la cartografía "
                "oficial del Ayuntamiento asigna a El Cañaveral (COD_BAR 194: 19052, 19053, "
                "19054, 19055, 19056, 19058, 19059, 19060, 19061), según el Padrón Municipal "
                "revisado a 1 de enero de 2025. La agregación es exacta, no estimada: esas "
                "9 secciones teselan el polígono del barrio al 100% (0 m2 fuera del límite, "
                "0 m2 sin cubrir), por lo que ninguna sección cruza el borde del barrio. "
                "'Hogares' es el concepto del Padrón (personas que comparten vivienda), no "
                "'familias' ni 'viviendas'. Referencia temporal: 1 ene 2025, NO la de "
                "population_total (oct 2026); para ratios coherentes usar "
                "population_total_2025."
            ),
        },
        "average_household_size": {
            "value": 2.64,
            "unit": "personas por hogar",
            "reference_period": "1 de enero de 2025",
            "source_url": "https://datos.madrid.es/dataset/300438-0-hogares-tamano",
            "consulted_at": "2026-10-20",
            "verification_status": "verified",
            "limitations": (
                "Derivado de los mismos datos que households_total: 21.492 habitantes / "
                "8.140 hogares = 2,64 personas por hogar a 1 de enero de 2025. Coherente con "
                "el 'tamaño medio del hogar' publicado por sección en el fichero oficial. "
                "No debe combinarse con population_total (oct 2026): use population_total_2025."
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


# Add to src/mcp/server.py after _load_statistics function.
# Insert the following functions.

import csv
import io
import urllib.request
from datetime import datetime, timezone

_LOCALES_CSV_URL = "https://datos.madrid.es/dataset/200085-0-censo-locales/resource/200085-1-censo-locales/download/200085-1-censo-locales.csv"
_LOCALES_CACHE_PATH = None  # set lazily; see _locales_cache_path()

def _locales_cache_path():
    global _LOCALES_CACHE_PATH
    if _LOCALES_CACHE_PATH is None:
        from pathlib import Path
        _LOCALES_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "censo_locales.csv"
    return _LOCALES_CACHE_PATH

# Canonical barrio names as they appear in the CSV (uppercase, normalized).
_SUPPORTED_LOCALES_AREAS = {
    "el-cañaveral": "EL CAÑAVERAL",
    "el-canaveral": "EL CAÑAVERAL",
    "canaveral": "EL CAÑAVERAL",
}


def _normalize_barrio_name(name: str) -> str:
    return " ".join(name.strip().upper().split())


def parse_locales_csv(csv_text: str, barrio_name: str = "EL CAÑAVERAL") -> dict:
    """Parse the Censo de Locales CSV and count open premises for a barrio.

    Pure function: no network, no side effects. Returns a dict with:
    - status: "ok" or "error"
    - count: number of unique open premises (or None on error)
    - total_rows: total rows for the barrio
    - situations: list of distinct situations found
    - barrio_name: the barrio searched
    - error: error message (only on error)
    - consulted_at: ISO timestamp
    """
    result = {
        "barrio_name": barrio_name,
        "count": None,
        "total_rows": 0,
        "situations": [],
        "consulted_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
    }
    if not csv_text or not csv_text.strip():
        result["status"] = "error"
        result["error"] = "CSV vacío o sin contenido."
        return result

    try:
        reader = csv.DictReader(io.StringIO(csv_text), delimiter=";")
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Error al parsear CSV: {e}"
        return result

    if reader.fieldnames is None:
        result["status"] = "error"
        result["error"] = "CSV sin cabecera."
        return result

    # Normalize field names (strip quotes/whitespace).
    fields = {f.strip().strip('"'): f for f in reader.fieldnames}
    barrio_field = None
    sit_field = None
    id_field = None
    for candidate in ("desc_barrio_local", "desc_barrio", "barrio"):
        if candidate in fields:
            barrio_field = fields[candidate]
            break
    for candidate in ("desc_situacion_local", "desc_situacion", "situacion"):
        if candidate in fields:
            sit_field = fields[candidate]
            break
    for candidate in ("id_local", "id"):
        if candidate in fields:
            id_field = fields[candidate]
            break

    if not barrio_field or not sit_field or not id_field:
        result["status"] = "error"
        result["error"] = (
            f"Columnas requeridas no encontradas. Disponibles: {list(reader.fieldnames)}"
        )
        return result

    target = _normalize_barrio_name(barrio_name)
    seen_ids = set()
    situations = set()
    total = 0
    for row in reader:
        try:
            barrio = _normalize_barrio_name(row.get(barrio_field, "") or "")
        except Exception:
            continue
        if barrio != target:
            continue
        total += 1
        sit = (row.get(sit_field) or "").strip().strip('"')
        situations.add(sit)
        if sit.lower() == "abierto":
            lid = (row.get(id_field) or "").strip().strip('"')
            if lid:
                seen_ids.add(lid)

    result["total_rows"] = total
    result["situations"] = sorted(situations)
    result["count"] = len(seen_ids)
    if total == 0:
        result["status"] = "error"
        result["error"] = f"Barrio '{barrio_name}' no encontrado en el CSV."
    return result


def refresh_locales_count(area_id: str = "el-cañaveral", csv_text: str = None,
                         url: str = None, timeout: float = 60.0,
                         store: dict = None) -> dict:
    """Refresh the open-premises count for an area from the Censo de Locales.

    - If csv_text is provided, parse it (useful for tests).
    - Otherwise download from url (or the default URL).
    - On success, update _STATISTICS_DATA and return status "ok".
    - On failure, do NOT overwrite the existing value; return status "error"
      (or "unsupported" for areas without data).
    """
    canonical = (area_id or "").strip().lower().replace(" ", "-").replace("_", "-")
    barrio_name = _SUPPORTED_LOCALES_AREAS.get(canonical)
    if barrio_name is None:
        return {
            "status": "unsupported",
            "area_id": area_id,
            "error": f"Área '{area_id}' no soportada para el Censo de Locales.",
            "consulted_at": datetime.now(timezone.utc).isoformat(),
        }

    if store is None:
        store = _STATISTICS_DATA

    consulted_at = datetime.now(timezone.utc).isoformat()
    source_url = url or _LOCALES_CSV_URL

    if csv_text is None:
        try:
            with urllib.request.urlopen(source_url, timeout=timeout) as response:
                raw = response.read()
            csv_text = raw.decode("utf-8-sig", errors="replace")
        except Exception as e:
            return {
                "status": "error",
                "area_id": area_id,
                "source_url": source_url,
                "consulted_at": consulted_at,
                "error": f"Error al descargar el CSV: {e}",
            }

    parsed = parse_locales_csv(csv_text, barrio_name)
    if parsed["status"] != "ok":
        return {
            "status": "error",
            "area_id": area_id,
            "source_url": source_url,
            "consulted_at": consulted_at,
            "error": parsed.get("error", "Error al parsear el CSV."),
        }

    count = parsed["count"]
    # Update the data store.
    try:
        indicator = store["indicators"].setdefault("businesses_open", {})
        indicator["value"] = count
        indicator["unit"] = "locales abiertos"
        indicator["reference_period"] = f"descarga del {consulted_at[:10]}"
        indicator["source_url"] = source_url
        indicator["consulted_at"] = consulted_at
        indicator["verification_status"] = "verified"
        indicator["limitations"] = (
            f"Locales con situación 'Abierto' en {barrio_name.title()} según el Censo de Locales "
            f"del Ayuntamiento de Madrid (datos.madrid.es/200085-0-censo-locales, CSV, "
            f"actualizado diariamente). Descargado el {consulted_at[:10]}. "
            f"Total de filas para el barrio: {parsed['total_rows']}. "
            f"'Locales' (premises) no equivale a 'negocios' (establecimientos)."
        )
    except Exception as e:
        return {
            "status": "error",
            "area_id": area_id,
            "source_url": source_url,
            "consulted_at": consulted_at,
            "error": f"Error al actualizar el almacén de datos: {e}",
        }

    # Optionally cache the CSV locally.
    try:
        cache_path = _locales_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(csv_text, encoding="utf-8")
    except Exception:
        pass  # Caching is best-effort.

    return {
        "status": "ok",
        "area_id": area_id,
        "count": count,
        "total_rows": parsed["total_rows"],
        "situations": parsed["situations"],
        "source_url": source_url,
        "consulted_at": consulted_at,
    }


# ── Hogares (datos.madrid.es/300438-0-hogares-tamano) ────────────────────
# Agregación EXACTA de los hogares de las secciones censales que la
# cartografía oficial del Ayuntamiento asigna al barrio (columna COD_BAR).
# No requiere reparto proporcional: las secciones del barrio lo teselan
# íntegramente (verificado en el estudio espacial documentado).

_HOGARES_XLSX_URL = (
    "https://datos.madrid.es/dataset/300438-0-hogares-tamano/resource/"
    "300438-2-hogares-tamano-xlsx/download/300438-2-hogares-tamano-xlsx.xlsx"
)
_SECCIONES_SHP_URL = (
    "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/"
    "LIMITES_ADMINISTRATIVOS/Seccionado/Secciones_Censales.zip"
)
_HOGARES_REFERENCE_PERIOD = "1 de enero de 2025"

# Codigo oficial de barrio (atributo COD_BAR de la cartografia municipal).
_BARRIO_CODES = {
    "el-cañaveral": 194,
    "el-canaveral": 194,
    "canaveral": 194,
}


def parse_households_rows(rows, section_codes) -> dict:
    """Aggregate households data for a set of census sections.

    Pure function: no network, no I/O. ``rows`` is an iterable of
    ``(section_code, habitantes, total_hogares)`` tuples as published in the
    official households workbook.

    Returns a dict with:
    - status: "ok" or "error"
    - households: total households (or None on error)
    - inhabitants: total inhabitants (or None on error)
    - average_household_size: inhabitants / households
    - sections: per-section detail
    - missing_sections: requested sections absent from the source
    """
    wanted = {int(c) for c in section_codes}
    result = {
        "status": "ok",
        "households": None,
        "inhabitants": None,
        "average_household_size": None,
        "sections": {},
        "missing_sections": sorted(wanted),
        "reference_period": _HOGARES_REFERENCE_PERIOD,
    }
    total_h = 0
    total_pop = 0.0
    for code, habitantes, hogares in rows:
        try:
            code = int(code)
        except (TypeError, ValueError):
            continue
        if code not in wanted:
            continue
        if not isinstance(hogares, (int, float)) or not isinstance(habitantes, (int, float)):
            continue
        result["sections"][code] = {
            "inhabitants": habitantes,
            "households": hogares,
        }
        total_h += hogares
        total_pop += habitantes

    if not result["sections"]:
        result["status"] = "error"
        result["error"] = "Ninguna de las secciones solicitadas aparece en el fichero de hogares."
        return result

    result["missing_sections"] = sorted(wanted - set(result["sections"]))
    result["households"] = int(total_h)
    result["inhabitants"] = int(round(total_pop))
    result["average_household_size"] = round(total_pop / total_h, 4) if total_h else None
    if result["missing_sections"]:
        result["status"] = "error"
        result["error"] = (
            "Secciones ausentes en el fichero de hogares: "
            f"{result['missing_sections']}. La suma no sería completa."
        )
    return result


def _read_households_workbook(path):
    """Read the official households workbook and return (code, hab, hog) rows.

    Requires openpyxl (offline preparation tool, not a runtime dependency of
    the MCP server). Raises RuntimeError if the dependency is missing.
    """
    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError(
            "openpyxl no está instalado; es necesario solo para regenerar el "
            "fichero de hogares (herramienta offline, no dependencia del servidor MCP)."
        ) from e

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = []
    for r in ws.iter_rows(values_only=True):
        if len(r) < 4:
            continue
        code = r[1]
        if not isinstance(code, int):
            continue
        rows.append((code, r[2], r[3]))
    return rows


def _read_sections_for_barrio(path, barrio_code):
    """Return the census section codes officially assigned to a barrio.

    Requires pyogrio (via geopandas) to read the DBF attribute table.
    Raises RuntimeError if the dependency is missing.
    """
    try:
        import pyogrio
    except ImportError as e:
        raise RuntimeError(
            "pyogrio no está instalado; es necesario solo para regenerar el "
            "fichero de hogares (herramienta offline, no dependencia del servidor MCP)."
        ) from e

    import tempfile
    import zipfile
    import os

    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.upper().endswith(".DBF")]
        if not names:
            raise RuntimeError("El ZIP de secciones censales no contiene un DBF.")
        with tempfile.TemporaryDirectory() as tmp:
            z.extract(names[0], tmp)
            table = pyogrio.read_dataframe(os.path.join(tmp, names[0]))
    col = "COD_BAR" if "COD_BAR" in table.columns else None
    if col is None:
        raise RuntimeError("La capa de secciones censales no tiene la columna COD_BAR.")
    codes = table[table[col].astype(int) == int(barrio_code)]["COD_SECCIO"]
    return [int(c) for c in codes]


def refresh_households(area_id: str = "el-cañaveral", rows=None, section_codes=None,
                        store: dict = None, xlsx_path: str = None,
                        sections_zip_path: str = None) -> dict:
    """Refresh the households indicators for an area from official sources.

    - If ``rows`` and ``section_codes`` are provided the aggregation is pure
      (used by the unit tests).
    - Otherwise the official workbook and the official section cartography are
      read from disk (paths) or downloaded.

    On failure the stored values are NOT modified.
    """
    canonical = (area_id or "").strip().lower().replace(" ", "-").replace("_", "-")
    barrio_code = _BARRIO_CODES.get(canonical)
    if barrio_code is None:
        return {
            "status": "unsupported",
            "area_id": area_id,
            "error": f"Área '{area_id}' sin código de barrio oficial conocido.",
            "consulted_at": datetime.now(timezone.utc).isoformat(),
        }

    consulted_at = datetime.now(timezone.utc).isoformat()

    if rows is None or section_codes is None:
        try:
            import os
            import tempfile
            import urllib.request
            import zipfile

            tmp = tempfile.mkdtemp(prefix="fitfamily_hogares_")
            if xlsx_path is None:
                xlsx_path = os.path.join(tmp, "hogares.xlsx")
                with urllib.request.urlopen(_HOGARES_XLSX_URL, timeout=300) as resp:
                    data = resp.read()
                with open(xlsx_path, "wb") as fh:
                    fh.write(data)
            if sections_zip_path is None:
                sections_zip_path = os.path.join(tmp, "secciones.zip")
                with urllib.request.urlopen(_SECCIONES_SHP_URL, timeout=300) as resp:
                    data = resp.read()
                with open(sections_zip_path, "wb") as fh:
                    fh.write(data)
            section_codes = _read_sections_for_barrio(sections_zip_path, barrio_code)
            rows = _read_households_workbook(xlsx_path)
        except Exception as e:
            return {
                "status": "error",
                "area_id": area_id,
                "consulted_at": consulted_at,
                "error": f"Error al preparar los datos de hogares: {e}",
            }

    parsed = parse_households_rows(rows, section_codes)
    if parsed["status"] != "ok":
        return {
            "status": "error",
            "area_id": area_id,
            "consulted_at": consulted_at,
            "error": parsed.get("error", "Error al agregar los datos de hogares."),
        }

    if store is None:
        store = _STATISTICS_DATA

    sections_desc = ", ".join(str(c) for c in sorted(parsed["sections"]))
    households = parsed["households"]
    average = parsed["average_household_size"]
    inhabitants = parsed["inhabitants"]

    try:
        ind = store["indicators"]
        ind["households_total"] = {
            "value": households,
            "unit": "hogares",
            "reference_period": _HOGARES_REFERENCE_PERIOD,
            "source_url": "https://datos.madrid.es/dataset/300438-0-hogares-tamano",
            "consulted_at": consulted_at,
            "verification_status": "verified",
            "limitations": (
                "Suma exacta de los hogares de las secciones censales que la cartografía "
                f"oficial asigna al barrio ({sections_desc}), Padrón Municipal a "
                f"{_HOGARES_REFERENCE_PERIOD}. 'Hogares' es el concepto del Padrón, no "
                "'familias' ni 'viviendas'."
            ),
        }
        ind["average_household_size"] = {
            "value": round(average, 2),
            "unit": "personas por hogar",
            "reference_period": _HOGARES_REFERENCE_PERIOD,
            "source_url": "https://datos.madrid.es/dataset/300438-0-hogares-tamano",
            "consulted_at": consulted_at,
            "verification_status": "verified",
            "limitations": (
                f"Derivado: {inhabitants} habitantes / {households} hogares a "
                f"{_HOGARES_REFERENCE_PERIOD}. No combinar con population_total (oct 2026)."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "area_id": area_id,
            "consulted_at": consulted_at,
            "error": f"Error al actualizar el almacén de datos: {e}",
        }

    return {
        "status": "ok",
        "area_id": area_id,
        "households": households,
        "inhabitants": inhabitants,
        "average_household_size": average,
        "sections": sorted(parsed["sections"]),
        "reference_period": _HOGARES_REFERENCE_PERIOD,
        "consulted_at": consulted_at,
    }

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