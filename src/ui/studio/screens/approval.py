"""Pantalla: Aprobación y entrega.

Vista previa del informe, lista de revisión y decisión humana. La
decisión se registra mediante el controlador público `resume_run`; la
interfaz no crea aprobaciones ni exporta por su cuenta.
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from src.ui.controller import (
    delivery_from_state,
    draft_from_state,
    metrics_from_state,
    research_from_state,
    review_from_state,
    validate_review_context,
)
from src.ui.report_preview import render_report_preview
from src.ui.studio import copy, services
from src.ui.studio.components import (
    badge,
    empty_state,
    page_header,
    render_metrics,
    section_header,
)
from src.ui.studio.formatting import format_datetime, humanize, status_label
from src.ui.studio.state import get_state, redact_secrets

ROOT = Path(__file__).resolve().parents[4]

_ACTION_LABELS = {
    "export_markdown": "Exportar Markdown (.md)",
    "export_pdf": "Exportar PDF (.pdf)",
    "update_tracking_csv": "Actualizar CSV de seguimiento",
}
_DOWNLOAD_LABELS = {
    "Markdown": "Descargar informe (Markdown)",
    "PDF": "Descargar informe (PDF)",
    "Seguimiento CSV": "Descargar seguimiento (CSV)",
}
_INTERNAL_ID_LINE = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*)?\s*"
    r"(identificador( del borrador)?|id( del borrador)?|huella|fingerprint|hash)"
    r"\b[^:\n]*:",
    re.IGNORECASE,
)


def _public_markdown(markdown: str) -> str:
    """Oculta identificadores internos en la vista previa del informe."""
    return "\n".join(
        line for line in markdown.splitlines() if not _INTERNAL_ID_LINE.match(line)
    )


def _review_bundle():
    """Reconstruye informe, investigación, métricas y revisión del estado."""
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
    """Muestra la entrega real registrada, sin inventar archivos."""
    delivery = delivery_from_state(state.get("delivery_result"))

    if delivery is None:
        st.info(
            "Todavía no hay entregables generados. Puedes crearlos cuando "
            "la aprobación esté registrada."
        )
        if st.button(
            "Generar entregables autorizados",
            type="primary",
            use_container_width=True,
            key="ff_generate_delivery",
        ):
            try:
                services.retry_delivery(run_id)
                st.session_state["ff_state"] = services.load_study(run_id)
                st.rerun()
            except Exception as exc:
                st.error(f"La entrega no se ha completado: {humanize(redact_secrets(exc))}")
        return

    if delivery.complete:
        st.success("Todas las acciones autorizadas se han completado correctamente.")
    else:
        st.warning(
            "La entrega está incompleta. Revisa los errores y vuelve a intentar "
            "las acciones pendientes."
        )

    cols = st.columns(3)
    cols[0].metric("Solicitadas", len(delivery.requested_actions), border=True)
    cols[1].metric("Completadas", len(delivery.completed_actions), border=True)
    cols[2].metric("Fallidas", len(delivery.failed_actions), border=True)

    if delivery.completed_actions:
        labels = [_ACTION_LABELS.get(str(a), str(a)) for a in delivery.completed_actions]
        st.caption("Completadas: " + ", ".join(labels))
    if delivery.failed_actions:
        labels = [_ACTION_LABELS.get(str(a), str(a)) for a in delivery.failed_actions]
        st.caption("Fallidas: " + ", ".join(labels))

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
            _DOWNLOAD_LABELS[action],
            data=file_path.read_bytes(),
            file_name=file_path.name,
            mime=mime,
            key=f"download_{file_path.suffix}_{file_path.name}",
        )
        st.caption(f"Archivo: {file_path.name}")
    if not downloaded and delivery.complete:
        st.caption("La entrega se registró, pero no hay archivos locales disponibles.")

    for action, message in delivery.errors or ():
        st.error(f"{_ACTION_LABELS.get(str(action), str(action))}: {humanize(message)}")

    if st.button(
        "Reintentar entrega",
        use_container_width=False,
        key="ff_retry_delivery",
    ):
        try:
            services.retry_delivery(run_id)
            st.session_state["ff_state"] = services.load_study(run_id)
            st.rerun()
        except Exception as exc:
            st.error(f"La entrega no se ha completado: {humanize(redact_secrets(exc))}")


def render() -> None:
    page_header(
        copy.TEXTS["approval.title"],
        copy.TEXTS["approval.subtitle"],
        eyebrow="CONTROL HUMANO Y ENTREGA",
    )

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
            f"{humanize(redact_secrets(exc))}. Inicia un nuevo estudio antes de aprobar."
        )
        bundle = None

    if not bundle or not state or not run_id:
        empty_state(
            copy.TEXTS["approval.empty_title"],
            copy.TEXTS["approval.empty_body"],
            action_label=copy.TEXTS["action.back_to_new_study"],
            page="Nuevo estudio",
        )
        return

    draft, _, _, review = bundle
    errors = [i for i in review.issues if i.severity == "error"]
    warnings = [i for i in review.issues if i.severity == "warning"]
    preview = render_report_preview(draft)
    approval = state.get("approval_record")
    awaiting = state.get("status") == "awaiting_approval"

    render_metrics(
        [
            ("Documento", "Informe", "Contenido sometido a revisión"),
            ("Versión", str(draft.version), "Versión vigente"),
            ("Errores bloqueantes", str(len(errors)), "Impiden la aprobación"),
        ],
        columns=3,
    )
    st.write("")

    section_header(copy.TEXTS["approval.preview_title"])
    with st.expander("Abrir informe completo", expanded=True):
        st.markdown(_public_markdown(preview.markdown))

    section_header(copy.TEXTS["approval.checklist_title"])
    checks = [
        ("Informe completo", bool(preview.markdown.strip())),
        ("Sin errores bloqueantes", not errors),
        (f"Avisos revisados ({len(warnings)})", True),
    ]
    for label, ok in checks:
        st.markdown(f"- {'✓' if ok else '⛔'} {label}")
    st.caption(
        "La revisión automática comprueba estructura, fuentes y coherencia. "
        "La decisión final sigue siendo tuya."
    )

    if warnings:
        with st.expander(f"Avisos informativos ({len(warnings)})"):
            for issue in warnings:
                st.warning(humanize(issue.message))

    if errors:
        st.error("La aprobación está bloqueada hasta corregir todos los errores de revisión.")
        for issue in errors:
            st.markdown(f"- {humanize(issue.message)}")
        with st.expander(copy.TEXTS["recommendation.technical"]):
            for issue in errors:
                st.code(
                    f"{issue.code} · {issue.reference_id} · {issue.correction_stage}",
                    language="text",
                )

    if awaiting:
        st.divider()
        section_header(copy.TEXTS["approval.decision_title"])
        st.caption(copy.TEXTS["approval.decision_help"])
        with st.form(f"ff_human_approval_{run_id}_{preview.draft_fingerprint}"):
            decision = st.radio(
                "Decisión",
                [
                    copy.TEXTS["approval.decision_approve"],
                    copy.TEXTS["approval.decision_changes"],
                ],
                horizontal=True,
                key="ff_decision",
            )
            confirm_read = st.checkbox(
                copy.TEXTS["approval.confirm_read"],
                key="ff_confirm_read",
            )
            st.markdown(f"**{copy.TEXTS['approval.actions_title']}**")
            approved = decision == copy.TEXTS["approval.decision_approve"]
            blocked = bool(errors) or not approved
            chosen_actions: list[tuple[str, bool]] = []
            for action in preview.delivery_actions:
                label = _ACTION_LABELS.get(str(action))
                if not label:
                    continue
                default = action == "export_markdown"
                value = st.checkbox(label, value=default, disabled=blocked, key=f"ff_action_{action}")
                chosen_actions.append((str(action), value))
            submit = st.form_submit_button(
                copy.TEXTS["action.register_decision"],
                type="primary",
                use_container_width=True,
            )

        if submit:
            if not confirm_read:
                st.error(
                    "Confirma que has leído el informe y sus limitaciones "
                    "antes de registrar la decisión."
                )
            else:
                chosen = [action for action, selected in chosen_actions if selected and approved]
                try:
                    new_state, _delivery = services.decide_approval(
                        run_id=run_id,
                        report_version_id=state.get("report_version_id") or "",
                        decision="approved" if approved else "rejected",
                        actions=chosen,
                        draft_fingerprint=preview.draft_fingerprint,
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
                            "Cambios solicitados. Esta versión no se exportará.",
                        )
                    st.rerun()
                except Exception as exc:
                    st.error(
                        "No se pudo registrar la decisión: "
                        f"{humanize(redact_secrets(exc))}"
                    )

    elif approval:
        st.write("")
        if approval.get("approved"):
            st.markdown(badge("Aprobación registrada", "ok"), unsafe_allow_html=True)
            st.caption(
                f"Decidida el {format_datetime(approval.get('decided_at'))} · "
                f"Versión {state.get('approved_version_id') or '—'}"
            )
            if state.get("status") == "completed":
                st.success("El informe ha sido aprobado y entregado completamente.")
        else:
            st.markdown(badge("Informe rechazado", "warn"), unsafe_allow_html=True)
            st.caption("No se autoriza ninguna exportación de este informe.")

    if approval and approval.get("approved"):
        st.divider()
        section_header(copy.TEXTS["approval.delivery_title"])
        actions = approval.get("actions") or []
        st.caption(
            "Acciones autorizadas: "
            + ", ".join(_ACTION_LABELS.get(str(a), str(a)) for a in actions)
        )
        _render_delivery(state, run_id)
    elif approval and not approval.get("approved"):
        st.info("Informe rechazado: no hay entregas disponibles para esta versión.")

    with st.expander("Detalles técnicos"):
        st.json(
            {
                "version_sometida": state.get("report_version_id"),
                "estado": status_label(state.get("status")),
                "decision": approval.get("decision") if approval else None,
                "acciones": approval.get("actions") if approval else None,
            }
        )
