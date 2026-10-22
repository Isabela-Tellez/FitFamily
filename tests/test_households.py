"""Tests for the households indicators (Persona 1 - Juan).

These tests use controlled data and do not require internet connectivity.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp.server import (
    parse_households_rows,
    refresh_households,
    _STATISTICS_DATA,
)

# The nine sections officially assigned to El Cañaveral (COD_BAR 194),
# with the values published in the official households workbook (1 Jan 2025).
OFFICIAL_SECTIONS = [19052, 19053, 19054, 19055, 19056, 19058, 19059, 19060, 19061]
OFFICIAL_ROWS = [
    (19052, 2091, 808),
    (19053, 2414, 875),
    (19054, 2394, 874),
    (19055, 2766, 1130),
    (19056, 3007, 1143),
    (19058, 1793, 806),
    (19059, 2613, 797),
    (19060, 2470, 942),
    (19061, 1944, 765),
]


def test_parse_households_rows_aggregates_official_sections():
    result = parse_households_rows(OFFICIAL_ROWS, OFFICIAL_SECTIONS)
    assert result["status"] == "ok"
    assert result["households"] == 8140
    assert result["inhabitants"] == 21492
    assert abs(result["average_household_size"] - 2.6403) < 0.0001
    assert result["missing_sections"] == []


def test_parse_households_rows_ignores_other_sections():
    rows = OFFICIAL_ROWS + [(19001, 3058, 904), (19002, 1721, 581)]
    result = parse_households_rows(rows, OFFICIAL_SECTIONS)
    assert result["households"] == 8140
    assert len(result["sections"]) == 9


def test_parse_households_rows_reports_missing_sections():
    result = parse_households_rows(OFFICIAL_ROWS, OFFICIAL_SECTIONS + [19999])
    assert result["status"] == "error"
    assert 19999 in result["missing_sections"]
    assert "19999" in result["error"]


def test_parse_households_rows_without_match_is_error():
    result = parse_households_rows([(19001, 100, 40)], OFFICIAL_SECTIONS)
    assert result["status"] == "error"
    assert result["households"] is None


def test_refresh_households_updates_store():
    store = {"indicators": {}}
    result = refresh_households("el-cañaveral", rows=OFFICIAL_ROWS,
                                section_codes=OFFICIAL_SECTIONS, store=store)
    assert result["status"] == "ok"
    assert result["households"] == 8140
    ind = store["indicators"]["households_total"]
    assert ind["value"] == 8140
    assert ind["verification_status"] == "verified"
    assert ind["reference_period"] == "1 de enero de 2025"
    avg = store["indicators"]["average_household_size"]
    assert abs(avg["value"] - 2.64) < 0.01


def test_refresh_households_unsupported_area():
    result = refresh_households("madrid", rows=OFFICIAL_ROWS,
                                section_codes=OFFICIAL_SECTIONS, store={"indicators": {}})
    assert result["status"] == "unsupported"


def test_refresh_households_error_does_not_touch_store():
    store = {"indicators": {"households_total": {"value": 123}}}
    result = refresh_households("el-cañaveral", rows=OFFICIAL_ROWS,
                                section_codes=OFFICIAL_SECTIONS + [19999], store=store)
    assert result["status"] == "error"
    assert store["indicators"]["households_total"]["value"] == 123


def test_published_indicators_are_consistent():
    """The published values must match the official aggregation."""
    ind = _STATISTICS_DATA["indicators"]
    assert ind["households_total"]["value"] == 8140
    assert ind["households_total"]["verification_status"] == "verified"
    assert ind["households_total"]["reference_period"] == "1 de enero de 2025"
    assert ind["average_household_size"]["value"] == 2.64
    assert ind["population_total_2025"]["value"] == 21492
    # The ratio must be coherent within the same reference period.
    ratio = ind["population_total_2025"]["value"] / ind["households_total"]["value"]
    assert abs(ratio - ind["average_household_size"]["value"]) < 0.01


def test_households_and_current_population_have_different_periods():
    """Guard against mixing households (2025) with current population (2026)."""
    ind = _STATISTICS_DATA["indicators"]
    assert ind["households_total"]["reference_period"] != ind["population_total"]["reference_period"]
    assert "population_total_2025" in ind
