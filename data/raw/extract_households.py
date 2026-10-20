#!/usr/bin/env python
"""Reproducible extraction of the households indicators for El Cañaveral.

This is an OFFLINE data-preparation tool, not part of the MCP server runtime.
It reproduces the values published in `src/mcp/server.py` for the indicators
`households_total`, `average_household_size` and `population_total_2025`.

Sources (both official, both free, both CC BY 4.0):
  1. Hogares por tamaño, composición del hogar, nacionalidad y sección censal
     https://datos.madrid.es/dataset/300438-0-hogares-tamano
     (recurso XLSX 2025, Padrón Municipal revisado a 1 de enero de 2025)
  2. Límites administrativos actuales (Geoportal del Ayuntamiento de Madrid)
     https://geoportal.madrid.es/IDEAM_WBGEOPORTAL/dataset.iam?id=e251898e-4a9c-11eb-9104-dc4a3e8ce33b
     (secciones censales, EPSG:25830, fecha de datos 31/08/2026)

Method:
  - The official cartography attributes every census section to a barrio
    through the attribute `COD_BAR`. Sections with COD_BAR = 194 (El Cañaveral)
    are selected.
  - Their households and inhabitants are summed from the official workbook.
  - The aggregation is EXACT: the 9 sections tile the barrio polygon (100 %),
    so no section crosses the boundary and no proportional allocation is used.
    `--verify-geometry` recomputes that geometric check.

Usage:
    python data/raw/extract_households.py                 # aggregate only
    python data/raw/extract_households.py --verify-geometry   # + geometric proof
    python data/raw/extract_households.py --json out.json

Dependencies: openpyxl and pyogrio (already available in the project
environment). They are NOT runtime dependencies of the MCP server.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

HOGARES_XLSX_URL = (
    "https://datos.madrid.es/dataset/300438-0-hogares-tamano/resource/"
    "300438-2-hogares-tamano-xlsx/download/300438-2-hogares-tamano-xlsx.xlsx"
)
SECCIONES_SHP_URL = (
    "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/"
    "LIMITES_ADMINISTRATIVOS/Seccionado/Secciones_Censales.zip"
)
BARRIOS_SHP_URL = (
    "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/"
    "LIMITES_ADMINISTRATIVOS/Barrios/Barrios.zip"
)

BARRIO_CODIGO = 194
BARRIO_NOMBRE = "El Cañaveral"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def _download(url: str, filename: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"[cache] {filename}")
        return path
    print(f"[descarga] {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = resp.read()
    with open(path, "wb") as fh:
        fh.write(data)
    print(f"[descarga] {filename} ({len(data)} bytes)")
    return path


def _read_households(xlsx_path: str):
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = []
    for r in ws.iter_rows(values_only=True):
        if len(r) < 4 or not isinstance(r[1], int):
            continue
        rows.append((r[1], r[2], r[3]))
    return rows


def _read_sections(zip_path: str):
    import pyogrio

    with zipfile.ZipFile(zip_path) as z:
        dbf = [n for n in z.namelist() if n.upper().endswith(".DBF")][0]
        with tempfile.TemporaryDirectory() as tmp:
            z.extract(dbf, tmp)
            return pyogrio.read_dataframe(os.path.join(tmp, dbf))


def _read_barrios(zip_path: str):
    import pyogrio

    with zipfile.ZipFile(zip_path) as z:
        dbf = [n for n in z.namelist() if n.upper().endswith(".DBF")][0]
        with tempfile.TemporaryDirectory() as tmp:
            z.extract(dbf, tmp)
            return pyogrio.read_dataframe(os.path.join(tmp, dbf))


def verify_geometry(sections_zip: str, barrios_zip: str, section_codes):
    """Prove that the selected sections tile the barrio exactly."""
    from shapely.ops import unary_union

    import geopandas as gpd

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(sections_zip) as z:
            z.extractall(os.path.join(tmp, "sec"))
        with zipfile.ZipFile(barrios_zip) as z:
            z.extractall(os.path.join(tmp, "bar"))
        sec = gpd.read_file(os.path.join(tmp, "sec"))
        bar = gpd.read_file(os.path.join(tmp, "bar"))

    barrio = bar[bar["COD_BAR"].astype(int) == BARRIO_CODIGO].iloc[0].geometry
    sel = sec[sec["COD_SECCIO"].astype(int).isin([int(c) for c in section_codes])]
    union = unary_union(sel.geometry.values)
    inter = barrio.intersection(union)

    print("\n--- Verificación geométrica ---")
    print(f"Área del barrio:                {barrio.area:,.1f} m2")
    print(f"Área de las {len(sel)} secciones:      {union.area:,.1f} m2")
    print(f"Intersección:                   {inter.area:,.1f} m2")
    print(f"Cobertura del barrio:           {100 * inter.area / barrio.area:.4f} %")
    print(f"Secciones fuera del barrio:     {union.difference(barrio).area:,.1f} m2")
    print(f"Barrio sin cubrir:              {barrio.difference(union).area:,.1f} m2")
    ratios = [g.intersection(barrio).area / g.area for g in sel.geometry]
    print(f"Ratio mínimo de intersección:   {min(ratios):.4f}")
    print(f"Ratio máximo de intersección:   {max(ratios):.4f}")
    exact = (
        union.difference(barrio).area < 1.0
        and barrio.difference(union).area < 1.0
        and min(ratios) > 0.9999
    )
    print(f"Agregación EXACTA (sin reparto): {exact}")
    return exact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-geometry", action="store_true",
                        help="Verifica geométricamente que las secciones teselan el barrio")
    parser.add_argument("--json", dest="json_out", help="Escribe el resultado en un JSON")
    args = parser.parse_args()

    xlsx = _download(HOGARES_XLSX_URL, "hogares_2025.xlsx")
    sections_zip = _download(SECCIONES_SHP_URL, "Secciones_Censales.zip")

    sections = _read_sections(sections_zip)
    codes = sorted(int(c) for c in
                   sections[sections["COD_BAR"].astype(int) == BARRIO_CODIGO]["COD_SECCIO"])
    print(f"\nSecciones asignadas oficialmente a {BARRIO_NOMBRE} (COD_BAR {BARRIO_CODIGO}): {codes}")

    rows = _read_households(xlsx)
    index = {int(c): (h, g) for c, h, g in rows}

    total_h = 0
    total_pop = 0.0
    detail = []
    for code in codes:
        if code not in index:
            print(f"  AVISO: la sección {code} no aparece en el fichero de hogares")
            continue
        hab, hog = index[code]
        total_h += round(hog)
        total_pop += hab
        detail.append({"seccion": code, "habitantes": round(hab), "hogares": round(hog)})

    print("\n--- Detalle por sección ---")
    for d in detail:
        print(f"  {d['seccion']}  hab={d['habitantes']:6d}  hogares={d['hogares']:5d}")
    print(f"\nTOTAL hogares: {total_h}")
    print(f"TOTAL habitantes: {round(total_pop)}")
    print(f"Tamaño medio del hogar: {total_pop / total_h:.4f}")

    exact = None
    if args.verify_geometry:
        barrios_zip = _download(BARRIOS_SHP_URL, "Barrios.zip")
        exact = verify_geometry(sections_zip, barrios_zip, codes)

    result = {
        "area": BARRIO_NOMBRE,
        "cod_barrio": BARRIO_CODIGO,
        "reference_period": "1 de enero de 2025",
        "sections": codes,
        "detail": detail,
        "households_total": int(total_h),
        "population_total": int(round(total_pop)),
        "average_household_size": round(total_pop / total_h, 4),
        "sources": {
            "households": HOGARES_XLSX_URL,
            "sections": SECCIONES_SHP_URL,
        },
        "geometry_verified": exact,
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print(f"\n[json] {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
