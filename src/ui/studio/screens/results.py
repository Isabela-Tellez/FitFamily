"""Pantalla: Resultados.

Organiza la información del estudio ejecutado: resumen, competidores,
tarifas, fuentes e informe. Todos los datos provienen del estado
guardado; abrir la pantalla no vuelve a investigar.
"""
from __future__ import annotations

import streamlit as st

from src.ui.controller import (
    metrics_from_state,
    research_from_state,
    review_from_state,
)
from src.ui.studio import copy, services
from src.ui.studio.components import (
    empty_state,
    page_header,
    render_metrics,
    render_steps,
    render_table,
    section_header,
)
from src.ui.studio.formatting import (
    format_datetime,
    format_euro,
    format_time,
    humanize,
    scenario_label,
    status_label,
)
from src.ui.studio.state import format_value, get_state


def _evidence_items(research):
    """Agrupa evidencias de la investigación y de cada competidor (sin duplicados)."""
    if not research:
        return []
    items = list(research.evidences)
    seen = {item.evidence_id for item in items}
    for competitor in research.competitors:
        for evidence in competitor.evidences:
            if evidence.evidence_id not in seen:
                items.append(evidence)
                seen.add(evidence.evidence_id)
    return items


def _verification_label(value: object) -> str:
    text = str(value or "").strip().lower()
    if text == "verified":
        return "Verificado"
    if text == "unverified":
        return "Sin verificar"
    return "No disponible"


_METRIC_LABELS = {
    "monthly_revenue": "Ingresos mensuales previstos",
    "monthly_variable_costs": "Costes variables mensuales",
    "monthly_result": "Resultado mensual",
    "break_even_clients": "Punto de equilibrio",
}
_UNIT_LABELS = {
    "EUR/month": "€/mes",
    "clients": "clientes",
}


def _metric_label(metric_id: str) -> str:
    suffix = str(metric_id or "").rsplit(".", 1)[-1]
    return _METRIC_LABELS.get(suffix, "Resultado del escenario")


def _human_metric_rows(metrics) -> list[dict[str, str]]:
    """Resumen económico legible; los identificadores quedan en técnicos."""
    rows = []
    for metric in metrics:
        unit = _UNIT_LABELS.get(str(metric.unit or ""), "—")
        rows.append(
            {
                "Indicador": _metric_label(metric.metric_id),
                "Escenario": (
                    f"{scenario_label(metric.context.scenario.scenario_type)} · "
                    f"{metric.context.scenario.expected_clients} clientes"
                    if metric.context
                    else "No disponible"
                ),
                "Resultado": (
                    format_value(float(metric.value))
                    if metric.value is not None
                    else "No disponible"
                ),
                "Unidad": unit,
                "Lectura": (
                    "Calculado con tus supuestos"
                    if metric.context and metric.context.scenario.assumptions
                    else "Calculado sin supuestos declarados"
                ),
            }
        )
    return rows


def _render_events(run_id: str | None) -> None:
    """Evolución real del proceso, en lenguaje humano y hora de Madrid."""
    if not run_id:
        st.caption("Sin evolución registrada para este estudio.")
        return
    try:
        events = services.run_events(run_id)
    except Exception as exc:
        st.warning(f"No se pudo leer la evolución del proceso: {humanize(exc)}")
        return
    if not events:
        st.caption("Este estudio no registró eventos de proceso.")
        return
    for event in events:
        st.markdown(
            f"- `{format_time(event.get('timestamp'))}` · "
            f"**{status_label(event.get('stage'))}** · "
            f"{humanize(event.get('message'))}"
        )


def _tariff_rows(research) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not research:
        return rows
    for competitor in research.competitors:
        source = competitor.evidences[0].source_url if competitor.evidences else ""
        for tariff in competitor.tariffs:
            value = tariff.get("value")
            rows.append(
                {
                    "Competidor": competitor.name or "No disponible",
                    "Tarifa": humanize(tariff.get("condition") or "Tarifa sin detalle"),
                    "Precio": format_euro(value) if value is not None else "No disponible",
                    "Frecuencia": humanize(tariff.get("frequency") or "—"),
                    "Fuente": source,
                }
            )
    return rows


def _source_rows(evidence_items) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for evidence in evidence_items:
        url = evidence.source_url or "Sin enlace"
        entry = grouped.setdefault(
            url,
            {
                "Fuente": url,
                "Fecha observada": format_datetime(evidence.date_observed),
                "Evidencias": 0,
                "Limitaciones": "",
            },
        )
        entry["Evidencias"] = int(entry["Evidencias"]) + 1
        if evidence.limitations and not entry["Limitaciones"]:
            entry["Limitaciones"] = humanize(evidence.limitations)
    return list(grouped.values())


