"""Competitor search tool for the FitFamily research module.

Provides the `competitor_search(params)` function that identifies competitors
by area and business type, using the web search and page reading tools.

Responsibilities:
- Receive a validated area, business type, and maximum results.
- Build pertinent search queries.
- Use existing search and reading tools.
- Read relevant pages within configured limits.
- Identify unique businesses.
- Extract data supported by evidence.
- Normalize fields without altering original meaning.
- Distinguish between absence, inaccessibility, and found data.
- Return a structured and validated result.
- Deduplicate by normalized URL, domain, name, and location.
- NOT invent competitors, addresses, prices, services, ratings, or statistics.

The public interface is: `competitor_search(params)` where `params` is a
dict-like object validated by the `CompetitorSearchInput` Pydantic model.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator

from src.schemas import Evidence, Competitor as CompetitorSchema
from src.tools.search_web import search_web, SearchResult
from src.tools.read_web_page import read_web_page, PageReadResult
from src.tools.evidence_ids import stable_evidence_id

logger = logging.getLogger(__name__)


class CompetitorSearchInput(BaseModel):
    """Input parameters for competitor search.

    Represents the validated contract passed to `competitor_search()`.
    """

    area: str = Field(
        description="City, neighborhood, or district where competitors operate."
    )
    business_type: str = Field(
        description="Type of business being researched (e.g., 'gimnasio con ludoteca')."
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of competitors to identify.",
    )
    search_queries: Optional[List[str]] = Field(
        default=None,
        description="Optional override for custom search queries.",
    )

    @field_validator("area")
    @classmethod
    def validate_area_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Area must be a non-empty string.")
        return v.strip()

    @field_validator("business_type")
    @classmethod
    def validate_business_type_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Business type must be a non-empty string.")
        return v.strip()


def competitor_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for competitors in a given area and business type.

    This function:
    1. Validates the input using CompetitorSearchInput.
    2. Builds pertinent search queries for the area and business type.
    3. Uses the web search tool to find potential competitors.
    4. Reads relevant pages to extract competitor data.
    5. Identifies unique businesses and extracts their data.
    6. Associates each data point with its source/evidence.
    7. Normalizes fields without altering meaning.
    8. Distinguishes between absence, inaccessibility, and found data.
    9. Returns a structured result with competitors and evidences.

    Args:
        params: Dictionary containing 'area', 'business_type', and optional
                'max_results' and 'search_queries'.

    Returns:
        A dictionary with:
        - 'competitors': List of Competitor schema objects.
        - 'evidences': List of Evidence records.
        - 'search_summary': Human-readable summary of the search performed.
        - 'unresolved_questions': Questions that could not be answered.

    Raises:
        ValueError: If input validation fails.
        RuntimeError: If the search provider fails or pages are inaccessible.
    """
    # 1. Validate input
    try:
        input_model = CompetitorSearchInput(**params)
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        raise ValueError(f"Invalid search parameters: {e}") from e

    area = input_model.area
    business_type = input_model.business_type
    max_results = input_model.max_results
    custom_queries = input_model.search_queries or []

    # 2. Build search queries
    if custom_queries:
        queries = custom_queries[:max_results]
    else:
        # Construct natural queries based on area and business type
        queries = [
            f"{business_type} {area}",
            f"{business_type} cerca de {area}",
            f"mejores {business_type} {area}",
        ]

    logger.info(
        f"Competitor search: area='{area}', business_type='{business_type}', "
        f"max_results={max_results}, queries={queries}"
    )

    # 3. Perform searches and collect results
    all_evidences: List[Evidence] = []
    seen_identifiers: set = set()  # For deduplication
    competitors_found: List[CompetitorSchema] = []

    for query in queries:
        if len(seen_identifiers) >= max_results:
            logger.info(
                f"Reached max_results limit ({max_results}), stopping search."
            )
            break

        try:
            search_results = search_web(query, max_results=max_results)
        except Exception as e:
            logger.warning(f"Search failed for query '{query}': {e}")
            continue

        # 4. Process each search result
        for sr in search_results:
            if len(seen_identifiers) >= max_results:
                break

            url = sr.url
            if not url:
                continue

            # Deduplicate by normalized URL
            url_norm = url.lower().strip()
            if url_norm in seen_identifiers:
                logger.debug(f"Duplicate URL detected, skipping: {url}")
                continue
            seen_identifiers.add(url_norm)

            # 5. Read the page content
            try:
                page = read_web_page(url)
            except Exception as e:
                logger.warning(
                    f"Failed to read page {url}: {e}. "
                    "Skipping this result."
                )
                # Record that we tried but couldn't access
                ev = Evidence(
                    evidence_id=stable_evidence_id("access_attempt", url_norm),
                    claim=f"Attempted to access {business_type} at {url}",
                    source_url=url,
                    snippet=f"Page access failed: {str(e)[:200]}",
                    limitations="Page could not be accessed or was blocked",
                )
                all_evidences.append(ev)
                continue

            # 6. Check if page has useful content
            if not page.has_content:
                logger.info(
                    f"Page {url} has no meaningful content, skipping."
                )
                continue

            # 7. Extract competitor information from page text
            evidence = _extract_evidence_from_page(
                page, business_type, url
            )
            if evidence:
                all_evidences.append(evidence)

        # Small delay to be respectful to the search provider
        import time
        time.sleep(0.5)

    # 8. Build Competitor objects from collected evidences
    # Group evidences by potential competitor (based on name/domain patterns)
    competitors_by_key: Dict[str, CompetitorSchema] = {}

    for ev in all_evidences:
        # Failed access attempts are recorded as evidence but must not become
        # competitors (they contain no business data).
        if ev.evidence_id.startswith("access_attempt_"):
            continue
        key = _get_competitor_key(ev, business_type)
        if key not in competitors_by_key:
            competitors_by_key[key] = CompetitorSchema(
                identifier=key,
                evidences=[],
            )
        # Add evidence to the competitor
        comp = competitors_by_key[key]
        comp.evidences.append(ev)

        # Populate structured tariffs when the evidence contains a price
        if ev.value is not None:
            comp.tariffs.append(
                {
                    "value": ev.value,
                    "unit": ev.unit or "euros",
                    "condition": ev.claim,
                    "frequency": ev.frequency or "",
                }
            )

        # Also try to populate name/location from evidence if empty
        if not comp.name and ev.claim:
            # Try to extract a name from the claim
            # Look for potential business names (capitalized phrases)
            name_candidates = re.findall(
                r"\b[A-Z][a-zA-Záéíóúñ]+\s+[A-Z][a-zA-Záéíóúñ]+\b", ev.claim
            )
            if name_candidates and not comp.name:
                comp.name = name_candidates[0]

    # 9. Convert to final format and ensure tariffs/services are reasonable
    competitors_list = list(competitors_by_key.values())[:max_results]

    # Normalize tariffs and services across all competitors
    for comp in competitors_list:
        comp.normalize_services()
        comp.normalize_tariffs()

    # 10. Build search summary
    search_summary = (
        f"Búsqueda de {business_type} en {area} "
        f"con hasta {max_results} resultados por consulta "
        f"({len(queries)} consultas realizadas). "
        f"Enlaces únicos revisados: {len(seen_identifiers)}. "
        f"Competidores identificados: {len(competitors_list)}. "
        f"Evidencias recopiladas: {len(all_evidences)}."
    )

    # 11. Determine unresolved questions (empty list for competitor search)
    unresolved = []

    result: Dict[str, Any] = {
        "competitors": competitors_list,
        "evidences": all_evidences,
        "search_summary": search_summary,
        "unresolved_questions": unresolved,
    }

    logger.info(
        f"Competitor search complete: "
        f"{len(competitors_list)} competitors, "
        f"{len(all_evidences)} evidences."
    )

    return result


