"""Compatibilidad del sistema de diseño.

La implementación vive en :mod:`src.ui.studio.styles`. Este módulo
mantiene los nombres históricos (`design.inject`, `design.COLORS`, etc.)
para que ninguna pantalla dependa de la ubicación del CSS.
"""
from __future__ import annotations

from src.ui.studio.styles import (  # noqa: F401
    COLORS,
    FONT_FAMILY,
    GLOBAL_CSS,
    RADIUS,
    SHADOW,
    SPACING,
    inject,
)

__all__ = [
    "COLORS",
    "FONT_FAMILY",
    "GLOBAL_CSS",
    "RADIUS",
    "SHADOW",
    "SPACING",
    "inject",
]
