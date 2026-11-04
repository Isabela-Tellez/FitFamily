"""Pantalla: Resultados.

Organiza la información del workflow ejecutado: indicadores principales,
competidores, evidencias, escenario calculado, informe y revisión.
Todos los datos provienen del estado guardado; no se re-investiga.
"""
from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

from src.ui.controller import (
    draft_from_state,
    metrics_from_state,
    research_from_state,
    review_from_state,
)
from src.ui.report_preview import render_report_preview
from src.ui.studio import services
from src.ui.studio.components import (
    empty_state,
    format_values,
    page_header,
    render_metrics,
    render_steps,
    render_table,
    section_header,
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


def _render_events(run_id: str | None) -> None:
    """Evolución real del proceso: eventos registrados por el workflow."""
    if not run_id:
        st.caption("Sin identificador de ejecución disponible.")
        return
    try:
        events = services.run_events(run_id)
    except Exception as exc:
        st.warning(f"No se pudo leer la evolución del proceso: {exc}")
        return
    if not events:
        st.caption("Este flujo no registró eventos para esta ejecución.")
        return
    for event in events:
        st.markdown(
            f"- `{str(event.get('timestamp', ''))[11:19]}` · "
            f"**{event.get('stage', '—')}** · {event.get('message', '')}"
        )


def render() -> None:
    state = get_state()
    if not state:
        empty_state(
            "Todavía no hay resultados",
            "Esta pantalla muestra el resultado de una ejecución real del workflow. "
            "Empieza un nuevo estudio para generar datos.",
            action_label="Ir a Nuevo estudio",
        )
        return

    page_header(
        "Resultados del estudio",
        "Información procedente de la ejecución guardada del workflow; "
        "no se vuelve a investigar al abrir esta pantalla.",
        eyebrow="ANÁLISIS Y RESULTADOS",
    )

    draft = draft_from_state(state["report_draft"]) if state.get("report_draft") else None
    research = research_from_state(state["research_result"]) if state.get("research_result") else None
    review = review_from_state(state["review_result"]) if state.get("review_result") else None
    metrics = metrics_from_state(state.get("analysis_result"))
    evidence_items = _evidence_items(research)

    verified_note = (
        "Proveedor Tavily" if os.getenv("TAVILY_API_KEY")
        else "Proveedor de búsqueda alternativo (DDGS si está disponible)"
    )

    # ---- Indicadores principales ----
    render_metrics(
        [
            ("Evidencias recuperadas", str(len(evidence_items)), "Fragmentos con fuente asociada"),
            ("Competidores", str(len(research.competitors) if research else 0), "Estructurados en la búsqueda"),
            ("Indicadores calculados", str(len(metrics)), "A partir de tus supuestos"),
            ("Incidencias", str(len(review.issues) if review else 0), "Detectadas en la revisión"),
        ],
        columns=4,
    )
    st.caption(
        f"{verified_note} · Ejecución {st.session_state.get('ff_run_id')} · "
        f"Estado {state.get('status', '—')}"
    )
    st.write("")

    tab_summary, tab_competitors, tab_evidence, tab_report = st.tabs(
        ["Resumen", "Competidores", "Evidencias", "Informe y revisión"]
    )

    # ---- Resumen ----
    with tab_summary:
        section_header("Progreso del workflow")
        render_steps(state)

        section_header(
            "Evolución del proceso",
            "Eventos reales registrados por el workflow durante la ejecución.",
        )
        _render_events(st.session_state.get("ff_run_id"))

        if research:
            section_header("Método de investigación")
            st.write(research.search_performed or "El módulo no devolvió un resumen del método.")
            if research.notes:
                st.caption(research.notes)
            if research.unresolved_questions:
                section_header("Preguntas pendientes")
                for question in research.unresolved_questions:
                    st.markdown(f"- {question}")

        analysis = state.get("analysis_result") or {}
        if analysis.get("limitations"):
            section_header("Alcance del análisis económico")
            for limitation in analysis["limitations"]:
                st.markdown(f"- {limitation}")

        if metrics:
            section_header(
                "Escenario calculado",
                "Resultado de los supuestos introducidos en el encargo; "
                "no son observaciones de mercado. Varias filas permiten "
                "comparar escenarios cuando existen varios.",
            )
            render_table(
                [
                    {
                        "Métrica": m.metric_id,
                        "Escenario": (
                            f"{m.context.scenario.scenario_type} · "
                            f"{m.context.scenario.expected_clients} clientes"
                            if m.context
                            else "No disponible"
                        ),
                        "Resultado": format_value(float(m.value)) if m.value is not None else "No disponible",
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
                empty_message="Sin métricas calculadas (no se introdujeron supuestos económicos).",
            )
            st.caption(
                "«No disponible» nunca equivale a cero: cada valor conserva su "
                "unidad, su identificador de cálculo y las limitaciones declaradas."
            )

    # ---- Competidores ----
    with tab_competitors:
        if research and research.competitors:
            section_header(
                "Competidores detectados",
                "«No disponible» significa que la fuente no permitió verificar ese campo; "
                "no equivale a «no».",
            )
            render_table(
                [
                    {
                        "Competidor": item.name or "Nombre no disponible",
                        "Ubicación": item.location or "No disponible",
                        "Servicios declarados": ", ".join(item.services) if item.services else "No disponible",
                        "Tarifas registradas": json.dumps(item.tariffs, ensure_ascii=False) if item.tariffs else "No disponible",
                        "Ludoteca": "Sí" if item.has_playroom is True else "No" if item.has_playroom is False else "No disponible",
                        "Verificación": item.verification_status or "No disponible",
                    }
                    for item in research.competitors
                ],
                empty_message="La búsqueda no devolvió competidores estructurados. Revisa el método y las preguntas pendientes.",
            )
        else:
            from src.ui.studio.components import empty_state as _es
            _es(
                "Sin competidores estructurados",
                "La búsqueda no devolvió competidores con estructura utilizable. "
                "Revisa las preguntas del estudio o aumenta el máximo de resultados.",
            )

    # ---- Evidencias ----
    with tab_evidence:
        if evidence_items:
            section_header(
                "Evidencias con trazabilidad",
                "Cada fragmento conserva su fuente, fecha y limitaciones.",
            )
            render_table(
                [
                    {
                        "ID": item.evidence_id,
                        "Afirmación / fragmento": item.claim,
                        "Extracto": item.snippet or "—",
                        "URL": item.source_url or "—",
                        "Fecha observada": item.date_observed or "—",
                        "Limitaciones": item.limitations or "—",
                    }
                    for item in evidence_items
                ],
                empty_message="Sin evidencias.",
                height=440,
            )
        else:
            from src.ui.studio.components import empty_state as _es
            _es(
                "Sin evidencias recuperadas",
                "El flujo no habilita aprobación si la investigación no aporta "
                "evidencia utilizable. Ejecuta un nuevo estudio con preguntas más concretas.",
            )

    # ---- Informe y revisión ----
    with tab_report:
        if draft:
            preview = render_report_preview(draft)
            section_header("Informe", f"{preview.draft_id} · versión {preview.draft_version}")
            st.markdown(preview.markdown)
            with st.expander("Trazabilidad e identidad del documento"):
                st.code(preview.draft_fingerprint, language="text")
                st.caption(
                    "La huella se calcula sobre el ReportDraft real mostrado. "
                    "Cualquier cambio invalida la aprobación previa."
                )
        else:
            from src.ui.studio.components import empty_state as _es
            _es(
                "Sin borrador de informe",
                "El workflow aún no ha producido un borrador. Revisa el progreso en la pestaña Resumen.",
            )

        if review:
            st.divider()
            section_header("Revisión automática")
            st.markdown(
                f"Estado: **{review.status}** · "
                f"Comprobaciones: {', '.join(review.checks_performed) or '—'}"
            )
            if review.issues:
                for issue in review.issues:
                    icon = "⛔" if issue.severity == "error" else "⚠️"
                    st.markdown(
                        f"{icon} **{issue.code}** · {issue.message}  \n"
                        f"Referencia: `{issue.reference_id}` · Corrección: `{issue.correction_stage}`"
                    )
            else:
                st.success(
                    "La revisión automática no ha detectado errores bloqueantes. "
                    "Esto no sustituye la lectura humana ni acredita la veracidad semántica de las fuentes."
                )
