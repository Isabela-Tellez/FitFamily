"""Deterministic identifiers for evidence records.

Evidence ids are persisted with research results, so they must be equal
between runs with the same inputs and must not depend on Python's salted
``hash()``.  The suffix is a truncated SHA-256 of the identifying parts.
"""

from __future__ import annotations

import hashlib
from typing import Any


def stable_evidence_id(prefix: str, *parts: Any, length: int = 16) -> str:
    """Return ``prefix_<hex digest>`` for the given identifying parts.

    ``parts`` are length-prefixed before joining, so a separator inside one
    part cannot be confused with a boundary. ``None`` and empty strings are
    equivalent.
    """
    clean_parts = ["" if part is None else str(part).strip() for part in parts]
    material = "\x1f".join(f"{len(part)}:{part}" for part in clean_parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"
