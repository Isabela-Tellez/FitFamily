"""Competitor registry for FitFamily, built on official open data.

The registry joins three resources of the *Censo de Locales y Actividades*
(Ayuntamiento de Madrid, CC BY 4.0):

- **Locales**: official identifier, address, postal code and coordinates.
- **Actividades**: economic epigraph (declared activity) per local.
- **Locales con informacion de licencia**: administrative licence data.

Each official field is backed by its own :class:`~src.schemas.Evidence`, so
consumers can tell municipal data apart from commercial data taken from a
business website.

Design rules that this module enforces:

- The official local identifier is preserved so every record can be traced
  back to its source.
- Coordinates published as ``0,0`` (or outside the UTM 30N envelope of the
  Community of Madrid) are treated as **not available** and never used for
  distances or clustering.
- A missing licence record means "no information available", never "denied".
- Commercial names are only used when the page can be tied to the official
  address.
- ``has_playroom`` is only ``True``/``False`` with reliable evidence;
  otherwise it stays ``None`` (unknown).
- Prices keep the source wording: no monthly-to-annual conversion is done
  without stating the transformation.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from src.schemas import Competitor, Evidence
from src.tools.competitor_search import extract_prices

logger = logging.getLogger(__name__)

CENSUS_RESOURCE_BASE = (
    "https://datos.madrid.es/dataset/200085-0-censo-locales/resource/"
)
LOCALES_URL = CENSUS_RESOURCE_BASE + "200085-1-censo-locales/download/200085-1-censo-locales.csv"
ACTIVIDADES_URL = CENSUS_RESOURCE_BASE + "200085-5-censo-locales/download/200085-5-censo-locales.csv"
LICENCIAS_URL = CENSUS_RESOURCE_BASE + "200085-3-censo-locales/download/200085-3-censo-locales.csv"

CENSUS_LICENSE = "CC BY 4.0 - Ayuntamiento de Madrid"

# Canonical area -> barrio name as published by the census.
BARRIO_NAMES = {
    "el-cañaveral": "EL CAÑAVERAL",
    "el-canaveral": "EL CAÑAVERAL",
    "canaveral": "EL CAÑAVERAL",
}

# Epigraphs tracked by the registry, with a readable label.
TRACKED_EPIGRAPHS = {
    "931008": "Actividades de los gimnasios",
    "855002": "Ensenanza no reglada (deportiva y recreativa)",
    "931010": "Piscinas de comunidades de vecinos",
    "932001": "Centros de juegos o celebraciones infantiles (con cocina)",
    "932002": "Centros de juegos o celebraciones infantiles (sin cocina)",
}

# Terms that evidence a playroom / children area inside a business.
PLAYROOM_TERMS = (
    "ludoteca",
    "playroom",
    "zona infantil",
    "sala infantil",
    "espacio infantil",
    "area infantil",
    "area de juegos",
    "childcare",
    "kids club",
    "club infantil",
)

# Terms that must appear in the page of a competitor, by declared activity.
# They prevent binding a housing listing or an unrelated page to a premise.
# The lists are specific on purpose: generic words would let any shop through.
BUSINESS_TERMS = {
    "Actividades de los gimnasios": (
        "gimnasio", "fitness", "gimnasia", "entrenamiento", "wellness", "gym",
    ),
    "Ensenanza no reglada (deportiva y recreativa)": (
        "deporte", "fitness", "gimnasio", "entrenamiento", "wellness", "gym",
    ),
    "Piscinas de comunidades de vecinos": ("piscina",),
    "Centros de juegos o celebraciones infantiles (con cocina)": (
        "infantil", "ludoteca", "juegos infantiles", "ocio infantil",
    ),
    "Centros de juegos o celebraciones infantiles (sin cocina)": (
        "infantil", "ludoteca", "juegos infantiles", "ocio infantil",
    ),
}

# Activities that mean the premise now hosts a different business than the
# one declared in the census. The registry does not guess: the record is
# flagged instead of taking that page's data.
DIFFERENT_BUSINESS_MARKERS = (
    "barberia", "peluqueria", "peluquería", "restaurante", "cafeteria",
    "cafetería", "farmacia", "estanco", "panaderia", "panadería", "fruteria",
    "frutería", "ferreteria", "autoescuela", "lavanderia", "lavandería",
    "optic", "óptica", "dentista", "veterinario", "floristeria", "carniceria",
    "carnicería", "pescaderia", "pescadería", "papeleria", "papelería",
)

# Words that identify a housing or rental listing, not a business.
# A page is only treated as a housing listing when several of them appear,
# so a gym that mentions "alquiler de taquillas" is not discarded.
HOUSING_MARKERS = (
    "piso en", "pisos en", "se alquila", "alquiler de piso", "alquilo",
    "apartamento", "vivienda", "dormitorios", "habitacion", "m2", "m²",
    "atico", "chalet", "adosado", "duplex", "renta mensual", "alquiler de",
)


# Hosts where the content is user opinion, not the published price list of
# the establishment. Prices and services are not taken from them.
REVIEW_HOST_MARKERS = (
    "esopiniones", "forocoches", "tripadvisor", "yelp", "facebook", "instagram",
    "twitter", "wordpress", "blogspot", "youtube", "reddit", "foro", "foro.",
    "opinion", "reviews", "reseñas", "reseñas", "foursquare", "wikimapia",
)


def _is_review_page(url: str) -> bool:
    """True when the page collects opinions instead of publishing the offer."""
    host = urlsplit(url or "").netloc.lower()
    return any(marker in host for marker in REVIEW_HOST_MARKERS)


def _business_terms_for(competitor: Competitor) -> List[str]:
    """Terms the page of this competitor has to mention."""
    terms: List[str] = []
    for service in competitor.services:
        for key, values in BUSINESS_TERMS.items():
            if service == key:
                terms.extend(values)
    return sorted(set(terms))


def _is_housing_listing(title: str, body: str) -> bool:
    """True when the page sells or rents a flat instead of a business."""
    signals = set()
    for text in (title, body):
        normalized = _normalize_text(text)
        for marker in HOUSING_MARKERS:
            if marker in normalized:
                signals.add(marker)
    # Two or more independent signals: it is a housing listing.
    return len(signals) >= 2


def _mentions_business(title: str, body: str, terms: Sequence[str]) -> bool:
    """True when the page identifies the declared activity.

    The check is made on the title and the beginning of the page: a business
    names its activity there. A mention deeper in the page (for example a
    gym listed among the amenities of a building) is not enough.
    """
    if not terms:
        return True
    head = _normalize_text(f"{title} {body[:300]}")
    return any(term in head for term in terms)


def _hosts_different_business(title: str, body: str) -> Optional[str]:
    """Return the activity found in the page when it is not the declared one.

    The census is a snapshot: a premise can change its activity. When the page
    shows a clearly different business, its data is not taken.
    """
    head = _normalize_text(f"{title} {body[:300]}")
    for marker in DIFFERENT_BUSINESS_MARKERS:
        if marker in head:
            return marker
    return None

# UTM 30N envelope of the Community of Madrid (EPSG:25830).
_UTM_X_RANGE = (380_000.0, 800_000.0)
_UTM_Y_RANGE = (4_000_000.0, 4_600_000.0)

_EARTH_RADIUS_M = 6_371_000.0


# ── low level helpers ────────────────────────────────────────────────────

def _normalize_text(value: str) -> str:
    """Lowercase, strip accents and collapse spaces."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())


