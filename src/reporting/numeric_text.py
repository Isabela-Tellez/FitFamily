"""Texto numérico mediante marcadores compartidos por Markdown y PDF."""
import re
from decimal import Decimal
from src.review.models import ReviewIssue

TEMPLATE = "Resultado documentado: {{value}} {{unit}}."
CLAIM_TOKEN = re.compile(r"\{\{claim:([^{}]+)\}\}")
# Control conservador: las cifras literales deben convertirse a referencias.
NUMBER = re.compile(r"\d|\b(?:cero|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciséis|diecisiete|dieciocho|diecinueve|veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|trescientos|mil|millón|millones|doble|triple|mitad)\b", re.I)


def is_numeric(claim):
    return any(v is not None for v in (claim.metric_id, claim.reported_value, claim.reported_unit))


def render_claim(claim):
    if not is_numeric(claim):
        return claim.text
    claim.__post_init__()
    if claim.text != TEMPLATE:
        raise ValueError("La afirmación numérica debe usar la plantilla de cifras: " + claim.claim_id)
    value = format(Decimal(str(claim.reported_value)), "f").rstrip("0").rstrip(".") if "." in str(claim.reported_value) else str(claim.reported_value)
    return TEMPLATE.replace("{{value}}", value or "0").replace("{{unit}}", claim.reported_unit)


def render_section(text, claims):
    index = {c.claim_id: c for c in claims}
    def replace(match):
        identifier = match.group(1)
        if identifier not in index:
            raise ValueError("Referencia de afirmación inexistente: " + identifier)
        return render_claim(index[identifier])
    result = CLAIM_TOKEN.sub(replace, text)
    if "{{" in result or "}}" in result:
        raise ValueError("Marcador de cifra desconocido.")
    return result


def validate_numeric_text(draft):
    issues = []
    def add(reference, message):
        issues.append(ReviewIssue(
            code="uncontrolled_numeric_text", reference_id=reference,
            message=message, severity="error", correction_stage="writing",
        ))
    ids = {c.claim_id for c in draft.claims}
    for claim in draft.claims:
        if is_numeric(claim):
            if claim.text != TEMPLATE:
                add(claim.claim_id, "Utiliza la plantilla numérica; no copies el importe en texto.")
        elif NUMBER.search(claim.text) or "{{" in claim.text or "}}" in claim.text:
            add(claim.claim_id, "Cifra o marcador sin indicador estructurado.")
    for position, section in enumerate(draft.sections):
        for match in CLAIM_TOKEN.finditer(section):
            if match.group(1) not in ids:
                add(str(position), "La sección cita una afirmación inexistente.")
        plain = CLAIM_TOKEN.sub("", section)
        if NUMBER.search(plain) or "{{" in plain or "}}" in plain:
            add(str(position), "La sección contiene cifras sin referencia a una afirmación.")
    # Título, zona y limitaciones también son visibles: no se omiten del control.
    for label, text in [("title", draft.title), ("study_area", draft.study_area), *(
        ("limitation", text) for text in draft.limitations
    )]:
        if NUMBER.search(text) or "{{" in text or "}}" in text:
            add(label, "Texto visible con cifras literales; requiere reformulación y revisión.")
    return issues
