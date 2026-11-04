"""Pantalla: Nuevo estudio.

Formulario organizado con validación comprensiva. Los campos
financieros son opcionales y se tratan como supuestos del usuario,
nunca como datos observados. La ejecución pasa por el controlador
público `start_run` (src.runtime.controller), no por nodos internos.
"""
from __future__ import annotations

import streamlit as st

from src.schemas import ResearchBrief
from src.ui.studio import navigation, services
from src.ui.studio.components import note, page_header, section_header
from src.ui.studio.state import redact_secrets


def _validate_finance(values: dict[str, str]) -> dict | str | None:
    """Valida los supuestos económicos opcionales.

    Devuelve: dict de supuestos válidos, None si están vacíos,
    o str con el mensaje de error si son inválidos.
    """
    raw_clients = str(values.get("expected_clients", "")).strip()
    raw_fee = str(values.get("monthly_fee", "")).strip()
    if not raw_clients and not raw_fee:
        return None  # opcionales: sin valores, sin supuestos
    try:
        if not raw_clients or any(c in raw_clients for c in ".,"):
            return "Clientes previstos debe ser un entero sin decimales (sin puntos ni comas)."
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


def render() -> None:
    page_header(
        "Nuevo estudio de mercado",
        "Caso preconfigurado: gimnasio con ludoteca · El Cañaveral · Madrid. "
        "Revisa las preguntas y activa la configuración avanzada solo si es necesario.",
        eyebrow="CONFIGURACIÓN Y ENTRADA DE DATOS",
    )
    note(
        "Los campos financieros son <strong>opcionales</strong>. Si los añades, FitFamily "
        "los tratará como <strong>supuestos de escenario</strong>, nunca como datos observados del mercado."
    )
    st.write("")

    # Dict inicializado ANTES del formulario (corrige el NameError del original)
    finance_values: dict[str, str] = {
        "expected_clients": "",
        "monthly_fee": "",
        "fixed_costs": "",
        "variable_cost_per_client": "",
    }

    with st.form("ff_brief_form", clear_on_submit=False):
        section_header("Ámbito del estudio")
        col_a, col_b = st.columns(2)
        with col_a:
            business_type = st.text_input(
                "Tipo de negocio *",
                value="gimnasio con ludoteca",
                help="Describe el tipo de negocio a estudiar.",
            )
            location = st.text_input(
                "Ciudad / municipio *",
                value="Madrid",
                help="Municipio donde se localiza el estudio.",
            )
        with col_b:
            study_area = st.text_input(
                "Zona de estudio *",
                value="El Cañaveral",
                help="Barrio o zona concreta dentro del municipio.",
            )
            max_results = st.slider(
                "Máximo de resultados de búsqueda",
                min_value=1, max_value=20, value=8,
                help="Límite de fuentes que recuperará la investigación.",
            )

        st.divider()
        section_header(
            "Preguntas del estudio",
            "Define qué debe responder la investigación. Una pregunta por línea.",
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
            label_visibility="collapsed",
        )

        st.divider()
        section_header("Escenario económico (opcional)")
        with st.expander("Añadir supuestos económicos para la recomendación determinista", expanded=False):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                finance_values["expected_clients"] = st.text_input(
                    "Clientes previstos", placeholder="Entero, ej. 150",
                    help="Supuesto del usuario. No es un dato observado.",
                )
            with f2:
                finance_values["monthly_fee"] = st.text_input(
                    "Cuota mensual (€)", placeholder="Ej. 45",
                    help="Supuesto del usuario. No es una tarifa verificada.",
                )
            with f3:
                finance_values["fixed_costs"] = st.text_input(
                    "Costes fijos / mes (€)", placeholder="Ej. 8000",
                    help="Supuesto del usuario.",
                )
            with f4:
                finance_values["variable_cost_per_client"] = st.text_input(
                    "Coste variable / cliente (€)", placeholder="Ej. 8",
                    help="Supuesto del usuario.",
                )
            st.caption(
                "Estos valores se guardarán como supuestos del encargo. No se "
                "incorporarán a los datos oficiales ni a la investigación de competidores."
            )

        st.divider()
        status = services.provider_status()
        if status["llm_ready"] == "yes":
            note(
                f"<strong>Redacción:</strong> {status['llm']}.<br>"
                f"<strong>Búsqueda:</strong> {status['search']}."
            )
        else:
            st.warning(
                f"{status['llm']}. Configura GROQ_API_KEY en el .env antes de "
                "ejecutar: sin ella el flujo se detendría en la etapa de redacción."
            )
        submitted = st.form_submit_button(
            "Ejecutar estudio real", type="primary", use_container_width=True
        )

    # ---- Validación y ejecución (fuera del form) ----
    if submitted:
        if st.session_state.get("ff_running"):
            st.warning("Ya hay un estudio en ejecución; espera a que termine.")
            return

        if not business_type.strip() or not location.strip() or not study_area.strip():
            st.error("Completa el tipo de negocio, la ciudad y la zona de estudio (campos con *).")
            return

        assumed = _validate_finance(finance_values)
        if isinstance(assumed, str):
            st.error(assumed)
            return

        if services.provider_status()["llm_ready"] != "yes":
            st.error(
                "No se puede ejecutar sin GROQ_API_KEY: la redacción del informe "
                "requiere el proveedor LLM configurado."
            )
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
            st.error(f"No se pudo validar el encargo: {redact_secrets(exc)}")
            return

        # Protección contra envíos duplicados.
        st.session_state["ff_running"] = True
        try:
            with st.status("Ejecutando el estudio real…", expanded=True) as progress:
                run_id, final_state = services.start_study(
                    brief,
                    on_progress=lambda message: progress.update(
                        label=message, state="running"
                    ),
                )
                final_status = final_state.get("status", "unknown")
                progress.update(
                    label=(
                        "Estudio listo para revisión humana"
                        if final_status == "awaiting_approval"
                        else f"Estudio finalizado con estado: {final_status}"
                    ),
                    state="complete" if final_status == "awaiting_approval" else "error",
                    expanded=False,
                )
        except Exception as exc:
            st.error(f"No se pudo completar el estudio: {redact_secrets(exc)}")
            return
        finally:
            st.session_state["ff_running"] = False

        st.session_state["ff_run_id"] = run_id
        st.session_state["ff_state"] = final_state
        navigation.go("Resultados")
        st.rerun()

    if st.session_state.get("ff_state"):
        st.info(
            "Ya existe un estudio en esta sesión. Puedes consultarlo en Resultados; "
            "ejecutar otro estudio sustituirá el estudio activo de esta sesión."
        )
