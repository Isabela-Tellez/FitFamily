"""Tests for the competitor registry (Persona 1 - Juan).

All tests use inline CSV samples: no network access and no cached files.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schemas import Competitor
from src.tools.competitor_registry import (
    build_competitor_registry,
    competitors_within_radius,
    detect_playroom,
    enrich_competitor_from_web,
    haversine_meters,
    parse_license_records,
    read_census_rows,
    registry_to_dict,
    to_dataframe,
)

LOCALES_CSV = (
    '"id_local";"desc_barrio_local";"desc_situacion_local";"rotulo";'
    '"clase_vial_edificio";"desc_vial_edificio";"nom_edificio";"num_edificio";'
    '"cal_edificio";"cod_postal";"desc_seccion_censal_local";'
    '"coordenada_x_local";"coordenada_y_local"\n'
    '"1";"EL CAÑAVERAL";"Abierto";"GIMNASIO EJEMPLO";"CALLE";"CERRO DEL CAMPO";"";"44";"";"28052";"19052";"453265.16";"4472862.91"\n'
    '"2";"EL CAÑAVERAL";"Abierto";"S/R";"AVENIDA";"DE LA PAZ";"";"2";"";"28052";"19053";"0.0";"0.0"\n'
    '"3";"VALDEBEBAS";"Abierto";"OTRO GIMNASIO";"CALLE";"OTRA";"";"1";"";"28052";"19099";"452000.0";"4473000.0"\n'
    '"4";"EL CAÑAVERAL";"Cerrado";"GIMNASIO CERRADO";"CALLE";"CERRADA";"";"9";"";"28052";"19054";"453000.0";"4472000.0"\n'
)

ACTIVIDADES_CSV = (
    '"id_local";"desc_barrio_local";"desc_situacion_local";"id_epigrafe";"desc_epigrafe"\n'
    '"1";"EL CAÑAVERAL";"Abierto";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
    '"1";"EL CAÑAVERAL";"Abierto";"472911";"COMERCIO AL POR MENOR"\n'
    '"2";"EL CAÑAVERAL";"Abierto";"932001";"CENTROS DE JUEGOS INFANTILES CON COCINA"\n'
    '"4";"EL CAÑAVERAL";"Cerrado";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
)

LICENCIAS_CSV = (
    '"id_local";"ref_licencia";"desc_tipo_licencia";'
    '"desc_tipo_situacion_licencia";"Fecha_Dec_Lic"\n'
    '"1";"LIC/2021/001";"Declaracion Responsable";"En tramitacion";"2021-09-17"\n'
)


def _registry():
    return build_competitor_registry(
        area_id="el-cañaveral",
        locales_rows=read_census_rows(LOCALES_CSV),
        activity_rows=read_census_rows(ACTIVIDADES_CSV),
        license_rows=read_census_rows(LICENCIAS_CSV),
    )


# --- carga y union de los tres recursos ---

def test_registry_joins_the_three_official_resources():
    registry = _registry()
    counters = registry["counters"]
    # 3 locales en el barrio (uno cerrado), 2 abiertos y con actividad relevante.
    assert counters["locales_en_barrio"] == 3
    assert counters["locales_abiertos"] == 2
    assert counters["competidores"] == 2
    ids = [c.identifier for c in registry["competitors"]]
    assert ids == ["1", "2"]


def test_registry_ignores_other_barrios_and_closed_premises():
    registry = _registry()
    identifiers = {c.identifier for c in registry["competitors"]}
    assert "3" not in identifiers  # otro barrio
    assert "4" not in identifiers  # cerrado


def test_registry_rejects_unknown_area():
    with pytest.raises(ValueError, match="sin nombre oficial"):
        build_competitor_registry(area_id="nowhere", locales_rows=read_census_rows(LOCALES_CSV))


# --- identificador unico y trazable ---

def test_identifiers_are_unique_and_traceable():
    registry = _registry()
    identifiers = [c.identifier for c in registry["competitors"]]
    assert len(identifiers) == len(set(identifiers))
    for competitor in registry["competitors"]:
        assert competitor.identifier
        # Cada campo oficial tiene su evidencia con URL.
        assert competitor.evidences
        assert all(ev.source_url for ev in competitor.evidences)


# --- direcciones ---

def test_address_is_normalised_and_keeps_the_original_values():
    registry = _registry()
    competitor = registry["competitors"][0]
    assert competitor.location.startswith("CALLE CERRO DEL CAMPO 44")
    assert "28052" in competitor.location
    assert competitor.postal_code == "28052"
    # Los componentes originales quedan en la evidencia.
    census = [e for e in competitor.evidences if e.evidence_id.startswith("census_local_")][0]
    assert "CERRO DEL CAMPO" in census.snippet
    assert "453265.16" in census.snippet


def test_trade_name_is_not_invented_when_the_registry_has_none():
    registry = _registry()
    without_name = [c for c in registry["competitors"] if c.identifier == "2"][0]
    assert without_name.name is None


# --- coordenadas ---

def test_zero_coordinates_are_treated_as_unavailable():
    registry = _registry()
    without_coords = [c for c in registry["competitors"] if c.identifier == "2"][0]
    assert without_coords.latitude is None
    assert without_coords.longitude is None
    # Y no se usan para el analisis espacial.
    assert competitors_within_radius(registry["competitors"], 40.4, -3.55, 5000) == [
        item for item in competitors_within_radius(registry["competitors"], 40.4, -3.55, 5000)
        if item["competitor_id"] != "2"
    ]


def test_valid_coordinates_are_converted_to_wgs84():
    pytest.importorskip(
        "pyproj",
        reason="pyproj es opcional; sin él las coordenadas quedan sin convertir",
    )
    registry = _registry()
    competitor = registry["competitors"][0]
    assert competitor.latitude is not None
    assert competitor.longitude is not None
    assert 40.3 < competitor.latitude < 40.5
    assert -3.7 < competitor.longitude < -3.4


# --- licencias ---

def test_missing_licence_is_reported_as_unavailable_not_denied():
    registry = _registry()
    competitor = [c for c in registry["competitors"] if c.identifier == "2"][0]
    assert competitor.license_status is None
    assert competitor.license_type is None
    evidence = [e for e in competitor.evidences if e.evidence_id.startswith("census_license_")][0]
    assert "licencia" in evidence.claim.lower()
    assert "no disponible" in evidence.limitations.lower()


def test_licence_status_is_kept_verbatim():
    registry = _registry()
    competitor = registry["competitors"][0]
    assert competitor.license_type == "Declaracion Responsable"
    assert competitor.license_status == "En tramitacion"
    assert competitor.license_date == "2021-09-17"
    evidence = [e for e in competitor.evidences if e.evidence_id.startswith("census_license_")][0]
    assert "no acredita" in evidence.limitations


# --- precios ---

def test_prices_are_extracted_with_their_periodicity():
    from src.tools.competitor_search import extract_prices
    prices = extract_prices("Cuota mensual 49,90 euros. Matricula 25 euros.")
    values = {(p["value"], p["frequency"]) for p in prices}
    assert (49.9, "monthly") in values
    assert (25.0, "one-time") in values


def test_ranges_are_flagged_instead_of_being_reduced():
    from src.tools.competitor_search import extract_prices
    prices = extract_prices("Cuotas de 40-70 euros al mes")
    assert prices
    assert prices[0]["is_range"] is True
    assert prices[0]["range_from"] == "40"


def test_price_without_periodicity_stays_unknown():
    from src.tools.competitor_search import extract_prices
    prices = extract_prices("Precio 30 euros")
    assert prices[0]["value"] == 30.0
    assert prices[0]["frequency"] == ""


# --- ludoteca ---

def test_playroom_detection_returns_true_false_or_unknown():
    assert detect_playroom("Contamos con ludoteca infantil en la zona de juegos")
    assert detect_playroom("Disposed de una sala infantil para los mas pequenos")
    # Si la web no lo menciona, la respuesta sigue siendo desconocida.
    assert detect_playroom("Gimnasio con salas de máquinas y sauna") is None


def test_a_negated_playroom_is_not_a_positive_mention():
    """'No dispone de ludoteca' must never be read as offering the service."""
    assert detect_playroom("El gimnasio no dispone de ludoteca") is None
    assert detect_playroom("No contamos con zona infantil") is None
    assert detect_playroom("No hay sala infantil en el centro") is None
    assert detect_playroom("Sin ludoteca") is None
    assert detect_playroom("Ludoteca no disponible") is None
    assert detect_playroom("Carece de area de juegos") is None
    # Plural and long formulations are also negations.
    assert detect_playroom("En el centro no disponen de ludoteca") is None
    assert detect_playroom("No disponemos en nuestras instalaciones de una ludoteca") is None
    assert detect_playroom("No ofrecen servicio de ludoteca") is None


def test_the_negation_stops_at_the_end_of_the_clause():
    """A negation of another service does not hide a real playroom."""
    assert detect_playroom("No disponemos de sauna, pero tenemos ludoteca")
    assert detect_playroom("Sin embargo, contamos con ludoteca infantil")
    assert detect_playroom("No solo hay ludoteca: también zona infantil")
    # 'sin' inside another word is not a negation.
    assert detect_playroom("Sinergia con ludoteca para socios")


def test_identity_negations_are_not_offers():
    """'No es una ludoteca' describes what the business is not."""
    assert detect_playroom("No es una ludoteca, es una guardería") is None
    assert detect_playroom("No somos una ludoteca") is None
    assert detect_playroom("No se trata de una ludoteca") is None
    assert detect_playroom("No constituye una ludoteca") is None
    assert detect_playroom("No es un centro con ludoteca") is None
    # 'No es solo una ludoteca' does describe an offered service.
    assert detect_playroom("No es solo una ludoteca: también hay zona infantil")


def test_identity_negation_does_not_hide_a_positive_claim():
    assert detect_playroom("No es la primera vez que ofrecemos ludoteca")
    assert detect_playroom("No es un secreto que tenemos ludoteca")
    assert detect_playroom("No es una simple ludoteca")
    assert detect_playroom("No se trata de una simple ludoteca")


def test_mentions_of_other_businesses_are_not_attributed_to_the_competitor():
    assert detect_playroom("El gimnasio de al lado tiene ludoteca") is None
    assert detect_playroom("Enfrente hay un centro con ludoteca") is None
    assert detect_playroom("Otro gimnasio ofrece ludoteca") is None
    assert detect_playroom("La competencia cuenta con zona infantil") is None
    # First person keeps the mention about the establishment.
    assert detect_playroom("A diferencia de otros gimnasios, nosotros contamos con ludoteca")
    assert detect_playroom("Nuestro gimnasio tiene ludoteca; el de al lado también")


def test_public_playgrounds_and_municipal_playrooms_are_not_the_service():
    assert detect_playroom("Junto al gimnasio hay un parque infantil") is None
    assert detect_playroom("La ludoteca municipal está enfrente") is None
    assert detect_playroom("Zona infantil pública del ayuntamiento") is None


def test_has_playroom_is_unknown_without_evidence():
    registry = _registry()
    assert all(c.has_playroom is None for c in registry["competitors"])


# --- enriquecimiento web ---

class _FakeResult:
    def __init__(self, url):
        self.url = url
        self.title = "Gimnasio Ejemplo"


class _FakePage:
    def __init__(self, body):
        self.body_text = body
        self.title = "Gimnasio Ejemplo"


def test_web_enrichment_requires_the_address_to_match():
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo 44, El Cañaveral. "
            "Cuota mensual 49,90 euros. Tenemos ludoteca infantil.")
    pages = {"https://gym.example": _FakePage(body)}

    def fake_search(query, max_results=4):
        return [_FakeResult("https://gym.example")]

    def fake_read(url):
        return pages[url]

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    monthly = [t for t in enriched.tariffs if t.get("frequency") == "monthly"]
    assert monthly and monthly[0]["value"] == 49.9
    assert monthly[0]["source_url"] == "https://gym.example"
    assert enriched.has_playroom is True
    price_evidence = [e for e in enriched.evidences if e.evidence_id.startswith("web_price_")]
    assert price_evidence and price_evidence[0].source_url == "https://gym.example"


def test_web_enrichment_rejects_a_page_from_another_establishment():
    competitor = _registry()["competitors"][0]
    body = "Gimnasio de otra ciudad, calle de la Alameda 10. Cuota 30 euros."

    def fake_search(query, max_results=4):
        return [_FakeResult("https://otro.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    assert enriched.has_playroom is None


def test_web_enrichment_rejects_another_number_on_the_same_street():
    """Number 46 is a different establishment than number 44."""
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo 46, El Cañaveral. "
            "Cuota mensual 39,90 euros.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://otro-numero.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    assert not [e for e in enriched.evidences if e.evidence_id.startswith("web_price_")]


def test_web_enrichment_rejects_a_street_without_house_number():
    """Without the number the page cannot be tied to the premises."""
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo, El Cañaveral. "
            "Cuota mensual 39,90 euros.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://sin-numero.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []


def test_web_enrichment_accepts_a_range_that_includes_the_premises():
    """A page publishing '42-46' covers the premises at number 44."""
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo 42-46, El Cañaveral. "
            "Cuota mensual 49,90 euros.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://gym.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert [t for t in enriched.tariffs if t.get("frequency") == "monthly"]


def test_quoted_official_street_matches_the_page_without_quotes():
    """'MARIO MORENO "CANTINFLAS' must match 'Mario Moreno Cantinflas'."""
    from src.tools.competitor_registry import _page_matches_address

    competitor = Competitor(
        identifier="270562257",
        name="GIMNASIO EJEMPLO",
        location='CALLE MARIO MORENO "CANTINFLAS 64, 28052',
    )
    assert _page_matches_address(
        "Gimnasio Ejemplo, calle Mario Moreno Cantinflas 64, El Canaveral", competitor
    )
    assert _page_matches_address(
        'Gimnasio Ejemplo, calle Mario Moreno "Cantinflas" 64, El Canaveral', competitor
    )
    assert not _page_matches_address(
        "Gimnasio Ejemplo, calle Mario Moreno Cantinflas 66, El Canaveral", competitor
    )


def test_a_negated_playroom_on_the_page_does_not_mark_the_service():
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo 44, El Cañaveral. "
            "Cuota mensual 49,90 euros. No dispone de ludoteca.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://gym.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.has_playroom is None
    assert not [e for e in enriched.evidences if e.evidence_id.startswith("web_playroom_")]
    # The price is still usable: the page is the right establishment.
    assert [t for t in enriched.tariffs if t.get("frequency") == "monthly"]


def test_another_business_playroom_on_the_page_is_not_attributed():
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo 44, El Cañaveral. "
            "Cuota mensual 49,90 euros. El gimnasio de al lado tiene ludoteca.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://gym.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.has_playroom is None
    assert not [e for e in enriched.evidences if e.evidence_id.startswith("web_playroom_")]


# --- compatibilidad con los agentes existentes ---

def test_address_omits_the_number_label_and_the_padding_zeros():
    """'NUM' is a label of the registry and the number is padded with zeros."""
    registry = _registry()
    competitor = registry["competitors"][0]
    assert "NUM" not in competitor.location.upper()
    assert "44" in competitor.location
    assert "000044" not in competitor.location


def test_housing_listing_is_not_taken_as_the_business():
    """A rental listing of a flat is not the establishment."""
    competitor = _registry()["competitors"][0]
    body = ("Piso en calle Cerro del Campo 44, El Cañaveral. Alquiler de 1.350 euros al mes, "
            "3 dormitorios, 85 m2, vivienda con garaje. La piscina y el gimnasio son zonas comunes.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://kelify.example/piso")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    assert enriched.has_playroom is None
    assert not [e for e in enriched.evidences if e.evidence_id.startswith("web_")]


def test_page_without_the_declared_activity_is_rejected():
    """A page that does not mention the declared activity is discarded."""
    competitor = _registry()["competitors"][0]
    body = ("Tienda de-Moño en calle Cerro del Campo 44. Rebajas del 30% en(print) "
            "accesorios y ropa de marca.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://tienda.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    assert enriched.has_playroom is None


def test_repeated_prices_are_not_duplicated():
    competitor = _registry()["competitors"][0]
    body = ("Gimnasio Ejemplo, calle Cerro del Campo 44, El Cañaveral. "
            "Cuota mensual 49,90 euros al mes. 49,90 euros al mes.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://gym.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    prices = [e for e in enriched.evidences if e.evidence_id.startswith("web_price_")]
    assert len(prices) == 1
    assert len(enriched.tariffs) == 1


def test_review_pages_are_not_used_as_price_evidence():
    """Prices quoted by users in a forum are not the published price list."""
    competitor = _registry()["competitors"][0]
    body = ("Energia Fitness el Canaveral, C. Cerro del Campo, 42-46 | todos lados. "
            "50 euros de matricula que son regalados. Vaya robo!")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://esopiniones.com/madrid/energie-fitness")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    assert not [e for e in enriched.evidences if e.evidence_id.startswith("web_price_")]


def test_business_activity_must_appear_in_the_head_of_the_page():
    """A gym mentioned deep in the page is not enough to bind it."""
    competitor = _registry()["competitors"][0]
    body = ("Shelby's Barbershop El Canaveral. Reserve citas. 15,50 euros por corte. "
            + "Recomendado por clientes del gimnasio de al lado. " * 40)

    def fake_search(query, max_results=4):
        return [_FakeResult("https://booksy.com/es-es/shelbys")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    assert enriched.has_playroom is None


def test_official_name_is_kept_and_web_name_is_flagged():
    """The official trade name wins; a web name is only used when there is none."""
    registry = _registry()
    named = registry["competitors"][0]
    body = "Gimnasio Ejemplo, calle Cerro del Campo 44. Cuota mensual 49,90 euros."

    def fake_search(query, max_results=4):
        return [_FakeResult("https://gym.example")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(named, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.name == "GIMNASIO EJEMPLO"


def test_a_different_business_at_the_same_address_is_flagged_not_used():
    """A premise can change its activity: the discrepancy is recorded."""
    competitor = _registry()["competitors"][0]
    body = ("Shelby's Barbershop El Canaveral. Peluqueria en calle Cerro del Campo 44. "
            "Corte caballero 15,50 euros. Reserva cita online.")

    def fake_search(query, max_results=4):
        return [_FakeResult("https://booksy.example/shelbys")]

    def fake_read(url):
        return _FakePage(body)

    enriched = enrich_competitor_from_web(competitor, search_callable=fake_search,
                                          read_callable=fake_read)
    assert enriched.tariffs == []
    conflicts = [e for e in enriched.evidences if e.evidence_id.startswith("web_conflict_")]
    assert conflicts
    assert "actividad" in conflicts[0].claim.lower()


def test_registry_is_compatible_with_the_existing_contract():
    from src.schemas import ResearchResult
    registry = _registry()
    result = ResearchResult(competitors=registry["competitors"])
    assert len(result.competitors) == 2
    # El agente redactor debe poder leer los registros sin cambios.
    from src.agents.writer_agent import WriterAgent
    from src.schemas import ResearchBrief
    brief = ResearchBrief(business_type="gimnasio con ludoteca", location="Madrid",
                          study_area="El Cañaveral")
    draft = WriterAgent().create_draft(brief, result)
    assert draft.title
    assert any("GIMNASIO EJEMPLO" in section for section in draft.sections)
    assert draft.sources  # el censo aporta URL de evidencia


def test_dataframe_is_usable_by_the_market_analysis_module():
    from src.analysis.market_analysis import summarize_competitors
    registry = _registry()
    frame = to_dataframe(registry["competitors"])
    for column in ("gym_name", "monthly_price_eur", "has_playroom"):
        assert column in frame.columns
    summary = summarize_competitors(frame)
    assert summary["competitor_count"] == 2
    # Sin precios ni evidencia de ludoteca, nada se inventa.
    assert summary["known_price_count"] == 0
    assert summary["average_monthly_price_eur"] is None
    assert summary["playroom_unknown_count"] == 2


# --- salida y espacial ---

def test_registry_serialisation_keeps_every_field():
    registry = _registry()
    payload = registry_to_dict(registry["competitors"])
    assert payload["competitors"]
    first = payload["competitors"][0]
    for key in ("identifier", "location", "postal_code", "latitude", "longitude",
                "services", "license_status", "has_playroom", "verification_status",
                "evidences"):
        assert key in first
    assert first["evidences"]


def test_haversine_and_radius_filter():
    # Dos puntos a ~111 m de latitud (~11,1 km).
    distance = haversine_meters(40.4000, -3.5500, 40.5000, -3.5500)
    assert 11000 < distance < 11200
    competitor = Competitor(identifier="x", name="X", latitude=40.4001, longitude=-3.5500)
    nearby = competitors_within_radius([competitor], 40.4000, -3.5500, 500)
    assert nearby and nearby[0]["competitor_id"] == "x"
    assert competitors_within_radius([competitor], 41.0, -3.55, 500) == []


def test_license_parser_keeps_raw_values():
    records = parse_license_records(read_census_rows(LICENCIAS_CSV))
    assert records["1"]["situacion_licencia"] == "En tramitacion"
    assert records["1"]["fecha_licencia"] == "2021-09-17"


def test_read_census_rows_preserves_quotes_inside_a_value():
    """The official street 'MARIO MORENO "CANTINFLAS"' keeps both quotes."""
    csv_text = (
        '"id_local";"desc_barrio_local";"desc_situacion_local";"rotulo";'
        '"clase_vial_edificio";"desc_vial_edificio";"nom_edificio";"num_edificio";'
        '"cal_edificio";"cod_postal";"desc_seccion_censal_local";'
        '"coordenada_x_local";"coordenada_y_local"\n'
        '"270562257";"EL CAÑAVERAL";"Abierto";"PISCINA";"CALLE";'
        '"MARIO MORENO ""CANTINFLAS""";"";"64";"";"28052";"19052";"0.0";"0.0"\n'
    )
    row = next(read_census_rows(csv_text))
    assert row["desc_vial_edificio"] == 'MARIO MORENO "CANTINFLAS"'
    assert row["id_local"] == "270562257"