def read_census_rows(source: Any) -> Iterator[Dict[str, str]]:
    """Yield normalized rows of a census CSV.

    ``source`` may be a string, a binary file object or a text file object.
    Column names are stripped of quotes and of a leading UTF-8 BOM, because the
    official files carry one.
    """
    if isinstance(source, (bytes, bytearray)):
        source = io.TextIOWrapper(io.BytesIO(source), encoding="utf-8-sig", newline="")
    elif isinstance(source, str):
        source = io.StringIO(source.lstrip("﻿"))
    elif not hasattr(source, "read"):
        raise TypeError("source must be a string or a readable file object")

    reader = csv.DictReader(source, delimiter=";")
    if reader.fieldnames is None:
        return
    mapping = {}
    for name in reader.fieldnames:
        clean = (name or "").lstrip("﻿").strip()
        mapping[clean] = name
    for raw in reader:
        row = {}
        for clean, original in mapping.items():
            value = raw.get(original)
            # csv already removes the outer quotes. Stripping '"' here would
            # destroy legitimate quotes inside a value, such as the official
            # street name 'MARIO MORENO "CANTINFLAS"'.
            row[clean] = value.strip() if isinstance(value, str) else ""
        yield row


def _to_float(value: str) -> Optional[float]:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _is_usable_utm(x: Optional[float], y: Optional[float]) -> bool:
    """A coordinate pair is usable only inside the Madrid UTM 30N envelope."""
    if x is None or y is None:
        return False
    if x == 0.0 and y == 0.0:
        return False
    if not (_UTM_X_RANGE[0] <= x <= _UTM_X_RANGE[1]):
        return False
    if not (_UTM_Y_RANGE[0] <= y <= _UTM_Y_RANGE[1]):
        return False
    return True


def to_wgs84(x: Optional[float], y: Optional[float]) -> Optional[Dict[str, float]]:
    """Convert EPSG:25830 metres to WGS84 degrees.

    Returns ``None`` when the transformation is not available (pyproj is an
    optional dependency) or when the coordinates are not usable.
    """
    if not _is_usable_utm(x, y):
        return None
    try:
        from pyproj import Transformer
    except ImportError:
        logger.info("pyproj no disponible: se conservan solo las coordenadas UTM.")
        return None
    transformer = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return {"latitude": round(lat, 7), "longitude": round(lon, 7)}


def _clean_number(value: str) -> str:
    """Return the street number without the padding zeros of the registry."""
    number = (value or "").strip()
    if not number:
        return ""
    stripped = number.lstrip("0")
    return stripped or number


def _is_number_label(value: str) -> bool:
    """The registry stores 'NUM'/'N' as a separate field: it is not a name."""
    label = _normalize_text(value)
    return label in {"num", "n", "numero", "nº", "no", "n.o", "núm"}


