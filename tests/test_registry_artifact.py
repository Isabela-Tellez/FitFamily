"""Invariants of the committed competitor registry artifact (Persona 1 - Juan).

The JSON is generated from the official Madrid census. These checks catch a
stale or corrupted artifact without needing network access or the raw files.
"""

import json
from pathlib import Path

from src.tools.competitor_registry import _normalize_text

ARTIFACT = Path(__file__).resolve().parents[1] / "data" / "processed" / "competitor_registry.json"


def _registry():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_artifact_has_the_expected_snapshot_and_counters():
    data = _registry()
    assert data["source"].startswith("Censo de Locales")
    assert data["license"]
    assert data["generated_at"]
    competitors = data["competitors"]
    counters = data["counters"]
    assert counters["competidores"] == len(competitors) == 18
    assert counters["sin_coordenadas"] == sum(
        1 for c in competitors if c.get("latitude") is None
    )
    assert counters["sin_nombre_comercial"] == sum(
        1 for c in competitors if not c.get("name")
    )
    assert counters["locales_con_licencia"] == sum(
        1 for c in competitors if c.get("license_status") is not None
    )


def test_artifact_identifiers_and_evidence_ids_are_unique():
    competitors = _registry()["competitors"]
    identifiers = [c["identifier"] for c in competitors]
    assert len(identifiers) == len(set(identifiers))
    evidence_ids = [e["evidence_id"] for c in competitors for e in c["evidences"]]
    assert len(evidence_ids) == len(set(evidence_ids))


def test_artifact_has_traceable_official_evidence():
    for competitor in _registry()["competitors"]:
        prefixes = {e["evidence_id"].split("_")[0] for e in competitor["evidences"]}
        assert {"census"} <= prefixes
        ids = {e["evidence_id"] for e in competitor["evidences"]}
        assert any(i.startswith("census_local_") for i in ids)
        assert any(i.startswith("census_activity_") for i in ids)
        assert any(i.startswith("census_license_") for i in ids)
        for evidence in competitor["evidences"]:
            assert evidence["source_url"].startswith("https://")
            assert "datos.madrid.es" in evidence["source_url"]
            assert evidence["claim"]
            assert evidence["limitations"]


def test_artifact_has_complete_addresses_and_activities():
    for competitor in _registry()["competitors"]:
        location = competitor.get("location") or ""
        assert location.strip()
        assert _normalize_text(location)
        assert location.count('"') % 2 == 0, location
        assert competitor.get("postal_code")
        assert competitor.get("census_section")
        assert competitor.get("services")
        assert len(competitor["services"]) == len(set(competitor["services"]))


def test_artifact_does_not_contain_zero_coordinates():
    for competitor in _registry()["competitors"]:
        latitude = competitor.get("latitude")
        longitude = competitor.get("longitude")
        assert (latitude is None) == (longitude is None)
        if latitude is not None:
            assert not (latitude == 0 and longitude == 0)
            assert 40.3 <= latitude <= 40.6
            assert -3.9 <= longitude <= -3.4


def test_license_absence_is_not_denied_and_pending_is_not_closure():
    for competitor in _registry()["competitors"]:
        licence = next(
            e for e in competitor["evidences"]
            if e["evidence_id"].startswith("census_license_")
        )
        status = competitor.get("license_status")
        if status is None:
            assert "Sin información" in licence["claim"]
            assert "no disponible" in licence["limitations"]
        else:
            assert "no acredita" in licence["limitations"]
            assert "abierto" in licence["limitations"]
            assert "cerrado" in licence["limitations"]


def test_csv_artifact_matches_the_json():
    import pandas as pd

    data = _registry()
    frame = pd.read_csv(ARTIFACT.with_suffix(".csv"))
    assert len(frame) == len(data["competitors"])
    assert set(frame["competitor_id"].astype(str)) == {
        c["identifier"] for c in data["competitors"]
    }
    assert frame["monthly_price_eur"].isna().all()
    assert frame["has_playroom"].isna().all()
    by_id = {c["identifier"]: c for c in data["competitors"]}
    for row in frame.itertuples():
        assert row.address == by_id[str(row.competitor_id)]["location"]
