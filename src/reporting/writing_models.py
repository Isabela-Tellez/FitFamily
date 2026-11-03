"""
Formato de salida estructurada del redactor con LLM.

Estos modelos validan la estructura de la respuesta.
La existencia y el respaldo de las referencias se comprueban después.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from src.reporting.templates import REPORT_SECTION_TITLES


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


# El formato del proveedor identifica cada cuerpo por su título. El constructor
# local controla el número y orden de los apartados, no una lista generada.
WritingSections = create_model(
    "WritingSections",
    __config__=ConfigDict(extra="forbid", strict=True),
    **{
        f"section_{index}": (str, Field(alias=title, min_length=1))
        for index, title in enumerate(REPORT_SECTION_TITLES)
    },
)


class WritingResponse(BaseModel):
    """Contrato de transporte: once cuerpos obligatorios, sin títulos libres."""

    model_config = ConfigDict(extra="forbid", strict=True)
    sections: WritingSections
    claims: list[WritingClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def writer_response_schema() -> dict:
    """Esquema compatible con el modo estricto de Groq; sin campos opcionales."""
    schema = WritingResponse.model_json_schema(by_alias=True)

    def make_required(node):
        if isinstance(node, dict):
            for key in ("title", "default", "minLength"):
                node.pop(key, None)
            if node.get("type") == "object":
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for child in node.values():
                make_required(child)
        elif isinstance(node, list):
            for child in node:
                make_required(child)

    make_required(schema)
    return schema


def writer_response_format(model: str) -> dict:
    """Usa esquema estricto solo en los modelos GPT-OSS verificados."""
    if model in {"groq/openai/gpt-oss-120b", "groq/openai/gpt-oss-20b"}:
        return {"type": "json_schema", "json_schema": {
            "name": "fitfamily_writing", "strict": True,
            "schema": writer_response_schema(),
        }}
    return {"type": "json_object"}


def parse_writing_output(raw: str) -> WritingOutput:
    """Valida el contrato y construye los títulos sin completar datos ausentes."""
    import json

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Clave JSON duplicada: {key}")
            result[key] = value
        return result

    data = json.loads(raw, object_pairs_hook=unique_keys)
    if isinstance(data, dict) and isinstance(data.get("sections"), dict):
        response = WritingResponse.model_validate(data)
        bodies = response.sections.model_dump(by_alias=True)
        return WritingOutput(
            sections=[f"{title}\n{bodies[title]}" for title in REPORT_SECTION_TITLES],
            claims=response.claims, limitations=response.limitations,
        )
    # Compatibilidad con respuestas/simulaciones anteriores; después se aplica
    # igualmente validate_report_sections, sin reordenar ni reparar listas.
    return WritingOutput.model_validate(data)