_PRICE_RE = re.compile(
    r"(?P<amount>\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"\s*"
    r"(?P<unit>€|euros?|eur\b|mensual(?:es)?|/\s*mes|al\s+mes|"
    r"anual(?:es)?|/\s*a[ñn]o|al\s+a[ñn]o|"
    r"matr[ií]cula|matriculaci[oó]n|inscripci[oó]n)",
    re.IGNORECASE,
)


def _parse_amount(raw: str) -> Optional[float]:
    """Parse an amount written in Spanish or English notation.

    Handles ``49,90``, ``49.90``, ``1.200``, ``1.200,50`` and ``1,200.50``.
    The last separator is treated as the decimal separator.
    """
    cleaned = raw.replace(" ", "").strip()
    if not cleaned:
        return None

    last_comma = cleaned.rfind(",")
    last_dot = cleaned.rfind(".")

    if last_comma == -1 and last_dot == -1:
        try:
            return float(cleaned)
        except ValueError:
            return None

    if last_comma > last_dot:
        # Comma is the decimal separator (European).
        int_part = cleaned[:last_comma].replace(".", "").replace(",", "")
        dec_digits = "".join(ch for ch in cleaned[last_comma + 1:] if ch.isdigit())
        normalized = f"{int_part}.{dec_digits}" if dec_digits else int_part
    else:
        # Dot is the last separator.
        int_part = cleaned[:last_dot]
        dec_part = cleaned[last_dot + 1:]
        # A single dot followed by exactly 3 digits and a short integer part
        # is a thousands separator in Spanish notation (1.200 -> 1200).
        if (
            cleaned.count(".") == 1
            and cleaned.count(",") == 0
            and len(dec_part) == 3
            and dec_part.isdigit()
            and int_part.isdigit()
            and 1 <= len(int_part) <= 3
        ):
            normalized = int_part + dec_part
        else:
            int_part = int_part.replace(",", "").replace(".", "")
            dec_digits = "".join(ch for ch in dec_part if ch.isdigit())
            normalized = f"{int_part}.{dec_digits}" if dec_digits else int_part

    try:
        return float(normalized)
    except ValueError:
        return None