def _address_from_record(record: Dict[str, str]) -> str:
    """Build a readable address without losing the original components."""
    street_parts = [
        record.get("clase_vial", ""),
        record.get("via", ""),
        record.get("nom_edificio", ""),
    ]
    street = " ".join(p for p in street_parts if p).strip()
    number = record.get("numero", "") or _clean_number(record.get("num_edificio", ""))
    if number:
        street = f"{street} {number}".strip()
    postal = record.get("cod_postal", "").strip()
    address = street
    if postal:
        address = f"{address}, {postal}" if address else postal
    return address


def _clean_trade_name(value: str) -> Optional[str]:
    """Return the registered trade name, or None when it is not informative."""
    name = (value or "").strip()
    if not name:
        return None
    if _normalize_text(name) in {"s/r", "s. r.", "sr", "-"}:
        return None
    return name


# ── parsers (pure functions over rows) ───────────────────────────────────

def parse_locales_records(rows: Iterable[Dict[str, str]],
                          barrio: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract the premises of a barrio from the 'Locales' resource."""
    records: List[Dict[str, str]] = []
    target = _normalize_text(barrio) if barrio else None
    for row in rows:
        row_barrio = _normalize_text(row.get("desc_barrio_local", ""))
        if target and row_barrio != target:
            continue
        records.append({
            "id_local": row.get("id_local", ""),
            "barrio": row.get("desc_barrio_local", ""),
            "situacion": row.get("desc_situacion_local", ""),
            "rotulo": row.get("rotulo", ""),
            "clase_vial": row.get("clase_vial_edificio", ""),
            "via": row.get("desc_vial_edificio", ""),
            "nom_edificio": "" if _is_number_label(row.get("nom_edificio", "")) else row.get("nom_edificio", ""),
            "num_edificio": row.get("num_edificio", ""),
            "numero": _clean_number(row.get("num_edificio", "")),
            "cal_edificio": "" if _is_number_label(row.get("cal_edificio", "")) else row.get("cal_edificio", ""),
            "cod_postal": row.get("cod_postal", ""),
            "seccion_censal": row.get("id_seccion_censal_local", "")
                              or row.get("desc_seccion_censal_local", ""),
            "x": row.get("coordenada_x_local", ""),
            "y": row.get("coordenada_y_local", ""),
        })
    return records


def parse_activity_records(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Extract the declared activity of every local from 'Actividades'."""
    records: List[Dict[str, str]] = []
    for row in rows:
        epigraph = row.get("id_epigrafe", "")
        if not epigraph:
            continue
        records.append({
            "id_local": row.get("id_local", ""),
            "id_epigrafe": epigraph,
            "desc_epigrafe": row.get("desc_epigrafe", ""),
            "situacion": row.get("desc_situacion_local", ""),
        })
    return records


def parse_license_records(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Extract the licence information of every local, keyed by local id.

    A premises can have several licence records. Keeping the last row of the
    file would show an arbitrary one, sometimes an old denied or ineffective
    licence. The most recent reference year (and, inside it, the most recent
    date) is kept instead. This is a presentation rule: it does not turn the
    licence into proof that the business is open or closed.
    """
    records: Dict[str, Dict[str, str]] = {}
    keys: Dict[str, tuple] = {}
    for row in rows:
        local_id = row.get("id_local", "")
        if not local_id:
            continue
        date = (row.get("Fecha_Dec_Lic", "") or "").strip()
        reference = row.get("ref_licencia", "") or ""
        match = re.search(r"/(\d{4})/", reference)
        year = int(match.group(1)) if match else 0
        if not year and re.match(r"\d{4}", date):
            year = int(date[:4])
        key = (year, date)
        if local_id in records and key < keys[local_id]:
            continue
        keys[local_id] = key
        records[local_id] = {
            "ref_licencia": reference,
            "tipo_licencia": row.get("desc_tipo_licencia", ""),
            "situacion_licencia": row.get("desc_tipo_situacion_licencia", ""),
            "fecha_licencia": date,
        }
    return records


# ── registry ─────────────────────────────────────────────────────────────

def build_competitor_registry(
    area_id: str = "el-cañaveral",
    locales_rows: Optional[Iterable[Dict[str, str]]] = None,
    activity_rows: Optional[Iterable[Dict[str, str]]] = None,
    license_rows: Optional[Iterable[Dict[str, str]]] = None,
    epigraphs: Optional[Sequence[str]] = None,
    only_open: bool = True,
    consulted_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Join the three official resources into a list of competitors.

    The returned competitors only contain **official** data. Commercial data
    (price, playroom) is added later by :func:`enrich_competitor_from_web`.

    Returns a dict with the competitors and counters describing what was
    processed, skipped or dropped.
    """
    barrio = BARRIO_NAMES.get(area_id.strip().lower())
    if barrio is None:
        raise ValueError(
            f"Area '{area_id}' sin nombre oficial de barrio conocido. "
            f"Disponibles: {sorted(BARRIO_NAMES)}"
        )
    wanted = set(epigraphs) if epigraphs else set(TRACKED_EPIGRAPHS)
    stamp = consulted_at or datetime.now(timezone.utc).isoformat()

    locales = parse_locales_records(locales_rows or [], barrio)
    open_locales = {
        rec["id_local"]: rec for rec in locales
        if not only_open or _normalize_text(rec["situacion"]) == "abierto"
    }

    activities: Dict[str, List[Dict[str, str]]] = {}
    for act in parse_activity_records(activity_rows or []):
        activities.setdefault(act["id_local"], []).append(act)

    licenses = parse_license_records(license_rows or [])

    competitors: List[Competitor] = []
    counters = {
        "locales_en_barrio": len(locales),
        "locales_abiertos": len(open_locales),
        "locales_con_actividad": 0,
        "locales_con_licencia": 0,
        "descartados_sin_actividad_relevante": 0,
        "sin_coordenadas": 0,
        "sin_nombre_comercial": 0,
        "locales_sin_actividad": 0,
    }

    for local_id, record in open_locales.items():
        acts = activities.get(local_id, [])
        if not acts:
            counters["locales_sin_actividad"] = counters.get("locales_sin_actividad", 0) + 1
            continue
        counters["locales_con_actividad"] += 1

        relevant = [a for a in acts if a["id_epigrafe"] in wanted]
        if not relevant:
            counters["descartados_sin_actividad_relevante"] += 1
            continue

        x = _to_float(record["x"])
        y = _to_float(record["y"])
        wgs84 = to_wgs84(x, y)
        latitude = wgs84["latitude"] if wgs84 else None
        longitude = wgs84["longitude"] if wgs84 else None
        if latitude is None:
            counters["sin_coordenadas"] += 1

        name = _clean_trade_name(record["rotulo"])
        if name is None:
            counters["sin_nombre_comercial"] += 1

        # Relevant activities first, the rest of the declared epigraphs after.
        relevant_labels = [TRACKED_EPIGRAPHS.get(a["id_epigrafe"], a["desc_epigrafe"])
                           for a in relevant]
        other_labels = [a["desc_epigrafe"] for a in acts
                        if a["id_epigrafe"] not in wanted and a["desc_epigrafe"]]
        services: List[str] = []
        for label in relevant_labels + other_labels:
            if label and label not in services:
                services.append(label)

        licence = licenses.get(local_id)
        license_status = None
        license_type = None
        license_date = None
        if licence:
            counters["locales_con_licencia"] += 1
            license_status = licence["situacion_licencia"] or None
            license_type = licence["tipo_licencia"] or None
            license_date = licence["fecha_licencia"] or None

        evidences: List[Evidence] = [
            Evidence(
                evidence_id=f"census_local_{local_id}",
                claim=(
                    f"Local {local_id} declarado en el Censo de Locales del Ayuntamiento de "
                    f"Madrid ({barrio}), situación '{record['situacion']}', "
                    f"dirección '{_address_from_record(record)}'."
                ),
                source_url=LOCALES_URL,
                snippet=(
                    f"rotulo={record['rotulo'] or 'S/R'} | "
                    f"via={record['via']} | num={record['num_edificio']} | "
                    f"cp={record['cod_postal']} | utm=({record['x']}, {record['y']})"
                ),
                date_observed=stamp,
                geo_scope=barrio,
                limitations=(
                    "Registro administrativo municipal: puede contener inconsistencias. "
                    "Las coordenadas se publican en EPSG:25830 (metros); la conversión a "
                    "WGS84 la realiza el módulo y queda documentada en la evidencia."
                ),
            ),
            Evidence(
                evidence_id=f"census_activity_{local_id}",
                claim=(
                    "Actividades declaradas: "
                    + ", ".join(relevant_labels)
                    + (f" (+{len(other_labels)} otras)" if other_labels else "")
                ),
                source_url=ACTIVIDADES_URL,
                snippet="; ".join(
                    f"{a['id_epigrafe']}={a['desc_epigrafe']}" for a in acts
                )[:500],
                date_observed=stamp,
                geo_scope=barrio,
                limitations=(
                    "Epígrafes de actividad económica declarados por el titular. "
                    "No equivalen a servicios verificados por el negocio."
                ),
            ),
        ]

        if licence and any(licence.values()):
            evidences.append(Evidence(
                evidence_id=f"census_license_{local_id}",
                claim=(
                    f"Licencia de actividad: {licence['tipo_licencia'] or 'tipo no indicado'}"
                    f" — {licence['situacion_licencia'] or 'situación no indicada'}"
                    f" (ref. {licence['ref_licencia'] or 'no indicada'})"
                    + (f", fecha {licence['fecha_licencia']}" if licence["fecha_licencia"] else "")
                ),
                source_url=LICENCIAS_URL,
                snippet=(
                    f"ref={licence['ref_licencia']} | tipo={licence['tipo_licencia']} | "
                    f"situacion={licence['situacion_licencia']} | fecha={licence['fecha_licencia']}"
                ),
                date_observed=licence["fecha_licencia"] or stamp,
                geo_scope=barrio,
                limitations=(
                    "Una situación administrativa no acredita que el negocio esté abierto ni "
                    "cerrado, ni que la actividad esté en curso. Si el local tiene varias "
                    "licencias, se muestra la referencia más reciente."
                ),
            ))
        else:
            evidences.append(Evidence(
                evidence_id=f"census_license_{local_id}",
                claim="Sin información de licencia disponible para este local en el fichero oficial.",
                source_url=LICENCIAS_URL,
                snippet="(sin registro de licencia)",
                date_observed=stamp,
                geo_scope=barrio,
                limitations=(
                    "La ausencia de registro significa 'no disponible', no 'denegada' ni "
                    "'sin efectos'."
                ),
            ))

        competitors.append(Competitor(
            identifier=local_id,
            name=name,
            location=_address_from_record(record) or None,
            postal_code=record["cod_postal"] or None,
            latitude=latitude,
            longitude=longitude,
            census_section=record["seccion_censal"] or None,
            services=services,
            tariffs=[],
            license_status=license_status,
            license_type=license_type,
            license_date=license_date,
            has_playroom=None,
            verification_status="verified",
            consulted_at=stamp,
            evidences=evidences,
        ))

    counters["competidores"] = len(competitors)
    return {"competitors": competitors, "counters": counters, "barrio": barrio}


# ── commercial enrichment ───────────────────────────────────────────────

_STREET_TYPE_WORDS = {
    "calle", "plaza", "avenida", "avda", "paseo", "camino", "ronda", "travesia",
    "travesía", "num", "n", "numero", "nº", "no", "n.o", "núm",
}


def _street_text(competitor: Competitor) -> str:
    """Street part of the official address, without the street type."""
    if not competitor.location:
        return ""
    street = competitor.location.split(",")[0]
    words = [w for w in street.split() if _normalize_text(w) not in _STREET_TYPE_WORDS]
    return " ".join(words)


_STREET_NUMBER_RE = re.compile(r"(?<!\d)(\d{1,4})\s*([A-Za-z])?\s*$")

_QUOTE_CHARS = "\"'“”«»‘’"


def _without_quotes(value: str) -> str:
    """Drop quoting marks so an official '"CANTINFLAS' matches 'Cantinflas'."""
    for char in _QUOTE_CHARS:
        value = value.replace(char, " ")
    return " ".join(value.split())


def _street_number(competitor: Competitor) -> Optional[str]:
    """House number of the official address, if the registry publishes one.

    The number is the last token before the postal code, for example
    ``CALLE CERRO DEL CAMPO 44, 28052`` -> ``44``. ``None`` means the
    registry has no usable number (``S/N``, ``BIS`` without digits...).
    """
    if not competitor.location:
        return None
    street = competitor.location.split(",")[0].strip()
    match = _STREET_NUMBER_RE.search(street)
    return match.group(1) if match else None


def _street_without_number(competitor: Competitor) -> str:
    """Street name without the house number nor the street type."""
    if not competitor.location:
        return ""
    street = competitor.location.split(",")[0]
    street = _STREET_NUMBER_RE.sub("", street).strip()
    words = [w for w in street.split() if _normalize_text(w) not in _STREET_TYPE_WORDS]
    return " ".join(words)


def _address_tokens(competitor: Competitor) -> List[str]:
    """Street tokens used to bind a web page to a premises."""
    normalized = _without_quotes(_normalize_text(_street_text(competitor)))
    if not normalized:
        return []
    tokens = [t for t in normalized.split() if len(t) > 3]
    if tokens:
        return tokens
    # Street with only short words: the whole street name has to appear.
    short = [t for t in normalized.split() if len(t) > 1]
    return [" ".join(short)] if short else []


def _number_appears(window: str, number: str) -> bool:
    """True when ``number`` appears in the window as a street number.

    A range such as ``42-46`` contains 44, so a page that publishes the whole
    building range is still bound to the premises. Longer numbers (postal
    codes, phone numbers) are never matched in part.
    """
    wanted = int(number)
    for match in re.finditer(
        r"(?<!\d)(\d{1,4})(?:\s*[-\u2013\u2014/]\s*(\d{1,4}))?(?!\d)", window
    ):
        low = int(match.group(1))
        high = int(match.group(2)) if match.group(2) else low
        if low <= wanted <= high:
            return True
    return False


def _page_matches_address(body_text: str, competitor: Competitor) -> bool:
    """True when the page is tied to the exact official address.

    The street name is not enough: the house number must appear next to it.
    Otherwise a page for number 46 on the same street would be taken as the
    premises at number 44. When the registry publishes no number, only the
    street can be checked.
    """
    normalized = _without_quotes(_normalize_text(body_text))
    tokens = _address_tokens(competitor)
    if not tokens:
        return False
    if not all(token in normalized for token in tokens):
        return False

    number = _street_number(competitor)
    if number is None:
        return True

    phrase = _without_quotes(_normalize_text(_street_without_number(competitor)))
    phrase_start = normalized.find(phrase) if phrase else -1
    if phrase_start >= 0:
        start = phrase_start + len(phrase)
    else:
        # Abbreviated street ("Cerro Campo 44"): use the last street token.
        first = min(normalized.find(token) for token in tokens)
        start = normalized.find(tokens[-1], first) + len(tokens[-1])
    return _number_appears(normalized[start:start + 45], number)


# Negation markers that turn a mention into "the service is not offered".
_NEGATION_PREFIXES = (
    "no dispone de", "no disponemos de", "no disponen de",
    "no dispone", "no disponemos", "no disponen",
    "no cuenta con", "no contamos con", "no cuentan con",
    "no cuenta", "no contamos", "no cuentan",
    "no tiene", "no tenemos", "no tienen",
    "no hay", "no ofrece", "no ofrecemos", "no ofrecen",
    "no incluye", "no incluimos", "no incluyen",
    "no existe", "no existen", "no se ofrece",
    "no se dispone", "carece de", "carente de", "ausencia de", "falta de",
    "ningun", "ninguna", "sin",
)

# Identity negations ("no es una ludoteca") are checked separately and only
# accept a very short distance to the term. Otherwise a sentence such as
# "no es un secreto que tenemos ludoteca" would be read as a negation.
_IDENTITY_NEGATION_PREFIXES = (
    "no es una", "no es un", "no es la", "no es el",
    "no somos una", "no somos un",
    "no se trata de una", "no se trata de un",
    "no constituye una", "no constituye un",
)

# Mentions of a playroom that belong to another business or to the public
# administration, not to the establishment being analysed.
_OTHER_BUSINESS_MARKERS = (
    "de al lado", "otro gimnasio", "otra empresa", "otro centro",
    "otros gimnasios", "otras empresas", "otros centros", "enfrente",
    "la competencia", "a diferencia de", "gimnasio cercano", "centro cercano",
)

_SELF_MARKERS = (
    "nuestro", "nuestra", "nuestros", "nuestras", "nosotros", "nosotras",
    "contamos", "disponemos", "tenemos", "ofrecemos", "incluimos",
)

_PUBLIC_PLAYROOM_MARKERS = (
    "municipal", "publica", "publico", "del ayuntamiento", "de la junta",
)

_NEGATION_SUFFIXES = (
    "no disponible", "no incluida", "no incluido", "no se ofrece",
    "no existe", "cerrada", "cerrado", "suspendida", "suspendido",
)

# If one of these appears between the negation and the term, the negation
# refers to another element of the sentence ("no hay sauna y sí ludoteca").
_NEGATION_BREAKERS = (" pero ", " sino ", " aunque ", " y ", ",", ";", ".")


def _is_negated(normalized: str, index: int, length: int) -> bool:
    """True when the mention at ``index`` is explicitly negated."""
    before = normalized[max(0, index - 70):index]
    before = (
        before.replace("sin embargo", " ")
        .replace("sin duda", " ")
        .replace("no es solo", " ")
        .replace("no es solamente", " ")
        .replace("no es unicamente", " ")
        .replace("no es una simple", " ")
        .replace("no es un simple", " ")
        .replace("no somos una simple", " ")
        .replace("no somos un simple", " ")
        .replace("no se trata de una simple", " ")
        .replace("no se trata de un simple", " ")
        .replace("no solo", " ")
    )
    after = normalized[index + length:index + length + 30]
    for prefix in _NEGATION_PREFIXES:
        position = before.rfind(prefix)
        if position < 0:
            continue
        # "sin" inside "sinergia" is not a negation.
        if position > 0 and before[position - 1].isalnum():
            continue
        end = position + len(prefix)
        if end < len(before) and before[end].isalnum():
            continue
        between = before[end:]
        if any(breaker in between for breaker in _NEGATION_BREAKERS):
            continue
        # "no dispone de una ludoteca": at most a few words between.
        if len(between.split()) <= 6:
            return True
    for prefix in _IDENTITY_NEGATION_PREFIXES:
        position = before.rfind(prefix)
        if position < 0:
            continue
        if position > 0 and before[position - 1].isalnum():
            continue
        end = position + len(prefix)
        if end < len(before) and before[end].isalnum():
            continue
        between = before[end:]
        if any(breaker in between for breaker in _NEGATION_BREAKERS):
            continue
        # Only an article or a short adjective can sit between the identity
        # negation and the term.
        if len(between.split()) <= 2:
            return True
    return any(suffix in after for suffix in _NEGATION_SUFFIXES)


def _refers_to_another_business(normalized: str, index: int, length: int) -> bool:
    """True when the mention belongs to another business or the administration.

    The window before the term usually carries its subject. When it names
    another establishment and the sentence does not speak in first person,
    the mention is not evidence about the competitor. A public playroom
    ("ludoteca municipal") is not the establishment's service either.
    """
    before = normalized[max(0, index - 90):index]
    after = normalized[index + length:index + length + 30]
    if any(marker in after for marker in _PUBLIC_PLAYROOM_MARKERS):
        return True
    if not any(marker in before for marker in _OTHER_BUSINESS_MARKERS):
        return False
    return not any(marker in before for marker in _SELF_MARKERS)


def _normalize_with_offsets(value: str) -> Tuple[str, List[int]]:
    """Normalize the text and keep, for each output char, its source index.

    Needed to return the real snippet from the original page when accents or
    line breaks make the normalized text shorter than the original one.
    """
    chars: List[str] = []
    offsets: List[int] = []
    pending_space = False
    for position, char in enumerate(value):
        decomposed = unicodedata.normalize("NFKD", char)
        base = "".join(c for c in decomposed if not unicodedata.combining(c))
        for piece in base.lower():
            if piece.isspace():
                pending_space = True
                continue
            if pending_space and chars:
                chars.append(" ")
                offsets.append(position)
            pending_space = False
            chars.append(piece)
            offsets.append(position)
    return "".join(chars), offsets


def detect_playroom(body_text: str) -> Optional[Dict[str, str]]:
    """Look for explicit references to a playroom / children area.

    Returns a dict with the matched term and the surrounding fragment, or
    ``None`` when there is no positive mention. A negated mention ("no
    dispone de ludoteca", "sin sala infantil", "ludoteca no disponible")
    is not evidence that the service is offered, so it never returns a match.

    The answer stays *unknown* rather than *False* because a page can negate
    the service of another subject (the neighbourhood, another centre), and
    the module does not guess. Mentions about another business or about a
    public playroom ("ludoteca municipal") are not evidence either.
    """
    if not body_text:
        return None
    normalized, offsets = _normalize_with_offsets(body_text)
    for term in PLAYROOM_TERMS:
        needle = _normalize_text(term)
        if not needle:
            continue
        start = 0
        while True:
            index = normalized.find(needle, start)
            if index < 0:
                break
            start = index + len(needle)
            if _is_negated(normalized, index, len(needle)):
                continue
            if _refers_to_another_business(normalized, index, len(needle)):
                continue
            source_start = offsets[index]
            source_end = offsets[min(index + len(needle) - 1, len(offsets) - 1)] + 1
            low = max(0, source_start - 120)
            high = min(len(body_text), source_end + 120)
            return {"term": term, "fragment": body_text[low:high].strip()}
    return None


def enrich_competitor_from_web(
    competitor: Competitor,
    max_results: int = 4,
    read_timeout: float = 30.0,
    search_callable=None,
    read_callable=None,
) -> Competitor:
    """Enrich a competitor with the data published on its own website.

    The official address is used to search, and a page is only accepted when
    its text mentions that address, so a chain website is never mixed with a
    single establishment.

    ``search_callable`` and ``read_callable`` can be injected for testing;
    by default the module uses ``search_web`` and ``read_web_page``.
    """
    from src.tools.competitor_search import search_web as default_search
    from src.tools.read_web_page import read_web_page as default_read

    search = search_callable or default_search
    read = read_callable or default_read

    address = competitor.location or ""
    street = _street_text(competitor)
    brand = competitor.name or ""
    query = " ".join(part for part in (brand, street, "El Cañaveral") if part)
    if not query.strip():
        return competitor

    try:
        results = search(query, max_results=max_results)
    except Exception as e:  # pragma: no cover - depends on the network
        logger.warning("Search failed for %s: %s", competitor.identifier, e)
        return competitor

    expected_terms = _business_terms_for(competitor)
    evidences = list(competitor.evidences)
    for result in results:
        url = getattr(result, "url", None)
        if not url:
            continue
        try:
            page = read(url)
        except Exception as e:
            logger.info("Could not read %s: %s", url, e)
            continue
        body = getattr(page, "body_text", "") or ""
        title = (getattr(page, "title", "") or "").strip()
        if not body or not _page_matches_address(body, competitor):
            logger.info("Page %s does not mention the official address, skipped.", url)
            continue
        if _is_housing_listing(title, body):
            logger.info("Page %s is a housing listing, skipped.", url)
            continue
        if not _mentions_business(title, body, expected_terms):
            logger.info("Page %s does not mention the declared activity, skipped.", url)
            continue
        other_activity = _hosts_different_business(title, body)
        if other_activity:
            logger.info("Page %s shows a different business (%s), skipped.", url, other_activity)
            if not [e for e in evidences if e.evidence_id == f"web_conflict_{competitor.identifier}"]:
                evidences.append(Evidence(
                    evidence_id=f"web_conflict_{competitor.identifier}",
                    claim=(
                        f"La web asociada a la direccion oficial muestra una actividad "
                        f"distinta a la declarada en el censo ('{other_activity}'); "
                        f"no se toman precios ni servicios de esa pagina."
                    ),
                    source_url=url,
                    snippet=(title or "")[:500],
                    date_observed=datetime.now(timezone.utc).isoformat(),
                    geo_scope=competitor.postal_code,
                    limitations=(
                        "El censo de locales es una fotografia: la actividad del local puede "
                        "haber cambiado. Se deja constancia de la discrepancia."
                    ),
                ))
            competitor.evidences = evidences
            continue
        if _is_review_page(url):
            logger.info("Page %s collects opinions, skipped.", url)
            continue

        stamp = datetime.now(timezone.utc).isoformat()
        seen_prices = set()
        for price in extract_prices(body):
            key = (price["value"], price["frequency"])
            if key in seen_prices:
                continue
            seen_prices.add(key)
            condition = price["fragment"]
            if price.get("is_range"):
                condition = (f"Rango desde {price.get('range_from')} euros. " + condition)
            evidences.append(Evidence(
                evidence_id=f"web_price_{competitor.identifier}_{len(evidences)}",
                claim=(
                    f"Precio publicado en la web del establecimiento: "
                    f"{price['value']} {price['unit']}"
                    + (f" ({price['frequency']})" if price["frequency"] else "")
                ),
                value=price["value"],
                unit=price["unit"],
                frequency=price["frequency"] or None,
                source_url=url,
                snippet=f"{title} | {price['fragment']}"[:500] if title else price["fragment"][:500],
                date_observed=stamp,
                geo_scope=competitor.postal_code,
                limitations=(
                    "Precio anunciado por el establecimiento en su web. No es un precio "
                    "registrado ni verificado con factura. La periodicidad se transcribe "
                    "tal como aparece; no se convierte a otra periodicidad."
                ),
            ))

        playroom = detect_playroom(body)
        if playroom:
            evidences.append(Evidence(
                evidence_id=f"web_playroom_{competitor.identifier}",
                claim=(
                    f"La web del establecimiento menciona '{playroom['term']}', "
                    f"por lo que se registra ludoteca/espacio infantil: sí."
                ),
                source_url=url,
                snippet=playroom["fragment"][:500],
                date_observed=stamp,
                geo_scope=competitor.postal_code,
                limitations=(
                    "Evidencia textual de la web del establecimiento. La web se ha vinculado "
                    "a la dirección oficial del local."
                ),
            ))

        competitor.evidences = evidences
        competitor.consulted_at = stamp
        if not competitor.name:
            web_title = (getattr(page, "title", "") or "").strip()
            if web_title:
                competitor.name = web_title
                evidences.append(Evidence(
                    evidence_id=f"web_name_{competitor.identifier}",
                    claim=(
                        f"El registro oficial no tiene nombre comercial ('S/R'); "
                        f"se toma '{web_title}' de la web del establecimiento."
                    ),
                    source_url=url,
                    snippet=web_title[:500],
                    date_observed=stamp,
                    geo_scope=competitor.postal_code,
                    limitations=(
                        "Nombre tomado de la web y no del registro municipal: se mantiene "
                        "distinguido del dato oficial."
                    ),
                ))
                competitor.evidences = evidences

        monthly = [t for t in competitor.tariffs
                   if t.get("frequency") == "monthly" and t.get("value") is not None]
        other = [t for t in competitor.tariffs if t not in monthly]
        new_tariffs = []
        for ev in evidences:
            if ev.evidence_id.startswith("web_price_") and ev.value is not None:
                new_tariffs.append({
                    "value": ev.value,
                    "unit": ev.unit or "euros",
                    "condition": (ev.snippet or "")[:200],
                    "frequency": ev.frequency or "",
                    "source_url": ev.source_url,
                })
        competitor.tariffs = new_tariffs + [t for t in other if t not in new_tariffs]
        if playroom:
            competitor.has_playroom = True
        elif competitor.has_playroom is None:
            # The page was reached but does not mention a playroom: still unknown.
            competitor.has_playroom = None
        break

    return competitor


# ── outputs ──────────────────────────────────────────────────────────────

def to_dataframe(competitors: Sequence[Competitor]):
    """Build the market analysis DataFrame expected by the analysis module.

    The first three columns are the ones ``summarize_competitors`` requires
    (``gym_name``, ``monthly_price_eur``, ``has_playroom``); the rest is
    extra context for the analysts.
    """
    import pandas as pd

    rows = []
    for competitor in competitors:
        monthly = None
        monthly_source = None
        for tariff in competitor.tariffs:
            if tariff.get("frequency") == "monthly" and tariff.get("value") is not None:
                monthly = tariff["value"]
                monthly_source = tariff.get("source_url")
                break
        rows.append({
            "gym_name": competitor.name or "desconocido",
            "monthly_price_eur": monthly,
            "has_playroom": competitor.has_playroom,
            "competitor_id": competitor.identifier,
            "address": competitor.location,
            "postal_code": competitor.postal_code,
            "latitude": competitor.latitude,
            "longitude": competitor.longitude,
            "census_section": competitor.census_section,
            "activities": "; ".join(competitor.services),
            "license_status": competitor.license_status,
            "license_type": competitor.license_type,
            "license_date": competitor.license_date,
            "price_source_url": monthly_source,
            "verification_status": competitor.verification_status,
        })
    return pd.DataFrame(rows, columns=[
        "gym_name", "monthly_price_eur", "has_playroom", "competitor_id",
        "address", "postal_code", "latitude", "longitude", "census_section",
        "activities", "license_status", "license_type", "license_date",
        "price_source_url", "verification_status",
    ])


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    from math import asin, cos, radians, sin, sqrt

    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = phi2 - phi1
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * asin(sqrt(a))


def competitors_within_radius(
    competitors: Sequence[Competitor],
    latitude: float,
    longitude: float,
    radius_m: float = 500.0,
) -> List[Dict[str, Any]]:
    """Return the competitors within ``radius_m`` of a point.

    Competitors without usable coordinates are never returned: the distance is
    unknown, not zero.
    """
    nearby: List[Dict[str, Any]] = []
    for competitor in competitors:
        if competitor.latitude is None or competitor.longitude is None:
            continue
        distance = haversine_meters(
            latitude, longitude, competitor.latitude, competitor.longitude
        )
        if distance <= radius_m:
            nearby.append({
                "competitor_id": competitor.identifier,
                "name": competitor.name,
                "distance_m": round(distance, 1),
            })
    nearby.sort(key=lambda item: item["distance_m"])
    return nearby


def registry_to_dict(competitors: Sequence[Competitor]) -> Dict[str, Any]:
    """Serialize the registry keeping every field and its evidence."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Censo de Locales y Actividades del Ayuntamiento de Madrid",
        "license": CENSUS_LICENSE,
        "competitors": [c.model_dump() for c in competitors],
    }
