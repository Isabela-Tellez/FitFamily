#!/usr/bin/env python
"""Build the FitFamily competitor registry from official open data.

OFFLINE data-preparation tool (not part of the MCP server runtime).

Sources (Ayuntamiento de Madrid, CC BY 4.0):
  - Censo de Locales:        id, direccion, CP, coordenadas
  - Censo de Actividades:   epigrafes de actividad
  - Locales con licencia:   referencia y situacion administrativa

Optional step: enrich each competitor with the data published on its own
website (price, playroom evidence), always tied to the official address.

Usage:
    python data/raw/extract_competitor_registry.py
    python data/raw/extract_competitor_registry.py --no-web
    python data/raw/extract_competitor_registry.py --json data/processed/competitor_registry.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from src.tools.competitor_registry import (  # noqa: E402
    ACTIVIDADES_URL,
    BARRIO_NAMES,
    LICENCIAS_URL,
    LOCALES_URL,
    _normalize_text,
    build_competitor_registry,
    enrich_competitor_from_web,
    read_census_rows,
    registry_to_dict,
    to_dataframe,
)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
MIN_CACHE_BYTES = 1_000_000


def _cache_is_valid(path: str) -> bool:
    """A tiny file (an HTML error page, a fixture) is not the official CSV."""
    if not os.path.exists(path) or os.path.getsize(path) < MIN_CACHE_BYTES:
        return False
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        header = fh.readline()
    return "id_local" in header


def _cached(url: str, filename: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    if _cache_is_valid(path):
        print("[cache] %s" % filename)
        return path
    if os.path.exists(path):
        print("[cache invalida] %s (%d bytes), se descarga de nuevo"
              % (filename, os.path.getsize(path)))
    print("[descarga] %s" % url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    partial = path + ".part"
    with urllib.request.urlopen(req, timeout=900) as resp, open(partial, "wb") as fh:
        total = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            total += len(chunk)
    if not _cache_is_valid(partial):
        os.remove(partial)
        raise RuntimeError("La descarga de %s no parece el CSV oficial" % filename)
    os.replace(partial, path)
    print("[descarga] %s (%d bytes)" % (filename, total))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", default="el-cañaveral")
    parser.add_argument("--no-web", action="store_true",
                        help="No enrichment from the websites (official data only)")
    parser.add_argument("--json", dest="json_out",
                        default="data/processed/competitor_registry.json")
    args = parser.parse_args()

    locales_path = _cached(LOCALES_URL, "censo_locales.csv")
    actividades_path = _cached(ACTIVIDADES_URL, "censo_actividades.csv")
    licencias_path = _cached(LICENCIAS_URL, "censo_licencias.csv")

    barrio = BARRIO_NAMES.get(args.area.strip().lower())
    if barrio is None:
        print("Area desconocida: %s" % args.area, file=sys.stderr)
        return 2
    target_barrio = _normalize_text(barrio)

    with open(locales_path, encoding="utf-8-sig", errors="replace", newline="") as locales_fh, \
         open(actividades_path, encoding="utf-8-sig", errors="replace", newline="") as activities_fh, \
         open(licencias_path, encoding="utf-8-sig", errors="replace", newline="") as licenses_fh:
        # Only the premises of the target neighbourhood are kept in memory;
        # the other two files are filtered while they are streamed.
        locales_rows = [
            row for row in read_census_rows(locales_fh)
            if _normalize_text(row.get("desc_barrio_local", "")) == target_barrio
        ]
        local_ids = {row.get("id_local") for row in locales_rows}
        activity_rows = (
            row for row in read_census_rows(activities_fh)
            if row.get("id_local") in local_ids
        )
        license_rows = (
            row for row in read_census_rows(licenses_fh)
            if row.get("id_local") in local_ids
        )
        registry = build_competitor_registry(
            area_id=args.area,
            locales_rows=locales_rows,
            activity_rows=activity_rows,
            license_rows=license_rows,
        )
    competitors = registry["competitors"]
    print("\n=== REGISTRO OFICIAL ===")
    print("contadores:", json.dumps(registry["counters"], ensure_ascii=False))
    for competitor in competitors:
        print("  %-11s %-24s %-52s licencia=%s" % (
            competitor.identifier,
            (competitor.name or "S/R")[:24],
            (competitor.location or "-")[:52],
            competitor.license_status or "sin informacion",
        ))

    if not args.no_web:
        print("\n=== ENRIQUECIMIENTO DESDE LAS WEBS ===")
        for competitor in competitors:
            enrich_competitor_from_web(competitor)
            prices = [t for t in competitor.tariffs if t.get("value") is not None]
            print("  %-11s precio_mensual=%-6s ludoteca=%-6s (%d precios)" % (
                competitor.identifier,
                next((t["value"] for t in prices
                      if t.get("frequency") == "monthly"), "-"),
                {True: "si", False: "no", None: "desconocido"}[competitor.has_playroom],
                len(prices),
            ))

    payload = registry_to_dict(competitors)
    payload["counters"] = registry["counters"]
    os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("\n[json] %s" % args.json_out)

    frame = to_dataframe(competitors)
    csv_path = os.path.splitext(args.json_out)[0] + ".csv"
    frame.to_csv(csv_path, index=False, encoding="utf-8")
    print("[csv] %s" % csv_path)
    print()
    print(frame[["gym_name", "monthly_price_eur", "has_playroom", "competitor_id",
                 "latitude", "longitude", "license_status"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
