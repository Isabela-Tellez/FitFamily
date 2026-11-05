"""Pantalla de aprobación y rechazo de investigaciones FitFamily."""

import streamlit as st

from src.runtime.controller import resume_run
from src.ui.runtime import get_all_researches, get_graph


st.set_page_config(
    page_title="Aprobaciones",
    page_icon="✅",
    layout="wide",
)

st.title("✅ Aprobación de investigaciones")

st.write(
    "Revisa el informe completo y decide si autorizas "
    "su entrega o lo rechazas."
)

st.divider()


# ==================================================
# INVESTIGACIONES PENDIENTES
# ==================================================

try:
    researches = [
        item
        for item in get_all_researches()
        if item.get("status") == "awaiting_approval"
        and item.get("report_draft")
        and item.get("report_version_id")
    ]

except Exception as exc:
    st.error("Error recuperando las investigaciones.")
    st.exception(exc)
    st.stop()


if not researches:
    st.success("No hay investigaciones pendientes.")
    st.stop()


options = {}

for item in researches:
    brief = item.get("brief") or {}

    label = (
        f"{brief.get('business_type', 'Investigación')} | "
        f"{brief.get('study_area', 'Sin zona')} | "
        f"{item.get('run_id')}"
    )

    options[label] = item


st.subheader("Investigaciones pendientes")

selected_label = st.selectbox(
    "Selecciona una investigación",
    list(options.keys()),
)

research = options[selected_label]

run_id = research["run_id"]
report = research.get("report_draft") or {}
review = research.get("review_result") or {}

st.divider()


# ==================================================
# INFORMACIÓN GENERAL
# ==================================================

st.subheader("Información general")

col1, col2, col3 = st.columns(3)

col1.metric("Estado", "Pendiente de aprobación")

col2.metric(
    "Versión",
    str(research.get("version", report.get("version", 1))),
)

col3.metric(
    "Incidencias",
    len(review.get("issues", [])),
)

st.write("**Identificador:**")
st.code(run_id)

st.divider()


# ==================================================
# INFORME COMPLETO
# ==================================================

st.header(
    report.get("title", "Informe de investigación")
)

st.caption(
    f"Zona de estudio: {report.get('study_area', 'No disponible')}"
)

sections = report.get("sections") or []

for index, section in enumerate(sections, start=1):

    if isinstance(section, dict):
        heading = section.get("title", f"Sección {index}")
        content = section.get("content", "")
    else:
        lines = str(section).split("\n", 1)

        heading = lines[0].strip() or f"Sección {index}"
        content = lines[1].strip() if len(lines) > 1 else ""

    st.markdown(f"### {heading}")
    st.markdown(content)

    st.divider()


# ==================================================
# FUENTES
# ==================================================

with st.expander("Fuentes consultadas"):
    for source in report.get("sources", []):
        st.markdown(f"- [{source}]({source})")


# ==================================================
# LIMITACIONES
# ==================================================

with st.expander("Limitaciones del informe"):
    for limitation in report.get("limitations", []):
        st.warning(limitation)


# ==================================================
# REVISIÓN
# ==================================================

st.header("Revisión del informe")

checks = review.get("checks_performed", [])
issues = review.get("issues", [])

st.write("**Controles realizados:**")

if checks:
    for check in checks:
        st.write(f"✓ {check}")
else:
    st.info("No hay controles registrados.")

st.write("**Incidencias:**")

if issues:
    for issue in issues:
        st.warning(issue)
else:
    st.success("No se han registrado incidencias.")


# ==================================================
# DECISIÓN
# ==================================================

st.divider()

st.header("Decisión de aprobación")

decision = st.radio(
    "Selecciona una opción:",
    options=["approved", "rejected"],
    format_func=lambda value: (
        "Aprobar informe"
        if value == "approved"
        else "Rechazar informe"
    ),
    horizontal=True,
    key=f"decision_{run_id}",
)


# ==================================================
# ACCIONES DE ENTREGA
# ==================================================

actions = []

if decision == "approved":

    st.subheader("Acciones de entrega")

    export_markdown = st.checkbox(
        "Exportar informe Markdown",
        value=True,
        key=f"markdown_{run_id}",
    )

    export_pdf = st.checkbox(
        "Exportar informe PDF",
        value=True,
        key=f"pdf_{run_id}",
    )

    update_csv = st.checkbox(
        "Actualizar seguimiento CSV",
        value=False,
        key=f"csv_{run_id}",
    )

    if export_markdown:
        actions.append("export_markdown")

    if export_pdf:
        actions.append("export_pdf")

    if update_csv:
        actions.append("update_tracking_csv")

    if not actions:
        st.warning("Selecciona al menos una acción.")

    if update_csv and not (
        export_markdown or export_pdf
    ):
        st.warning(
            "CSV requiere autorizar Markdown o PDF."
        )

else:
    st.warning(
        "El informe será rechazado. "
        "No se ejecutarán acciones de entrega."
    )


# ==================================================
# CONFIRMACIÓN
# ==================================================

confirmed = st.checkbox(
    "Confirmo que he revisado el informe y mi decisión.",
    key=f"confirmed_{run_id}",
)

valid_actions = (
    bool(actions)
    and (
        "update_tracking_csv" not in actions
        or bool(
            {"export_markdown", "export_pdf"}.intersection(actions)
        )
    )
)

can_submit = confirmed and (
    decision == "rejected" or valid_actions
)


if st.button(
    "Confirmar decisión",
    type="primary",
    use_container_width=True,
    disabled=not can_submit,
):

    try:
        graph, _ = get_graph()

        decision_data = {
            "decision": decision,
            "report_version_id": research["report_version_id"],
            "actions": actions if decision == "approved" else [],
        }

        with st.spinner("Procesando decisión..."):
            result = resume_run(
                graph=graph,
                run_id=run_id,
                decision=decision_data,
            )

        if decision == "rejected":
            st.success("Investigación rechazada correctamente.")

        else:
            st.success("Investigación aprobada.")

            # ==========================================
            # RESULTADO DE LA ENTREGA
            # ==========================================

            st.subheader("Resultado de la entrega")

            if result.complete:
                st.success("Entrega completada correctamente.")
            else:
                st.warning(
                    "La entrega no se ha completado por completo."
                )

            st.write("**Acciones solicitadas:**")

            for action in result.requested_actions:
                st.write(f"• {action}")

            st.write("**Acciones completadas:**")

            if result.completed_actions:
                for action in result.completed_actions:
                    st.success(f"✓ {action}")
            else:
                st.info("Todavía no hay acciones completadas.")

            st.write("**Acciones pendientes o fallidas:**")

            if result.failed_actions:
                for action in result.failed_actions:
                    st.error(f"✗ {action}")
            else:
                st.success("No hay acciones pendientes.")

            st.write("**Archivos generados:**")

            if result.markdown_path:
                st.write(f"Markdown: {result.markdown_path}")

            if result.pdf_path:
                st.write(f"PDF: {result.pdf_path}")

            if result.tracking_path:
                st.write(f"Seguimiento CSV: {result.tracking_path}")

            if result.errors:
                st.subheader("Errores de entrega")

                for action, error in result.errors:
                    st.error(f"{action}: {error}")

        st.rerun()

    except Exception as exc:
        st.error("No se pudo procesar la decisión.")
        st.exception(exc)
