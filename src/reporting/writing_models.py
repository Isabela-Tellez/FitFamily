"""
Formato de salida estructurada del redactor con LLM.

Estos modelos validan la estructura de la respuesta.
La existencia y el respaldo de las referencias se comprueban despues.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from src.reporting.templates import REPORT_SECTION_TITLES


class WritingClaim(BaseModel):
    """Afirmacion redactada con referencias a las evidencias recibidas."""

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


# El formato del proveedor identifica cada cuerpo por su titulo. El constructor
# local controla el numero y orden de los apartados, no una lista generada.
WritingSections = create_model(
    "WritingSections",
    __config__=ConfigDict(extra="forbid", strict=True),
    **{
        f"section_{index}": (str, Field(alias=title, min_length=1))
        for index, title in enumerate(REPORT_SECTION_TITLES)
    },
)


class WritingResponse(BaseModel):
    """Contrato de transporte: once cuerpos obligatorios, sin titulos libres."""

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
    """Formato de respuesta para el proveedor.

    Evidencia (ejecucion real fitfamily-e2e-demo-001, 2026-11-04):
    Groq con json_schema rechazo la respuesta del LLM porque este la envolvio
    en un array [{...}] en lugar de un objeto {...}. El esquema estricto se
    valida en el servidor y la respuesta nunca llego al parser local.
    Se usa json_object y se valida localmente con Pydantic (strict=True,
    extra=forbid), conservando todos los requisitos del informe.
    """
    return {"type": "json_object"}


def parse_writing_output(raw: str) -> WritingOutput:
    """Valida el contrato y construye los titulos sin completar datos ausentes.

    Normalizacion segura del formato (sin alterar valores):
    - Objeto JSON valido: se valida directamente.
    - Array con un unico objeto: se extrae ese objeto.
    - Array vacio: error claro.
    - Array con varios objetos: rechazo (estructura ambigua).
    - Contenido no-objeto: rechazo con mensaje explicativo.
    - Objeto con campos incorrectos: validacion estricta (Pydantic).
    """
    import json

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Clave JSON duplicada: {key}")
            result[key] = value
        return result

    try:
        data = json.loads(raw, object_pairs_hook=unique_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(
            "El redactor no devolvio un JSON valido: " + str(exc)
        ) from exc

    # Normalizacion del formato (sin cambiar valores ni completar campos).
    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError(
                "La respuesta del redactor es un array vacio; "
                "se esperaba un objeto JSON."
            )
        if len(data) > 1:
            raise ValueError(
                "La respuesta del redactor es un array con varios objetos; "
                "estructura ambigua, no se selecciona ninguno."
            )
        data = data[0]
        if not isinstance(data, dict):
            raise ValueError(
                "El unico elemento del array no es un objeto JSON valido."
            )

    if not isinstance(data, dict):
        raise ValueError(
            "La respuesta del redactor no es un objeto JSON valido."
        )

    if isinstance(data.get("sections"), dict):
        response = WritingResponse.model_validate(data)
        bodies = response.sections.model_dump(by_alias=True)
        return WritingOutput(
            sections=[f"{title}\n{bodies[title]}" for title in REPORT_SECTION_TITLES],
            claims=response.claims, limitations=response.limitations,
        )
    # Compatibilidad con respuestas/simulaciones anteriores; se aplica igualmente
    # validate_report_sections, sin reordenar ni reparar listas.
    return WritingOutput.model_validate(data)