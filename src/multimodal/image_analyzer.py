"""Análisis visual de gráficos y artefactos de FitFamily."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

import litellm
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

if TYPE_CHECKING:
    from src.reporting.models import ReportDraft

logger = logging.getLogger(__name__)
SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}


class ImageObservation(BaseModel):
    """Observación visual trazable asociada a una imagen del proyecto."""

    model_config = ConfigDict(extra="forbid")

    image_id: str = Field(min_length=1)
    source_image_path: str = Field(min_length=1)
    source_artifact_id: str | None = None
    model_used: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)
    processed_file_path: str = Field(min_length=1)


def _image_data_url(image_path: Path) -> str:
    """Valida la extensión y codifica la imagen para el proveedor visual."""

    if not image_path.exists():
        raise FileNotFoundError(f"No existe el archivo de imagen: {image_path}")
    if not image_path.is_file():
        raise ValueError(f"La ruta de imagen no es un archivo: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        raise ValueError("Formato no compatible. Usa PNG, JPG, JPEG o WEBP.")

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError("No se ha podido determinar el formato de la imagen.")

    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _extract_text(content: Any) -> str:
    """Extrae texto de las respuestas de LiteLLM en sus formatos habituales."""

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        return "\n".join(text_parts).strip()
    raise ValueError("El proveedor visual devolvió una respuesta sin texto.")


def _parse_json_response(content: Any) -> dict[str, Any]:
    """Convierte la respuesta del modelo en un objeto JSON."""

    text = _extract_text(content)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("El modelo visual no devolvió un JSON válido.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("La respuesta JSON del modelo debe ser un objeto.")
    return parsed


def analyze_image(
    image_path: str | Path,
    context: str | dict[str, Any],
    *,
    image_id: str | None = None,
    source_artifact_id: str | None = None,
    model: str | None = None,
) -> ImageObservation:
    """Envía la imagen real a un modelo visual y devuelve una observación trazable.

    La variable VISION_LLM_MODEL debe identificar un modelo con entrada de imagen.
    Se reutiliza GROQ_API_KEY, pero no el modelo textual del redactor.
    """

    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)

    path = Path(image_path)
    data_url = _image_data_url(path)
    selected_model = (model or os.getenv("VISION_LLM_MODEL", "")).strip()
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not selected_model:
        raise ValueError("Falta configurar VISION_LLM_MODEL.")
    if not selected_model.startswith("groq/"):
        raise ValueError("VISION_LLM_MODEL debe utilizar el proveedor Groq (prefijo groq/).")
    if not api_key or api_key == "pega_aqui_tu_clave":
        raise ValueError("Falta configurar GROQ_API_KEY.")

    if isinstance(context, dict):
        context_text = json.dumps(context, ensure_ascii=False, default=str)
    elif isinstance(context, str):
        context_text = context.strip()
    else:
        raise ValueError("context debe ser texto o un diccionario.")
    if not context_text:
        raise ValueError("context no puede estar vacío.")

    prompt = (
        "Analiza la imagen adjunta usando el contexto solo como información de apoyo. "
        "Describe únicamente patrones visuales observables, comparaciones, tendencias, "
        "legibilidad, escala, etiquetas ausentes y ambigüedades. No inventes valores ni "
        "atribuyas causalidad. Si se facilitan cifras fuente, no afirmes que son correctas "
        "solo por aparecer en el contexto; indica cualquier discrepancia que sea visible. "
        "No infieras la calidad, capacidad ni seguridad real de un negocio a partir de "
        "un gráfico. Devuelve exclusivamente un objeto JSON con las claves "
        "observation (texto) y limitations (lista de textos). Escribe en español.\n\n"
        f"Contexto del gráfico y datos de origen:\n{context_text}"
    )

    try:
        response = litellm.completion(
            model=selected_model,
            api_key=api_key,
            temperature=0,
            timeout=60,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
    except Exception as exc:
        logger.exception("Falló el análisis visual con %s", selected_model)
        raise RuntimeError(
            f"Error al solicitar el análisis visual al modelo {selected_model}."
        ) from exc

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise ValueError("La respuesta del proveedor visual tiene un formato inesperado.") from exc

    parsed = _parse_json_response(content)
    observation = parsed.get("observation")
    limitations = parsed.get("limitations", [])
    if not isinstance(observation, str) or not observation.strip():
        raise ValueError("La respuesta visual debe incluir una observación no vacía.")
    if not isinstance(limitations, list) or any(not isinstance(item, str) for item in limitations):
        raise ValueError("limitations debe ser una lista de textos.")

    return ImageObservation(
        image_id=image_id or path.stem,
        source_image_path=str(path),
        source_artifact_id=source_artifact_id,
        model_used=selected_model,
        observation=observation.strip(),
        limitations=[item.strip() for item in limitations if item.strip()],
        processed_file_path=str(path),
    )


def append_image_observations_to_report(
    draft: "ReportDraft",
    observations: list[ImageObservation],
) -> "ReportDraft":
    """Añade observaciones visuales al borrador sin convertirlas en hechos verificados."""

    if not observations:
        return draft

    from src.reporting.templates import MISSING_SECTION_TEXT

    heading = "Análisis visual"
    entries = [heading]
    for item in observations:
        entries.append(
            f"### Imagen: {item.image_id}\n"
            f"Observación asistida por IA: {item.observation}\n"
            f"Artefacto de origen: {item.source_artifact_id or 'No indicado'}\n"
            f"Archivo: {item.processed_file_path}\n"
            f"Modelo utilizado: {item.model_used}"
        )
        for limitation in item.limitations:
            note = f"Limitación del análisis visual ({item.image_id}): {limitation}"
            if note not in draft.limitations:
                draft.limitations.append(note)

    section_text = "\n\n".join(entries)
    existing_index = next(
        (index for index, section in enumerate(draft.sections)
         if section.strip().splitlines()[0:1] == [heading]),
        None,
    )
    if existing_index is None:
        draft.sections.append(section_text)
    else:
        existing_section = draft.sections[existing_index]
        _, _, body = existing_section.strip().partition("\n")
        if body.strip() == MISSING_SECTION_TEXT:
            existing_section = heading
        additions = [entry for entry in entries[1:] if entry not in existing_section]
        if additions:
            draft.sections[existing_index] = existing_section.rstrip() + "\n\n" + "\n\n".join(additions)
    return draft
