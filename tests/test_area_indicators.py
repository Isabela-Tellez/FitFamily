"""Tests for the equipment/ocio and households-with-minors indicators.

All tests use controlled inline data: no network access.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp.server import (
    parse_actividades_csv,
    refresh_gyms_count,
    parse_household_composition_rows,
    refresh_households_with_minors,
    _STATISTICS_DATA,
)

ACTIVIDADES_CSV = (
    '"id_local";"desc_barrio_local";"desc_situacion_local";"id_epigrafe";"desc_epigrafe"\n'
    '"1";"EL CAÑAVERAL";"Abierto";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
    '"2";"EL CAÑAVERAL";"Abierto";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
    '"3";"EL CAÑAVERAL";"Abierto";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
    '"4";"EL CAÑAVERAL";"Cerrado";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
    '"5";"EL CAÑAVERAL";"Abierto";"855002";"ENSEÑANZA NO REGLADA (DEPORTIVA)"\n'
    '"6";"EL CAÑAVERAL";"Abierto";"932001";"CENTROS DE JUEGOS INFANTILES CON COCINA"\n'
    '"7";"EL CAÑAVERAL";"Abierto";"932002";"CENTROS DE JUEGOS INFANTILES SIN COCINA"\n'
    '"8";"EL CAÑAVERAL";"Abierto";"931010";"PISCINAS DE COMUNIDADES DE VECINOS"\n'
    '"9";"VALDEBEBAS";"Abierto";"931008";"ACTIVIDADES DE LOS GIMNASIOS"\n'
)


def _composition_rows(sections):
    """Build a minimal 'Composicion del hogar' sheet."""
    header = ("Distrito / Sección", None, "Total", "Composición del hogar (tipo)")
    labels = (None, None, None,
              "Dos adultos y un menor",
              "Dos adultos de 16 a 64 años, sin menores",
              "Otro hogar de tres adultos, con o sin menores",
              "Una mujer sola de 16 a 64 años ")
    rows = [
        ("Ciudad de Madrid",),
        ("Explotación estadística",),
        (),
        ("2. Hogares por Composición del hogar según Distrito y Sección",),
        header,
        labels,
    ]
    for code, total, with_minors, without, ambiguous, neither in sections:
        rows.append((None, code, total, with_minors, without, ambiguous, neither))
    return rows


SECTIONS = [
    (19052, 100, 10, 40, 20, 30),
    (19053, 120, 12, 48, 24, 36),
]


# --- actividades ---

def test_parse_actividades_counts_distinct_open_premises():
    r = parse_actividades_csv(ACTIVIDADES_CSV, "EL CAÑAVERAL")
    assert r["status"] == "ok"
    # 3 open locales with 931008 (the closed one is excluded, no duplicate rows)
    assert r["counts"]["931008"] == 3
    # Other barrio is ignored
    assert r["total_open_premises"] == 7
    assert r["rows_for_barrio"] == 8


def test_parse_actividades_requires_columns():
    r = parse_actividades_csv('"a";"b"\n"1";"2"\n', "EL CAÑAVERAL")
    assert r["status"] == "error"
    assert "Columnas requeridas" in r["error"]


def test_parse_actividades_empty_csv():
    r = parse_actividades_csv("", "EL CAÑAVERAL")
    assert r["status"] == "error"


def test_parse_actividades_handles_utf8_bom_header():
    """The official CSV may be read with a BOM on the first column name."""
    csv_bom = "﻿" + ACTIVIDADES_CSV
    r = parse_actividades_csv(csv_bom, "EL CAÑAVERAL")
    assert r["status"] == "ok"
    assert r["counts"]["931008"] == 3


def test_parse_locales_handles_utf8_bom_header():
    """Same BOM tolerance is required for the 'Locales' file."""
    from src.mcp.server import parse_locales_csv
    csv_text = (
        "﻿" + '"id_local";"desc_barrio_local";"desc_situacion_local"\n'
        '"1";"EL CAÑAVERAL";"Abierto"\n'
    )
    r = parse_locales_csv(csv_text, "EL CAÑAVERAL")
    assert r["status"] == "ok"
    assert r["count"] == 1


def test_refresh_gyms_count_sums_epigraphs_of_same_indicator():
    """932001 and 932002 both feed childrens_play_venues and must be summed."""
    store = {"indicators": {}}
    res = refresh_gyms_count("el-cañaveral", csv_text=ACTIVIDADES_CSV, store=store)
    assert res["status"] == "ok"
    ind = store["indicators"]
    assert ind["gyms_registered"]["value"] == 3
    assert ind["sports_recreation_venues"]["value"] == 1
    assert ind["childrens_play_venues"]["value"] == 2   # 1 + 1
    assert ind["community_pools"]["value"] == 1
    assert ind["gyms_registered"]["verification_status"] == "verified"


def test_refresh_gyms_count_unsupported_area():
    res = refresh_gyms_count("madrid", csv_text=ACTIVIDADES_CSV, store={"indicators": {}})
    assert res["status"] == "unsupported"


def test_refresh_gyms_count_error_does_not_touch_store():
    store = {"indicators": {"gyms_registered": {"value": 42}}}
    res = refresh_gyms_count("el-cañaveral", csv_text="a;b\n", store=store)
    assert res["status"] == "error"
    assert store["indicators"]["gyms_registered"]["value"] == 42


def test_refresh_gyms_count_download_error():
    res = refresh_gyms_count("el-cañaveral", url="http://127.0.0.1:1/nope", timeout=2,
                              store={"indicators": {}})
    assert res["status"] == "error"
    assert "Error al descargar" in res["error"]


# --- composición del hogar ---

def test_parse_household_composition_classifies_three_buckets():
    r = parse_household_composition_rows(_composition_rows(SECTIONS), [19052, 19053])
    assert r["status"] == "ok"
    assert r["households_total"] == 220          # 100 + 120
    assert r["households_with_minors"] == 22     # 10 + 12
    assert r["without_minors_households"] == 88  # 40 + 48
    assert r["ambiguous_households"] == 44       # 20 + 24


def test_parse_household_composition_missing_section():
    r = parse_household_composition_rows(_composition_rows(SECTIONS), [19052, 19999])
    assert r["status"] == "error"
    assert 19999 in r["missing_sections"]


def test_parse_household_composition_without_sheet_header():
    r = parse_household_composition_rows([("nada",)], [19052])
    assert r["status"] == "error"


def test_refresh_households_with_minors_updates_store():
    store = {"indicators": {}}
    res = refresh_households_with_minors("el-cañaveral",
                                         rows=_composition_rows(SECTIONS),
                                         section_codes=[19052, 19053], store=store)
    assert res["status"] == "ok"
    assert res["households_with_minors"] == 22
    value = store["indicators"]["households_with_minors"]["value"]
    assert value == 22
    assert store["indicators"]["households_with_minors"]["verification_status"] == "verified"


def test_refresh_households_with_minors_unsupported_area():
    res = refresh_households_with_minors("madrid", rows=_composition_rows(SECTIONS),
                                          section_codes=[19052], store={"indicators": {}})
    assert res["status"] == "unsupported"


def test_refresh_households_with_minors_error_does_not_touch_store():
    store = {"indicators": {"households_with_minors": {"value": 7}}}
    res = refresh_households_with_minors("el-cañaveral",
                                         rows=_composition_rows(SECTIONS),
                                         section_codes=[19052, 19999], store=store)
    assert res["status"] == "error"
    assert store["indicators"]["households_with_minors"]["value"] == 7


# --- contrato de los valores publicados ---

def test_published_equipment_indicators_are_consistent():
    ind = _STATISTICS_DATA["indicators"]
    assert ind["gyms_registered"]["value"] == 9
    assert ind["sports_recreation_venues"]["value"] == 4
    assert ind["childrens_play_venues"]["value"] == 3
    assert ind["community_pools"]["value"] == 3
    for key in ("gyms_registered", "sports_recreation_venues",
                "childrens_play_venues", "community_pools"):
        assert ind[key]["verification_status"] == "verified"
        assert ind[key]["source_url"]
        assert ind[key]["limitations"]


def test_published_households_with_minors_is_a_documented_minimum():
    ind = _STATISTICS_DATA["indicators"]
    assert ind["households_with_minors"]["value"] == 3071
    assert ind["households_with_minors"]["verification_status"] == "verified"
    # The limitation must state that it is a minimum, not a total.
    assert "MÍNIMO" in ind["households_with_minors"]["limitations"]


def test_unverifiable_indicators_remain_null():
    ind = _STATISTICS_DATA["indicators"]
    for key in ("gyms_with_ludoteca", "families_with_children"):
        assert ind[key]["value"] is None
        assert ind[key]["verification_status"] == "unavailable"
        assert ind[key]["limitations"]
