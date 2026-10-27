"""Enlace explícito de los resultados de análisis al redactor determinista."""
from decimal import Decimal
from src.reporting.models import ReportClaim
from src.reporting.numeric_text import TEMPLATE
from src.analysis.provenance import validate_metric_provenance


def bind_metrics(draft, research, metrics):
    issues = validate_metric_provenance(metrics, research)
    if issues:
        raise ValueError("; ".join(i.message for i in issues))
    if len({m.metric_id for m in metrics}) != len(metrics):
        raise ValueError("Identificador de indicador duplicado.")
    used = set()
    for claim in draft.claims:
        matches = [m for m in metrics if m.calculation == "evidence_value"
                   and set(m.evidence_ids) == set(claim.evidence_ids)]
        if len(matches) == 1:
            metric = matches[0]
            original = claim.text
            value = float(metric.value)
            if Decimal(str(value)) != metric.value:
                raise ValueError("El valor no se representa sin pérdida en ReportClaim.")
            claim.metric_id = metric.metric_id
            claim.reported_value = value
            claim.reported_unit = metric.unit
            claim.text = TEMPLATE
            claim.__post_init__()
            # El Writer determinista había copiado la misma observación en sections.
            draft.sections = [s.replace(original, "{{claim:" + claim.claim_id + "}}")
                              for s in draft.sections]
            used.add(metric.metric_id)
    for metric in metrics:
        if metric.metric_id in used:
            continue
        value = float(metric.value)
        if Decimal(str(value)) != metric.value:
            raise ValueError("El valor no se representa sin pérdida en ReportClaim.")
        identifier = "numeric_" + str(len(draft.claims) + 1)
        while any(c.claim_id == identifier for c in draft.claims):
            identifier += "_"
        draft.claims.append(ReportClaim(
            claim_id=identifier, text=TEMPLATE, kind="inference",
            evidence_ids=list(metric.evidence_ids), metric_id=metric.metric_id,
            reported_value=value, reported_unit=metric.unit,
        ))
        draft.sections.append("Indicador documentado\n{{claim:" + identifier + "}}")
    # Una sola fuente de texto: no conservamos copias independientes de tarifas
    # en las secciones que había producido el Writer determinista.
    draft.sections = ["Resultados documentados\n" + "\n".join(
        "{{claim:" + claim.claim_id + "}}" for claim in draft.claims
    )]
    draft.limitations.append(
        "Este informe presenta los indicadores documentados recibidos; "
        "no demuestra representatividad del mercado ni veracidad de las fuentes."
    )
    return draft