def render() -> None:
    state = get_state()
    if not state:
        empty_state(
            copy.TEXTS["results.empty_title"],
            copy.TEXTS["results.empty_body"],
            action_label=copy.TEXTS["action.back_to_new_study"],
            page="Nuevo estudio",
        )
        return

    page_header(
        copy.TEXTS["results.title"],
        copy.TEXTS["results.subtitle"],
        eyebrow="ANÁLISIS Y RESULTADOS",
    )
    st.write("")

    research = research_from_state(state["research_result"]) if state.get("research_result") else None
    review = review_from_state(state["review_result"]) if state.get("review_result") else None
    metrics = metrics_from_state(state.get("analysis_result"))
    evidence_items = _evidence_items(research)

    run_id = st.session_state.get("ff_run_id")
    events = services.run_events(run_id) if run_id else []
    last_update = format_datetime(events[-1].get("timestamp")) if events else "No disponible"
    st.caption(f"Actualizado el {last_update}.")

    render_metrics(
        [
            (
                copy.TEXTS["results.metrics_evidence"],
                str(len(evidence_items)),
                "Fragmentos con fuente asociada",
            ),
            (
                copy.TEXTS["results.metrics_competitors"],
                str(len(research.competitors) if research else 0),
                "Estructurados en la búsqueda",
            ),
            (
                copy.TEXTS["results.metrics_indicators"],
                str(len(metrics)),
                "A partir de tus supuestos",
            ),
            (
                copy.TEXTS["results.metrics_issues"],
                str(len(review.issues) if review else 0),
                "Detectadas en la revisión",
            ),
        ],
        columns=4,
    )
    st.write("")

    # ---- Resumen y escenario ----
    section_header(
        copy.TEXTS["results.scenario_title"],
        copy.TEXTS["results.scenario_subtitle"],
    )
    if metrics:
        st.caption(
            "Cifras calculadas con los supuestos económicos del encargo. "
            "No son observaciones del mercado."
        )
        render_table(
            _human_metric_rows(metrics),
            empty_message="Sin métricas calculadas.",
        )
    else:
        st.info("Sin métricas calculadas. Añade supuestos económicos al iniciar un estudio.")

    with st.expander(copy.TEXTS["results.technical"]):
        if metrics:
            section_header("Trazabilidad de los cálculos")
            render_table(
                [
                    {
                        "Métrica": m.metric_id,
                        "Escenario": (
                            f"{scenario_label(m.context.scenario.scenario_type)} · "
                            f"{m.context.scenario.expected_clients} clientes"
                            if m.context
                            else "No disponible"
                        ),
                        "Resultado": (
                            format_value(float(m.value))
                            if m.value is not None
                            else "No disponible"
                        ),
                        "Unidad": m.unit,
                        "Cálculo": m.calculation,
                        "ID cálculo": (
                            m.context.calculation_result.calculation_id
                            if m.context
                            else "No disponible"
                        ),
                        "Limitaciones": (
                            "; ".join(m.context.calculation_result.limitations)
                            if m.context and m.context.calculation_result.limitations
                            else "Ninguna documentada"
                        ),
                    }
                    for m in metrics
                ],
                empty_message="Sin métricas calculadas.",
            )
        section_header("Progreso del estudio")
        render_steps(state)
        section_header(
            copy.TEXTS["results.events_title"],
            "Eventos reales registrados durante la ejecución.",
        )
        _render_events(run_id)

    st.write("")
    tab_competitors, tab_tariffs, tab_sources = st.tabs(
        [
            copy.TEXTS["results.tab_competitors"],
            copy.TEXTS["results.tab_tariffs"],
            copy.TEXTS["results.tab_sources"],
        ]
    )

    # ---- Competidores ----
    with tab_competitors:
        if research and research.competitors:
            st.caption(
                "«No disponible» significa que la fuente no permitió verificar "
                "ese campo; no equivale a «no»."
            )
            render_table(
                [
                    {
                        "Competidor": item.name or "Nombre no disponible",
                        "Ubicación": item.location or "No disponible",
                        "Servicios declarados": ", ".join(item.services) if item.services else "No disponible",
                        "Ludoteca": (
                            "Sí" if item.has_playroom is True
                            else "No" if item.has_playroom is False
                            else "No disponible"
                        ),
                        "Verificación": _verification_label(item.verification_status),
                    }
                    for item in research.competitors
                ],
                empty_message="La búsqueda no devolvió competidores estructurados.",
            )
        else:
            empty_state(
                "Sin competidores estructurados",
                "La búsqueda no devolvió competidores con estructura utilizable. "
                "Revisa las preguntas del estudio o aumenta el máximo de resultados.",
            )

    # ---- Tarifas ----
    with tab_tariffs:
        rows = _tariff_rows(research)
        if rows:
            st.caption("Precios publicados por los competidores cuando la fuente los ofrece.")
            render_table(
                rows,
                empty_message="Sin tarifas registradas.",
                column_config={
                    "Fuente": st.column_config.LinkColumn(
                        "Fuente",
                        display_text="Abrir fuente",
                        width="medium",
                    )
                },
            )
        else:
            empty_state(
                "Sin tarifas verificadas",
                "La investigación no encontró precios publicados con fuente utilizable. "
                "Esto no significa que no existan: significa que no se pudieron verificar.",
            )

    # ---- Fuentes ----
    with tab_sources:
        rows = _source_rows(evidence_items)
        if rows:
            st.caption("Cada fuente conserva la fecha en que se consultó y sus limitaciones.")
            render_table(
                rows,
                empty_message="Sin fuentes asociadas.",
                column_config={
                    "Fuente": st.column_config.LinkColumn(
                        "Fuente",
                        display_text="Abrir fuente",
                        width="medium",
                    )
                },
            )
        else:
            empty_state(
                "Sin fuentes recuperadas",
                "La investigación no aportó evidencias con enlace verificable. "
                "Ejecuta un nuevo estudio con preguntas más concretas.",
            )

    if review and review.issues:
        st.write("")
        section_header("Revisión automática")
        for issue in review.issues:
            if issue.severity == "error":
                st.error(humanize(issue.message))
            else:
                st.warning(humanize(issue.message))
        with st.expander(copy.TEXTS["results.technical"]):
            for issue in review.issues:
                st.code(
                    f"{issue.code} · {issue.reference_id} · {issue.correction_stage}",
                    language="text",
                )
    elif review:
        st.write("")
        st.success(
            "La revisión automática no ha detectado errores bloqueantes. "
            "Esto no sustituye la lectura humana ni acredita la veracidad "
            "semántica de las fuentes."
        )
