"""Pantalla: Nuevo estudio.

Formulario en tres bloques (ámbito, preguntas y opciones avanzadas) con
validación humana. Los campos financieros son opcionales y se tratan
como supuestos del escenario, nunca como datos observados. La ejecución
pasa por el controlador público `start_run`; la interfaz solo traduce el
progreso y los errores a lenguaje comprensible.
"""
from __future__ import annotations

import streamlit as st

from src.schemas import ResearchBrief
from src.ui.studio import copy, navigation, services
from src.ui.studio.components import badge, note, page_header, section_header
from src.ui.studio.formatting import humanize, status_label
from src.ui.studio.state import redact_secrets


def _validate_finance(values: dict[str, str]) -> dict | str | None:
    """Valida los supuestos económicos opcionales.

    Devuelve el dict de supuestos, None si están vacíos o un mensaje de
    error legible si son inválidos.
    """
    raw_clients = str(values.get("expected_clients", "")).strip()
    raw_fee = str(values.get("monthly_fee", "")).strip()
    if not raw_clients and not raw_fee:
        return None
    try:
        if not raw_clients or any(c in raw_clients for c in ".,"):
            return "Clientes debe ser entero sin decimales."
        clients = int(raw_clients)
        fee = float(raw_fee.replace(",", ".")) if raw_fee else 0.0
        fixed = float(str(values.get("fixed_costs", "0") or "0").replace(",", ".") or 0)
        variable = float(str(values.get("variable_cost_per_client", "0") or "0").replace(",", ".") or 0)
        if clients < 0 or min(fee, fixed, variable) < 0:
            return "Los supuestos económicos no pueden ser negativos."
        return {
            "expected_clients": clients,
            "monthly_fee": fee,
            "fixed_costs": fixed,
            "variable_cost_per_client": variable,
        }
    except (TypeError, ValueError) as exc:
        return f"Revisa los supuestos: {exc}"


def _friendly_progress(message: object) -> str:
    """Traduce el mensaje técnico del workflow a una etapa comprensible."""
    text = str(message or "").lower()
    if any(word in text for word in ("research", "investig", "búsqueda", "busqueda", "fuente")):
        return "Investigando fuentes y competidores…"
    if any(word in text for word in ("analys", "análisis", "analisis", "cálculo", "calculo")):
        return "Analizando datos y escenarios…"
    if any(word in text for word in ("writ", "redact", "informe")):
        return "Redactando el informe…"
    if any(word in text for word in ("review", "revis")):
        return "Revisando el contenido…"
    if any(word in text for word in ("approval", "aprob")):
        return "Preparando la revisión humana…"
    return "Trabajando en el estudio…"


def _execute(brief: ResearchBrief) -> None:
    """Ejecuta el estudio y presenta el progreso real por etapas."""
    if st.session_state.get("ff_running"):
        st.warning("Ya hay un estudio en ejecución; espera a que termine.")
        return

    st.session_state["ff_running"] = True
    try:
        with st.status("Preparando el estudio…", expanded=True) as progress:
            seen: set[str] = set()

            def on_progress(message: str) -> None:
                label = _friendly_progress(message)
                if label not in seen:
                    seen.add(label)
                    progress.write(label)
                progress.update(label=label, state="running")

            run_id, final_state = services.start_study(brief, on_progress=on_progress)
            final_status = final_state.get("status", "unknown")
            ready = final_status == "awaiting_approval"
            progress.update(
                label=(
                    "Estudio listo para revisión humana"
                    if ready
                    else f"Estudio finalizado · {status_label(final_status)}"
                ),
                state="complete" if ready else "error",
                expanded=False,
            )
    except Exception as exc:
        st.session_state["ff_retry_brief"] = brief.model_dump(mode="json")
        st.error(
            "No se pudo completar el estudio. "
            f"{humanize(redact_secrets(exc))}"
        )
        return
    finally:
        st.session_state["ff_running"] = False

    st.session_state["ff_run_id"] = run_id
    st.session_state["ff_state"] = final_state
    navigation.go("Resultados")
    st.rerun()


