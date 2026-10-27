"""
Formato de salida estructurada del redactor con LLM.

Estos modelos validan la estructura de la respuesta.
La existencia y el respaldo de las referencias se comprueban después.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WritingClaim(BaseModel):
    """Afirmación redactada con referencias a las evidencias recibidas."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    kind: Literal["fact", "assumption", "inference"]
    evidence_ids: list[str] = Field(default_factory=list)


class WritingOutput(BaseModel):
    """Contenido que debe devolver el LLM."""

    model_config = ConfigDict(extra="forbid")

    sections: list[str] = Field(min_length=1)
    claims: list[WritingClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)