"""
Formato de salida estructurada del redactor con LLM.

Estos modelos validan la estructura de la respuesta.
La existencia y el respaldo de las referencias se comprueban después.
"""
import json
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
        f"section_{index}": (str, Field(min_length=1))
        for index, _ in enumerate(REPORT_SECTION_TITLES)
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
    """Genera un JSON Schema compatible con Structured Outputs de Groq."""

    if model in {
        "groq/openai/gpt-oss-120b",
        "groq/openai/gpt-oss-20b",
    }:
        schema = WritingResponse.model_json_schema()

        sections_schema = schema["$defs"]["WritingSections"]

        sections_schema["properties"] = {
            title: {"type": "string"}
            for title in REPORT_SECTION_TITLES
        }

        sections_schema["required"] = list(REPORT_SECTION_TITLES)
        sections_schema["additionalProperties"] = False

        claim_schema = schema["$defs"]["WritingClaim"]

        claim_schema["required"] = [
            "text",
            "kind",
            "evidence_ids",
        ]

        # Groq exige que todos los campos de cada objeto
        # estén incluidos en required.
        schema["required"] = [
            "sections",
            "claims",
            "limitations",
        ]

        schema["additionalProperties"] = False

        return {
            "type": "json_schema",
            "json_schema": {
                "name": "fitfamily_writing",
                "strict": True,
                "schema": schema,
            },
        }

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
        sections = data["sections"]

        # Compatibilidad con secciones identificadas por sus títulos.
        if set(sections) == set(REPORT_SECTION_TITLES):
            data["sections"] = {
                f"section_{i}": sections[title]
                for i, title in enumerate(REPORT_SECTION_TITLES)
            }

        response = WritingResponse.model_validate(data)

        bodies = response.sections.model_dump()

        return WritingOutput(
            sections=[
                f"{title}\n{bodies[f'section_{index}']}"
                for index, title in enumerate(REPORT_SECTION_TITLES)
            ],
            claims=response.claims,
            limitations=response.limitations,
        )

    # Compatibilidad con respuestas/simulaciones anteriores.
    # Después se aplica igualmente validate_report_sections,
    # sin reordenar ni reparar listas.
    return WritingOutput.model_validate(data)
