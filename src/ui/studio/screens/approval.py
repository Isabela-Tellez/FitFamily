"""Pantalla: Aprobación y entrega.

Revisión del informe, decisión humana y entrega de los formatos
autorizados. La decisión se registra mediante el controlador público
`resume_run` (src.runtime.controller), de modo que `approval_node`
valida versión, huella y errores antes de crear el ApprovalRecord, y
`delivery_node` ejecuta únicamente las acciones autorizadas.

La aprobación no equivale a entrega completada: el resultado mostrado
es exactamente el DeliveryResult devuelto por el workflow.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.automation.exporter import calculate_draft_fingerprint
from src.ui.controller import (
    delivery_from_state,
    draft_from_state,
    metrics_from_state,
    research_from_state,
    review_from_state,
    validate_review_context,
)
from src.ui.report_preview import render_report_preview
from src.ui.studio import services
from src.ui.studio.components import (
    empty_state,
    page_header,
    render_metrics,
    section_header,
)
from src.ui.studio.state import get_state, redact_secrets

ROOT = Path(__file__).resolve().parents[4]


def _review_bundle():
    """Reconstruye borrador + research + métricas + revisión del estado."""
    state = get_state()
    if not state or not state.get("report_draft") or not state.get("review_result"):
        return None
    draft = draft_from_state(state["report_draft"])
    research = research_from_state(state["research_result"])
    metrics = metrics_from_state(state.get("analysis_result"))
    review = review_from_state(state["review_result"])
    validate_review_context(draft=draft, research=research, metrics=metrics, review=review)
    return draft, research, metrics, review


def _render_delivery(state: dict, run_id: str) -> None:
    """Muestra la entrega real registrada en el estado (sin inventar nada)."""
    delivery = delivery_from_state(state.get("delivery_result"))

    if delivery is None:
        st.info(
            "Todavía no hay resultado de entrega registrado. Genera los "
            "entregables autorizados para ver su estado real."
        )
        if st.button(
            "Generar / reintentar entregables autorizados",
            type="primary",
            use_container_width=True,
        ):
            try:
                services.retry_delivery(run_id)
                st.session_state["ff_state"] = services.load_study(run_id)
                st.rerun()
            except Exception as exc:
                st.error(f"La entrega no se ha completado: {redact_secrets(exc)}")
        return

    if delivery.complete:
        st.success("Todas las acciones autorizadas se han completado correctamente.")
    else:
        st.warning(
            "Entrega parcial o fallida: revisa los errores y vuelve a "
            "intentar las acciones pendientes."
        )

    cols = st.columns(3)
    cols[0].metric("Solicitadas", len(delivery.requested_actions))
    cols[1].metric("Completadas", len(delivery.completed_actions))
    cols[2].metric("Fallidas", len(delivery.failed_actions))

    # Solo se muestran acciones realmente ejecutadas.
    if delivery.completed_actions:
        st.caption(
            "Completadas: " + ", ".join(str(a) for a in delivery.completed_actions)
        )
    if delivery.failed_actions:
        st.caption(
            "Fallidas: " + ", ".join(str(a) for a in delivery.failed_actions)
        )

    # Descargas solo cuando el archivo existe realmente en disco.
    downloaded = False
    for action, path in (
        ("Markdown", delivery.markdown_path),
        ("PDF", delivery.pdf_path),
        ("Seguimiento CSV", delivery.tracking_path),
    ):
        if not path:
            continue
        file_path = Path(path)
        if not file_path.is_file():
            continue
        mime = (
            "text/markdown"
            if file_path.suffix == ".md"
            else "application/pdf"
            if file_path.suffix == ".pdf"
            else "text/csv"
        )
        downloaded = True
        st.download_button(
            f"Descargar {action} ({file_path.name})",
            data=file_path.read_bytes(),
            file_name=file_path.name,
            mime=mime,
            key=f"download_{file_path.suffix}_{file_path.name}",
        )
    if not downloaded and delivery.complete:
        st.caption("La entrega se registró pero no hay archivos locales disponibles.")

    for action, message in delivery.errors or ():
        st.error(f"{action}: {redact_secrets(message)}")

    if st.button("Reintentar entrega autorizada"):
        try:
            services.retry_delivery(run_id)
            st.session_state["ff_state"] = services.load_study(run_id)
            st.rerun()
        except Exception as exc:
            st.error(f"La entrega no se ha completado: {redact_secrets(exc)}")


def render() -> None:
    page_header(
        "Aprobación y entrega",
        "Revisa el informe, registra tu decisión y genera únicamente "
        "los formatos autorizados.",
        eyebrow="CONTROL HUMANO Y ENTREGA",
    )

    # Aviso persistente tras el rerun de la decisión humana.
    notice = st.session_state.pop("ff_notice", None)
    if notice:
        kind, message = notice
        getattr(st, kind if kind in ("success", "warning", "error") else "info")(message)

    state = get_state()
    run_id = st.session_state.get("ff_run_id")

    try:
        bundle = _review_bundle()
    except Exception as exc:
        st.error(
            "La revisión ya no corresponde al contenido actual: "
            f"{redact_secrets(exc)}. Ejecuta un nuevo estudio antes de aprobar."
        )
        bundle = None

    if not bundle or not state or not run_id:
        empty_state(
            "Sin informe pendiente de aprobación",
            "Esta pantalla se habilita cuando el workflow ha producido un "
            "borrador y una revisión. Ejecuta primero un estudio real.",
            action_label="Ir a Nuevo estudio",
        )
        return

    draft, research, metrics, review = bundle
    errors = [i for i in review.issues if i.severity == "error"]
    warnings = [i for i in review.issues if i.severity == "warning"]
    preview = render_report_preview(draft)
    approval = state.get("approval_record")
    awaiting = state.get("status") == "awaiting_approval"

    render_metrics(
        [
            ("Documento", draft.draft_id[:12], "Identidad del borrador"),
            ("Versión", str(draft.version), "Versión vigente"),
            ("Errores bloqueantes", str(len(errors)), "Impiden la aprobación"),
        ],
        columns=3,
    )
    st.write("")

    section_header("Confirmación del contenido")
    with st.expander("Abrir informe completo antes de decidir", expanded=True):
        st.markdown(preview.markdown)

    if warnings:
        with st.expander(f"Avisos informativos ({len(warnings)})"):
            for issue in warnings:
                st.warning(f"{issue.code}: {issue.message}")

    if errors:
        st.error("La aprobación está bloqueada hasta corregir todos los errores de revisión.")
        for issue in errors:
            st.markdown(
                f"- **{issue.code}** · {issue.message} · etapa: `{issue.correction_stage}`"
            )

    # ---- Decisión humana (solicita el workflow) ----
    if awaiting:
        st.divider()
        section_header("Tu decisión")
        st.caption(
            f"Versión sometida a decisión: `{state.get('report_version_id')}` · "
            "la decisión se registra sobre exactamente esta versión."
        )
        with st.form("ff_human_approval"):
            decision = st.radio(
                "Decisión", ["Aprobar para exportar", "Rechazar informe"], horizontal=True
            )
            confirm_read = st.checkbox(
                "He leído el informe, las fuentes y las limitaciones mostradas."
            )
            st.markdown("**Acciones que autorizo**")
            blocked = bool(errors) or decision.startswith("Rechazar")
            export_md = st.checkbox("Exportar Markdown (.md)", value=True, disabled=blocked)
            export_pdf = st.checkbox("Exportar PDF (.pdf)", value=False, disabled=blocked)
            update_csv = st.checkbox("Actualizar CSV de seguimiento", value=False, disabled=blocked)
            submit = st.form_submit_button(
                "Registrar decisión humana", type="primary", use_container_width=True
            )

        if submit:
            if not confirm_read:
                st.error(
                    "Confirma que has leído el informe y sus limitaciones "
                    "antes de registrar la decisión."
                )
            else:
                approved = decision.startswith("Aprobar")
                chosen: list[str] = []
                if approved:
                    if export_md:
                        chosen.append("export_markdown")
                    if export_pdf:
                        chosen.append("export_pdf")
                    if update_csv:
                        chosen.append("update_tracking_csv")
                try:
                    new_state, _delivery = services.decide_approval(
                        run_id=run_id,
                        report_version_id=state.get("report_version_id") or "",
                        decision="approved" if approved else "rejected",
                        actions=chosen,
                    )
                    st.session_state["ff_state"] = new_state
                    if approved:
                        st.session_state["ff_notice"] = (
                            "success",
                            "Aprobación registrada sobre la versión mostrada. "
                            "La entrega se ejecuta a continuación.",
                        )
                    else:
                        st.session_state["ff_notice"] = (
                            "warning",
                            "Rechazo registrado. No se podrá exportar este informe.",
                        )
                    st.rerun()
                except Exception as exc:
                    st.error(f"No se pudo registrar la decisión: {redact_secrets(exc)}")

    elif approval:
        st.write("")
        if approval.get("approved"):
            st.markdown(
                '<span class="ff-badge ff-badge-ok">Aprobación registrada</span>',
                unsafe_allow_html=True,
            )
            st.caption(
                f"Decidida: {approval.get('decided_at')} · "
                f"Versión: {state.get('approved_version_id') or '—'}"
            )
        else:
            st.markdown(
                '<span class="ff-badge ff-badge-warn">Informe rechazado</span>',
                unsafe_allow_html=True,
            )
            st.caption("No se autoriza ninguna exportación de este informe.")

    # ---- Publicación controlada ----
    if approval and approval.get("approved"):
        st.divider()
        section_header("Publicación controlada")
        st.caption(
            "Acciones autorizadas: " + ", ".join(approval.get("actions") or [])
        )
        _render_delivery(state, run_id)
    elif approval and not approval.get("approved"):
        st.info("Informe rechazado: no hay entregas disponibles para esta versión.")