def render() -> None:
    page_header(
        copy.TEXTS["new.title"],
        copy.TEXTS["new.subtitle"],
        eyebrow="CONFIGURACIÓN DEL ESTUDIO",
    )
    note(copy.TEXTS["new.note"])
    st.write("")

    finance_values: dict[str, str] = {
        "expected_clients": "",
        "monthly_fee": "",
        "fixed_costs": "",
        "variable_cost_per_client": "",
    }

    with st.form("ff_brief_form", clear_on_submit=False):
        section_header(copy.TEXTS["new.section_scope"])
        col_a, col_b = st.columns(2)
        with col_a:
            business_type = st.text_input(
                "Tipo de negocio *",
                value="gimnasio con ludoteca",
                help="Describe el tipo de negocio que quieres estudiar.",
                key="ff_business_type",
            )
            location = st.text_input(
                "Ciudad / municipio *",
                value="Madrid",
                help="Municipio donde se localiza el estudio.",
                key="ff_location",
            )
        with col_b:
            study_area = st.text_input(
                "Zona de estudio *",
                value="El Cañaveral",
                help="Barrio o zona concreta dentro del municipio.",
                key="ff_study_area",
            )
            max_results = st.slider(
                copy.TEXTS["new.max_results"],
                min_value=1,
                max_value=20,
                value=8,
                help=copy.TEXTS["new.max_results_help"],
                key="ff_max_results",
            )
            st.caption(copy.TEXTS["new.max_results_help"])

        st.divider()
        section_header(
            copy.TEXTS["new.section_questions"],
            copy.TEXTS["new.section_questions_help"],
        )
        questions_text = st.text_area(
            "Preguntas que debe resolver el estudio",
            value=(
                "¿Qué competidores ofrecen servicios deportivos similares?\n"
                "¿Qué tarifas y servicios publican?\n"
                "¿Qué información oficial existe sobre población y hogares?\n"
                "¿Qué aspectos siguen sin poder verificarse?"
            ),
            height=130,
            help="Escribe una pregunta por línea. Cuanto más concretas, mejor será la investigación.",
            key="ff_questions",
        )

        st.divider()
        with st.expander(
            f"{copy.TEXTS['new.section_advanced']} · {copy.TEXTS['new.section_advanced_help']}",
            expanded=False,
        ):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                finance_values["expected_clients"] = st.text_input(
                    "Clientes previstos",
                    placeholder="Entero, ej. 150",
                    help="Supuesto tuyo. No es un dato observado.",
                    key="ff_expected_clients",
                )
            with f2:
                finance_values["monthly_fee"] = st.text_input(
                    "Cuota mensual (€)",
                    placeholder="Ej. 45",
                    help="Supuesto tuyo. No es una tarifa verificada.",
                    key="ff_monthly_fee",
                )
            with f3:
                finance_values["fixed_costs"] = st.text_input(
                    "Costes fijos / mes (€)",
                    placeholder="Ej. 8000",
                    help="Supuesto tuyo.",
                    key="ff_fixed_costs",
                )
            with f4:
                finance_values["variable_cost_per_client"] = st.text_input(
                    "Coste variable / cliente (€)",
                    placeholder="Ej. 8",
                    help="Supuesto tuyo.",
                    key="ff_variable_cost",
                )
            st.caption(
                "Estos valores se guardan como supuestos del encargo. No se "
                "incorporan a los indicadores oficiales ni a la investigación "
                "de competidores."
            )

        st.divider()
        status = services.provider_status()
        llm_ok = status["llm_ready"] == "yes"
        search_ok = status.get("search_ready") == "yes"
        st.markdown(f"**{copy.TEXTS['new.providers']}**")
        badges = st.columns(2)
        badges[0].markdown(
            badge(
                copy.TEXTS["new.llm_ok"] if llm_ok else copy.TEXTS["new.llm_missing"],
                "ok" if llm_ok else "danger",
            ),
            unsafe_allow_html=True,
        )
        badges[1].markdown(
            badge(
                copy.TEXTS["new.search_ok"] if search_ok else copy.TEXTS["new.search_missing"],
                "ok" if search_ok else "warn",
            ),
            unsafe_allow_html=True,
        )
        if not llm_ok:
            st.warning(copy.TEXTS["new.llm_help"])
        submitted = st.form_submit_button(
            copy.TEXTS["action.start_study"],
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not business_type.strip() or not location.strip() or not study_area.strip():
            st.error("Completa el tipo de negocio, la ciudad y la zona de estudio (campos con *).")
            return

        assumed = _validate_finance(finance_values)
        if isinstance(assumed, str):
            st.error(assumed)
            return

        if services.provider_status()["llm_ready"] != "yes":
            st.error(copy.TEXTS["new.llm_error"])
            return

        try:
            brief = ResearchBrief(
                business_type=business_type.strip(),
                location=location.strip(),
                study_area=study_area.strip(),
                questions=[line.strip() for line in questions_text.splitlines() if line.strip()],
                assumed_params=assumed,
                search_limits={"max_results": max_results},
            )
        except Exception as exc:
            st.error(f"No se pudo revisar el encargo: {humanize(redact_secrets(exc))}")
            return

        _execute(brief)

    retry_brief = st.session_state.get("ff_retry_brief")
    if retry_brief and not submitted:
        st.write("")
        st.caption("El estudio anterior no terminó. Puedes intentarlo de nuevo con los mismos datos.")
        if st.button(copy.TEXTS["action.retry"], type="primary", key="ff_retry_study"):
            st.session_state.pop("ff_retry_brief", None)
            try:
                _execute(ResearchBrief(**retry_brief))
            except Exception as exc:
                st.error(f"No se pudo reintentar el estudio: {humanize(redact_secrets(exc))}")

    if st.session_state.get("ff_state"):
        st.info(copy.TEXTS["new.existing"])
