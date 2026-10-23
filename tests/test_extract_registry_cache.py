"""Cache validation of the registry extraction script (Persona 1 - Juan).

A small file (an HTML error page or a fixture) must never be accepted as the
official census cache, because it silently produces an empty registry.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "data" / "raw" / "extract_competitor_registry.py"

spec = importlib.util.spec_from_file_location("extract_competitor_registry", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_cache_validation_rejects_tiny_files_and_missing_headers(tmp_path):
    tiny = tmp_path / "tiny.csv"
    tiny.write_text('"id_local";"desc_barrio_local"\n"1";"EL CANAVERAL"\n', encoding="utf-8")
    assert module._cache_is_valid(str(tiny)) is False

    headerless = tmp_path / "headerless.csv"
    headerless.write_bytes(b"x" * 1_100_000)
    assert module._cache_is_valid(str(headerless)) is False


def test_cache_validation_accepts_a_large_official_header(tmp_path):
    valid = tmp_path / "valid.csv"
    valid.write_bytes(b'"id_local";"desc_barrio_local"\n' + b"x" * 1_100_000)
    assert module._cache_is_valid(str(valid)) is True
