"""Demo local de revisión FitFamily. Datos ficticios, sin API ni exportaciones."""
import argparse
from copy import deepcopy
from decimal import Decimal

from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.analysis.calculation_adapter import metric_from_break_even
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.reporting.templates import validate_report_sections
from src.reporting.markdown_renderer import render_report_markdown
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult


def require(condition, message):
    if not condition:
        raise RuntimeError("La demo no cumple el contrato esperado: " + message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true",
                        help="Muestra al final la vista previa completa en Markdown.")
    args = parser.parse_args()
    print("DEMO FICTICIA — no representa un estudio real ni una aprobación.\n", flush=True)
    scenario = create_economic_scenario(
        "intermediate", 100, 50, 1000, 10,
        assumptions=["Cuota y costes hipotéticos para esta demostración."],
    )
    calculation = next(item for item in evaluate_economic_scenario(
        scenario, limitations=["No incluye impuestos ni estacionalidad."]
    ) if item.calculation_type == "break_even")
    metric = metric_from_break_even(scenario, calculation)
    research = ResearchResult()
    draft = build_report(
        ResearchBrief(business_type="gimnasio con ludoteca", location="Madrid",
                      study_area="Zona ficticia de demostración"),
        research, use_llm=False, calculated_metrics=[metric],
    )
    validate_report_sections(draft.sections)
    claim = next(c for c in draft.claims if c.metric_id == metric.metric_id)
    economic_section = next(s for s in draft.sections
                            if s.split("\n", 1)[0] == "Escenarios económicos")
    require(claim.text in economic_section, "punto de equilibrio en Escenarios económicos.")
    require(metric.value == Decimal("25"), "el cálculo real debe producir 25 clientes.")
    print("Entradas supuestas: costes fijos 1.000 EUR/mes; cuota 50 EUR/cliente/mes;")
    print("coste variable 10 EUR/cliente/mes. Resultado de la función de Laura: 25 clientes.")
    print("Indicador:", metric.metric_id)
    print("Texto generado por Gema:", claim.text, "\n")

    checked = run_basic_review(draft, research, calculated_metrics=[metric])
    route = choose_review_route_for_context(
        checked, draft, research, revision_count=0, calculated_metrics=[metric],
    )
    require(checked.issues == () and route == "pending_review", "caso correcto.")
    preview = render_report_markdown(draft)
    require(metric.metric_id in preview and "**Valor declarado:** 25.0" in preview
            and "**Unidad:** clients" in preview, "presentación numérica de Gema.")
    print("CASO 1 — Cifra correcta: pending_review.")
    print("Sin incidencias; sigue pendiente de revisión humana.\n")

    wrong = deepcopy(draft)
    altered = next(c for c in wrong.claims if c.metric_id == metric.metric_id)
    old_text = altered.text
    altered.reported_value = 30.0
    altered.text = old_text.replace("25 clientes", "30 clientes")
    wrong.sections = [s.replace(old_text, altered.text) for s in wrong.sections]
    wrong_review = run_basic_review(wrong, research, calculated_metrics=[metric])
    wrong_route = choose_review_route_for_context(
        wrong_review, wrong, research, revision_count=0, calculated_metrics=[metric],
    )
    require(any(i.code == "metric_value_mismatch" for i in wrong_review.issues)
            and wrong_route == "revise_writing", "caso de discrepancia.")
    print("CASO 2 — Informe alterado a 30; cálculo original 25: revise_writing.")
    for issue in wrong_review.issues:
        print(" ", issue.code + ":", issue.message)
    print()

    changed_scenario = scenario.model_copy(deep=True)
    changed_scenario.assumptions.append("Nuevo supuesto añadido después de revisar.")
    # Se reconstruye el adaptador desde los originales actuales.
    current_metric = metric_from_break_even(changed_scenario, calculation)
    try:
        choose_review_route_for_context(
            checked, draft, research, revision_count=0, calculated_metrics=[current_metric],
        )
    except ValueError as exc:
        require("análisis cambió" in str(exc), "rechazo por contexto de análisis modificado.")
        print("CASO 3 — Cambio de un supuesto: revisión anterior rechazada.")
        print(" ", str(exc))
    else:
        raise RuntimeError("La revisión obsoleta no fue rechazada.")
    print("\nTres casos comprobados. No se han creado aprobaciones ni exportado archivos.")
    print("Esta demo enlaza módulos reales; no ejecuta el workflow completo de Isabella.")
    if args.markdown:
        print("\nVISTA PREVIA DEL CASO CORRECTO — BORRADOR\n")
        print(preview)


if __name__ == "__main__":
    main()