def test_license_parser_keeps_the_most_recent_reference():
    csv_text = (
        '"id_local";"ref_licencia";"desc_tipo_licencia";'
        '"desc_tipo_situacion_licencia";"Fecha_Dec_Lic"\n'
        '"9";"500/2022/06998";"Declaracion Responsable";"En tramitacion";"2022-09-15"\n'
        '"9";"350/2024/28192";"Declaracion Responsable";"Favorable no inspeccionada";"2025-08-26"\n'
        '"9";"500/2022/06773";"";"Denegada";"2023-02-22"\n'
    )
    records = parse_license_records(read_census_rows(csv_text))
    assert records["9"]["ref_licencia"] == "350/2024/28192"
    assert records["9"]["situacion_licencia"] == "Favorable no inspeccionada"


def test_newer_undated_reference_wins_over_an_older_dated_one():
    csv_text = (
        '"id_local";"ref_licencia";"desc_tipo_licencia";'
        '"desc_tipo_situacion_licencia";"Fecha_Dec_Lic"\n'
        '"9";"350/2023/01611";"Declaracion Responsable";"Ineficaz o sin efectos";"2024-11-04"\n'
        '"9";"350/2025/11808";"Declaracion Responsable";"Presentada (pendiente de comprobacion)";""\n'
    )
    records = parse_license_records(read_census_rows(csv_text))
    assert records["9"]["ref_licencia"] == "350/2025/11808"
    assert records["9"]["situacion_licencia"].startswith("Presentada")


def test_a_denied_licence_does_not_remove_an_open_premise():
    """A licence state is not proof that the business is closed."""
    licencias = (
        '"id_local";"ref_licencia";"desc_tipo_licencia";'
        '"desc_tipo_situacion_licencia";"Fecha_Dec_Lic"\n'
        '"1";"500/2024/00001";"Declaracion Responsable";"Denegada";"2024-01-01"\n'
    )
    registry = build_competitor_registry(
        area_id="el-cañaveral",
        locales_rows=read_census_rows(LOCALES_CSV),
        activity_rows=read_census_rows(ACTIVIDADES_CSV),
        license_rows=read_census_rows(licencias),
    )
    competitor = next(c for c in registry["competitors"] if c.identifier == "1")
    assert competitor.license_status == "Denegada"
    assert "operating_status" not in competitor.model_dump()
    licence_evidence = next(
        e for e in competitor.evidences if e.evidence_id.startswith("census_license_")
    )
    assert "no acredita" in licence_evidence.limitations
