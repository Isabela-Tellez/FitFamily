"""Source discovery for FitFamily.

Given a variable that is missing from a research, this module builds several
targeted queries, runs them with the module's own search tool and returns the
candidate sources with an explicit state:

- ``discovered``: the source was located.
- ``accessible``: the resource could be fetched and read.
- ``extracted``: the data could be parsed (CSV/JSON/HTML table).
- ``validated``: the content actually contains the requested variable.
- ``rejected``: the source was discarded, with the reason.

The module never invents a source: a candidate is only ``discovered`` when a
real search returned it, and it is only ``validated`` when its content has
been read and checked for the requested variable.

It is deliberately not a fixed list of Madrid datasets: the queries are built
from the variable itself, so the same code discovers sources for other
variables, municipalities or projects.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlsplit

from src.tools.search_web import search_web

logger = logging.getLogger(__name__)

# Organisms that publish official statistics and open data in Spain.
DEFAULT_ORGANISMS = (
    "ine.es",
    "datos.gob.es",
    "datos.madrid.es",
    "comunidad.madrid",
    "datos.comunidad.madrid",
    "geoportal.madrid.es",
    "csd.gob.es",
    "sep.es",
)

# Words that usually accompany a downloadable resource.
DATASET_HINTS = (
    "descargar", "download", "csv", "xlsx", "json", "api", "datos abiertos",
    "conjunto de datos", "dataset", "fichero", "consulta", "consulta de datos",
)

# Extensions that identify a machine readable resource.
DATASET_EXTENSIONS = (
    ".csv", ".xlsx", ".xls", ".json", ".geojson", ".zip", ".shp", ".gpx", ".xml",
)

# Terms that must appear in the content to consider the variable covered.
_GENERIC_STOPWORDS = {
    "datos", "dato", "informacion", "por", "de", "del", "la", "el",
    "los", "las", "en", "para", "con", "media", "seccion", "censal",
    "variable", "fuente", "serie", "historico", "actual",
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())


def build_queries(
    variable: str,
    area: Optional[str] = None,
    organisms: Sequence[str] = DEFAULT_ORGANISMS,
    max_queries: int = 6,
) -> List[str]:
    """Build several targeted queries for a missing variable.

    Different formulations are used on purpose: a variable can be published
    under a different name, and a source can be indexed as a dataset page or
    as a plain web page.
    """
    variable = (variable or "").strip()
    if not variable:
        return []
    scope = (area or "").strip()
    queries: List[str] = []

    queries.append(f"{variable} {scope}".strip())
    queries.append(f"datos abiertos {variable} {scope}".strip())
    queries.append(f"estadística {variable} {scope}".strip())
    for organism in organisms:
        queries.append(f"site:{organism} {variable}".strip())
        if len(queries) >= max_queries:
            break
    # Keep the order, drop the empty ones and the duplicates.
    seen = set()
    result = []
    for query in queries:
        key = _normalize(query)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(query)
    return result[:max_queries]


def required_terms(variable: str) -> List[str]:
    """Content terms that must appear for a source to be considered useful."""
    words = [w for w in re.findall(r"[\wáéíóúñÁÉÍÓÚÑ]+", variable.lower())
             if len(w) > 3 and w not in _GENERIC_STOPWORDS]
    return list(dict.fromkeys(words))


def looks_like_dataset(url: str, content: str = "") -> bool:
    """Tell apart an informative page from a downloadable resource."""
    lowered = (url or "").lower()
    if any(lowered.endswith(ext) for ext in DATASET_EXTENSIONS):
        return True
    if "/dataset/" in lowered or "/datasets/" in lowered or "/api/" in lowered:
        return True
    if lowered.startswith("data:") or lowered.startswith("opendata"):
        return True
    normalized = _normalize(content)
    return any(hint in normalized for hint in ("csv", "xlsx", "json", "api", "datos abiertos"))


def extract_table(text: str) -> List[Dict[str, str]]:
    """Extract a simple table from an HTML or CSV text.

    Only the tables the official portals publish in a regular way are
    supported: CSV text, or HTML tables whose rows have the same number of
    cells. It never guesses values.
    """
    if not text:
        return []
    if "<table" not in text.lower() and (";" in text or "," in text):
        separator = ";" if text.count(";") >= text.count(",") else ","
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=separator)
            rows = [dict(row) for row in reader]
            if rows:
                return rows
        except Exception:
            pass
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.IGNORECASE | re.DOTALL)
    table: List[Dict[str, str]] = []
    header: List[str] = []
    for row in rows:
        cells = [re.sub(r"<[^>]+>", " ", cell)
                 for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.IGNORECASE | re.DOTALL)]
        cells = [" ".join(cell.split()) for cell in cells]
        if not cells:
            continue
        if not header:
            header = cells
            continue
        table.append({header[i] if i < len(header) else f"col_{i}": cell
                      for i, cell in enumerate(cells)})
    return table


def _contains_term(text: str, term: str) -> bool:
    """Whole-word, accent-insensitive match with singular/plural variants.

    "renta" must not be satisfied by "rentabilidad", while "rentas" and
    "poblacion" must satisfy "renta" and "población".
    """
    term = _normalize(term)
    variants = {term, term + "s", term + "es"}
    if term.endswith("es") and len(term) > 4:
        variants.add(term[:-2])
    if term.endswith("s") and len(term) > 3:
        variants.add(term[:-1])
    pattern = "|".join(
        re.escape(variant) for variant in sorted(variants, key=len, reverse=True)
    )
    return re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)", text) is not None


def check_variable(content: str, variable: str) -> Dict[str, Any]:
    """Check whether a content really contains the requested variable.

    Every key term must appear. Accepting a subset would validate a page about
    "rentabilidad y barrios" as a source for "renta media por barrio".
    """
    terms = required_terms(variable)
    normalized = _normalize(content)
    if not terms:
        return {"covered": False, "matched": [], "reason": "Variable demasiado generica para comprobar."}
    matched = [term for term in terms if _contains_term(normalized, term)]
    covered = len(matched) == len(terms)
    reason = (
        "Contiene los terminos clave de la variable."
        if covered else
        "El contenido no menciona los terminos clave de la variable (%s)." % ", ".join(terms)
    )
    return {"covered": covered, "matched": matched, "reason": reason}


def _organism_of(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    for organism in DEFAULT_ORGANISMS:
        if organism in host:
            return organism
    return host or "desconocido"


def discover_sources(
    variable: str,
    area: Optional[str] = None,
    max_results_per_query: int = 5,
    max_queries: int = 6,
    organisms: Sequence[str] = DEFAULT_ORGANISMS,
    read_callable=None,
    search_callable=None,
    fetch_content: bool = True,
) -> List[Dict[str, Any]]:
    """Search for the sources that can provide a missing variable.

    Every candidate goes through the same pipeline: discovered -> accessible ->
    extracted -> validated, or rejected with a reason. Nothing is returned as
    validated without having read its content.
    """
    search = search_callable or search_web
    read = read_callable
    if read is None and fetch_content:
        from src.tools.read_web_page import read_web_page
        read = read_web_page

    queries = build_queries(variable, area, organisms, max_queries)
    results: List[Dict[str, Any]] = []
    seen_urls = set()

    for query in queries:
        try:
            found = search(query, max_results=max_results_per_query)
        except Exception as e:
            logger.info("Search failed for %r: %s", query, e)
            results.append({
                "url": None, "query": query, "state": "rejected",
                "reason": f"La busqueda fallo: {e}",
                "organism": None, "variable": variable,
            })
            continue

        if not found:
            results.append({
                "url": None, "query": query, "state": "rejected",
                "reason": "La consulta no devolvio resultados.",
                "organism": None, "variable": variable,
            })
            continue

        for item in found:
            url = getattr(item, "url", None)
            title = getattr(item, "title", None) or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidate: Dict[str, Any] = {
                "url": url,
                "title": title,
                "query": query,
                "organism": _organism_of(url),
                "variable": variable,
                "state": "discovered",
                "reason": "",
                "is_dataset": looks_like_dataset(url, title),
                "matched_terms": [],
            }
            if read is None:
                candidate["reason"] = "No se ha leido el contenido (validacion desactivada)."
                results.append(candidate)
                continue
            try:
                page = read(url)
            except Exception as e:
                candidate["state"] = "rejected"
                candidate["reason"] = f"No se pudo acceder al recurso: {e}"
                results.append(candidate)
                continue

            content = getattr(page, "body_text", "") or ""
            candidate["state"] = "accessible"
            candidate["reason"] = "Recurso accesible."
            table = extract_table(content)
            if table:
                candidate["state"] = "extracted"
                candidate["rows"] = len(table)
                candidate["columns"] = list(table[0].keys())[:12]
            check = check_variable(content, variable)
            candidate["matched_terms"] = check["matched"]
            if check["covered"]:
                candidate["state"] = "validated"
                candidate["reason"] = check["reason"]
            else:
                candidate["state"] = "extracted" if table else "accessible"
                candidate["reason"] = check["reason"]
            results.append(candidate)

    return results


def summarize(results: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Count the candidates per state."""
    counters: Dict[str, int] = {}
    for result in results:
        state = result.get("state", "rejected")
        counters[state] = counters.get(state, 0) + 1
    return counters