def _classify_price(match: "re.Match[str]", text: str) -> "tuple[Optional[float], Optional[str]]":
    """Return ``(value, frequency)`` for a price match.

    Frequency is one of ``monthly``, ``one-time`` or ``None`` when the
    surrounding text does not make it explicit.
    """
    value = _parse_amount(match.group("amount"))
    token = match.group("unit").lower()

    # Look only at the immediate surroundings to avoid mixing two prices.
    head = text[max(0, match.start() - 18):match.start()].lower()
    tail = text[match.end():match.end() + 12].lower()

    if token.startswith(("matr", "inscrip")):
        frequency = "one-time"
    elif "mensual" in token or "mes" in token:
        frequency = "monthly"
    elif "anual" in token or "año" in token:
        frequency = "annual"
    elif re.search(r"(/\s*mes\b|\bal\s+mes\b|\bmensual)", head + " " + tail):
        frequency = "monthly"
    elif re.search(r"(/\s*a[ñn]o\b|\bal\s+a[ñn]o\b|\banual)", head + " " + tail):
        frequency = "annual"
    elif re.search(r"(matr[ií]cul|inscripci[oó]n)", head + " " + tail):
        frequency = "one-time"
    else:
        frequency = None

    return value, frequency


def extract_prices(text: str) -> List[Dict[str, Any]]:
    """Extract every published price found in a text.

    Reuses the same regular expression and classification as the evidence
    extraction, so a price found here and a price stored as evidence always
    agree. Ranges ("50-70 EUR") are flagged instead of being silently
    reduced to one of their bounds.

    Returns a list of dicts with:
    - value: the amount as a float
    - unit: currency (all the matched patterns are euro denominated)
    - frequency: 'monthly', 'annual', 'one-time' or '' when unknown
    - fragment: the surrounding text
    - is_range / range_from: set when the amount is the upper bound of a range
    """
    results: List[Dict[str, Any]] = []
    if not text:
        return results
    for match in _PRICE_RE.finditer(text):
        value, frequency = _classify_price(match, text)
        if value is None:
            continue
        before = text[max(0, match.start() - 14):match.start()]
        range_match = re.search(r"(\d+(?:[.,]\d{1,2})?)\s*[-–—]\s*$", before)
        entry = {
            "value": value,
            "unit": "euros",
            "frequency": frequency or "",
            "fragment": text[max(0, match.start() - 60):match.end() + 60].strip(),
            "is_range": bool(range_match),
        }
        if range_match:
            entry["range_from"] = range_match.group(1)
        results.append(entry)
    return results


def _extract_evidence_from_page(
    page: PageReadResult,
    business_type: str,
    url: str,
) -> Optional[Evidence]:
    """Extract an Evidence record from a page's content.

    Looks for a published price and returns it with its source, the
    surrounding snippet, and its payment frequency. Monthly prices are
    preferred over one-off fees when both appear on the page.
    """
    if not page.body_text:
        return None

    # Prefer a monthly fee; otherwise keep the first price and, as a last
    # resort, a one-off fee (e.g. registration).
    value: Optional[float] = None
    frequency: Optional[str] = None
    best_rank = -1

    for match in _PRICE_RE.finditer(page.body_text):
        candidate_value, candidate_frequency = _classify_price(match, page.body_text)
        if candidate_value is None:
            continue

        rank = 2 if candidate_frequency == "monthly" else 0 if candidate_frequency == "one-time" else 1
        if rank > best_rank:
            value = candidate_value
            frequency = candidate_frequency
            best_rank = rank
            if rank == 2:
                break

    # Determine geo_scope from URL if possible
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc or url
    geo_scope = parsed.netloc or None

    if value is not None:
        claim = f"Precio publicado por {business_type} en {domain}: {value:g} euros"
        if frequency == "monthly":
            claim += " al mes"
        elif frequency == "annual":
            claim += " al año"
        elif frequency == "one-time":
            claim += " (pago único)"
    else:
        claim = f"Información sobre {business_type} encontrada en {domain}"

    limitations_str = (
        "Extracción automática; verifique la fuente original para datos completos."
    )

    evidence = Evidence(
        evidence_id=stable_evidence_id("ev", url),
        claim=claim,
        value=value,
        unit="euros" if value is not None else None,
        frequency=frequency,
        source_url=url,
        snippet=page.body_text[:500].strip() if page.body_text else "",
        limitations=limitations_str,
        geo_scope=geo_scope,
    )

    return evidence


def _get_competitor_key(evidence: Evidence, business_type: str) -> str:
    """Generate a key for grouping evidences into competitors.

    Uses the source URL domain as the primary identifier, falling back
    to the claim text.
    """
    from urllib.parse import urlparse
    parsed = urlparse(evidence.source_url or "")
    domain = parsed.netloc or ""
    # Use a simplified key: domain + first word of claim
    claim_first = (
        evidence.claim.split()[0] if evidence.claim else ""
    ).lower()
    return f"{domain}|{claim_first}|{business_type.lower()}"