"""Tests for the Censo de Locales integration (Persona 1 - Juan).

These tests use a small inline CSV and do not require network access.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp.server import parse_locales_csv, refresh_locales_count

SAMPLE_CSV = (
    '"id_local";"desc_barrio_local";"desc_situacion_local"\n'
    '"1";"EL CANAVERAL";"Abierto"\n'
    '"2";"EL CANAVERAL";"Abierto"\n'
    '"3";"EL CANAVERAL";"Cerrado"\n'
    '"4";"VALDEBEBAS";"Abierto"\n'
    '"1";"EL CANAVERAL";"Abierto"\n'  # duplicate id
)


def test_parse_locales_csv_basic():
    r = parse_locales_csv(SAMPLE_CSV.replace("CANAVERAL", "CAÑAVERAL"), "EL CAÑAVERAL")
    assert r["status"] == "ok"
    assert r["count"] == 2  # unique ids
    assert r["total_rows"] == 4
    assert "Abierto" in r["situations"]
    assert "Cerrado" in r["situations"]


def test_parse_locales_csv_empty():
    r = parse_locales_csv("", "EL CAÑAVERAL")
    assert r["status"] == "error"
    assert r["count"] is None


def test_parse_locales_csv_missing_columns():
    r = parse_locales_csv('"a";"b"\n"1";"2"\n', "EL CAÑAVERAL")
    assert r["status"] == "error"
    assert "Columnas requeridas" in r["error"]


def test_parse_locales_csv_barrio_not_found():
    r = parse_locales_csv(SAMPLE_CSV.replace("CANAVERAL", "CAÑAVERAL"), "FUENCARRAL")
    assert r["status"] == "error"
    assert "no encontrado" in r["error"]


def test_parse_locales_csv_malformed_rows():
    csv_text = (
        '"id_local";"desc_barrio_local";"desc_situacion_local"\n'
        '"1";"EL CAÑAVERAL";"Abierto"\n'
        'not;a;valid;row\n'
        '"2";"EL CAÑAVERAL";"Abierto"\n'
    )
    r = parse_locales_csv(csv_text, "EL CAÑAVERAL")
    assert r["status"] == "ok"
    assert r["count"] == 2


def test_refresh_with_csv_text_updates_store():
    store = {"indicators": {}}
    res = refresh_locales_count("el-cañaveral", csv_text=SAMPLE_CSV.replace("CANAVERAL", "CAÑAVERAL"), store=store)
    assert res["status"] == "ok"
    assert res["count"] == 2
    assert store["indicators"]["businesses_open"]["value"] == 2
    assert store["indicators"]["businesses_open"]["verification_status"] == "verified"


def test_refresh_unsupported_area():
    res = refresh_locales_count("madrid")
    assert res["status"] == "unsupported"


def test_refresh_download_error():
    res = refresh_locales_count("el-cañaveral", url="http://127.0.0.1:1/nope", timeout=2)
    assert res["status"] == "error"
    assert "Error al descargar" in res["error"]


def test_refresh_empty_csv():
    res = refresh_locales_count("el-cañaveral", csv_text="", store={"indicators": {}})
    assert res["status"] == "error"