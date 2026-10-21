#!/usr/bin/env python
"""Reproducible extraction of the Censo de Locales indicators for El Cañaveral.

OFFLINE data-preparation tool (not part of the MCP server runtime). It
reproduces the values published in `src/mcp/server.py`:

  * `businesses_open`            234  (fichero de Locales)
  * `gyms_registered`             9  (epígrafe 931008, fichero de Actividades)
  * `sports_recreation_venues`    4  (epígrafe 855002)
  * `childrens_play_venues`       3  (epígrafes 932001 + 932002)
  * `community_pools`             3  (epígrafe 931010)

Source: Censo de Locales y Actividades del Ayuntamiento de Madrid
https://datos.madrid.es/dataset/200085-0-censo-locales (CC BY 4.0, actualización diaria).

Usage:
    python data/raw/extract_censo_locales.py
    python data/raw/extract_censo_locales.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from src.mcp.server import (  # noqa: E402
    _ACTIVIDADES_CSV_URL,
    _LOCALES_CSV_URL,
    _SUPPORTED_LOCALES_AREAS,
    parse_actividades_csv,
    parse_locales_csv,
)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

EPIGRAFES = {
    "gyms_registered": ["931008"],
    "sports_recreation_venues": ["855002"],
    "childrens_play_venues": ["932001", "932002"],
    "community_pools": ["931010"],
}


def _download(url: str, filename: str) -> str:
    import urllib.request

    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print("[cache] %s" % filename)
        return path
    print("[descarga] %s" % url)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = resp.read()
    with open(path, "wb") as fh:
        fh.write(data)
    print("[descarga] %s (%d bytes)" % (filename, len(data)))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_out", help="Escribe el resultado en un JSON")
    args = parser.parse_args()

    barrio = _SUPPORTED_LOCALES_AREAS["el-cañaveral"]

    print("\n=== Locales abiertos (fichero de Locales) ===")
    locales_path = _download(_LOCALES_CSV_URL, "censo_locales.csv")
    with open(locales_path, encoding="utf-8-sig", errors="replace") as fh:
        locales = parse_locales_csv(fh.read(), barrio)
    if locales["status"] != "ok":
        print("ERROR: %s" % locales.get("error"))
        return 1
    print("locales abiertos: %s (filas del barrio: %s)" % (
        locales["count"], locales["total_rows"]))
    print("situaciones: %s" % locales["situations"])

    print("\n=== Equipamientos por epigrafe (fichero de Actividades) ===")
    actividades_path = _download(_ACTIVIDADES_CSV_URL, "censo_actividades.csv")
    with open(actividades_path, encoding="utf-8-sig", errors="replace") as fh:
        actividades = parse_actividades_csv(fh.read(), barrio)
    if actividades["status"] != "ok":
        print("ERROR: %s" % actividades.get("error"))
        return 1
    print("locales abiertos con actividad declarada: %s" % actividades["total_open_premises"])

    indicadores = {}
    for nombre, codes in EPIGRAFES.items():
        value = sum(actividades["counts"].get(c, 0) for c in codes)
        indicadores[nombre] = value
        print("  %-28s %s" % (nombre, value))

    result = {
        "area": "El Cañaveral",
        "reference_period": "descarga del %s" % datetime.now(timezone.utc).date().isoformat(),
        "businesses_open": locales["count"],
        "indicators": indicadores,
        "epigraph_counts": actividades["counts"],
        "sources": {
            "locales": _LOCALES_CSV_URL,
            "actividades": _ACTIVIDADES_CSV_URL,
        },
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print("\n[json] %s" % args.json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
