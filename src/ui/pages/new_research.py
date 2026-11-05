"""Página de creación de investigaciones de FitFamily."""

from uuid import uuid4

import streamlit as st

from src.schemas import ResearchBrief
from src.runtime.controller import start_run
from src.ui.runtime import get_graph


st.title("🔎 Nueva investigación")
st.write(
    "Define los parámetros del estudio de viabilidad "
    "y lanza una investigación con FitFamily."
)

st.divider()

with st.form("new_research_form"):

    st.subheader("1. Datos del negocio")

    business_type = st.text_input(
        "Tipo de negocio",
        value="Gimnasio con ludoteca",
    )

    col1, col2 = st.columns(2)

    with col1:
        location = st.text_input(
            "Localidad",
            value="Madrid",
        )

    with col2:
        study_area = st.text_input(
            "Zona de estudio",
            value="El Cañaveral",
        )

    st.divider()

    st.subheader("2. Preguntas de investigación")

    questions_text = st.text_area(
        "Preguntas (una por línea)",
        value=(
            "¿Cuál es la demanda potencial de gimnasios con ludoteca?\n"
            "¿Qué competidores existen en la zona?\n"
            "¿Qué precios ofrecen los competidores?\n"
            "¿Qué características demográficas tiene la población?\n"
            "¿Cuál es la viabilidad comercial del negocio?"
        ),
        height=180,
    )

    st.divider()

    st.subheader("3. Parámetros económicos")

    st.info(
        "Introduce las hipótesis económicas iniciales. "
        "Estos valores alimentarán directamente el análisis "
        "de escenarios conservador, intermedio y optimista."
    )

    col1, col2 = st.columns(2)

    with col1:
        expected_clients = st.number_input(
            "Clientes previstos",
            min_value=0,
            value=0,
            step=1,
            help="Número de clientes mensuales previstos.",
        )

        monthly_fee = st.number_input(
            "Cuota mensual por cliente (€)",
            min_value=0.0,
            value=0.0,
            step=5.0,
            help="Ingreso mensual por cada cliente.",
        )

    with col2:
        fixed_costs = st.number_input(
            "Costes fijos mensuales (€)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            help="Alquiler, salarios y otros costes fijos.",
        )

        variable_cost_per_client = st.number_input(
            "Coste variable por cliente (€)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Coste mensual asociado a cada cliente.",
        )

    st.divider()

    st.subheader("4. Supuestos adicionales")

    assumptions = st.text_area(
        "Observaciones (opcional)",
        placeholder="Describe otras hipótesis iniciales del estudio.",
    )

    max_results = st.slider(
        "Resultados de búsqueda",
        min_value=5,
        max_value=20,
        value=5,
        step=5,
    )

    st.caption(
        "Por defecto se realizan 5 resultados. "
        "Puedes aumentar el límite hasta un máximo de 20."
    )

    confirmed = st.checkbox(
        "He revisado los datos y deseo iniciar la investigación."
    )

    submitted = st.form_submit_button(
        "🚀 Iniciar investigación",
        type="primary",
        use_container_width=True,
    )


if submitted:

    if not all([
        business_type.strip(),
        location.strip(),
        study_area.strip(),
        questions_text.strip(),
    ]):
        st.error("Completa todos los campos obligatorios.")

    elif monthly_fee <= 0:
        st.error("La cuota mensual debe ser mayor que cero.")

    elif monthly_fee <= variable_cost_per_client:
        st.error(
            "La cuota mensual debe superar el coste variable "
            "por cliente."
        )

    elif not confirmed:
        st.warning("Confirma los datos antes de continuar.")

    else:

        questions = [
            question.strip()
            for question in questions_text.splitlines()
            if question.strip()
        ]

        assumed_params = {
            "expected_clients": int(expected_clients),
            "monthly_fee": float(monthly_fee),
            "fixed_costs": float(fixed_costs),
            "variable_cost_per_client": float(
                variable_cost_per_client
            ),
        }

        if assumptions.strip():
            assumed_params["notes"] = assumptions.strip()

        brief_data = {
            "business_type": business_type.strip(),
            "location": location.strip(),
            "study_area": study_area.strip(),
            "questions": questions,
            "assumed_params": assumed_params,
            "search_limits": {
                "max_results": int(max_results),
            },
            "assumed": True,
        }

        try:
            brief = ResearchBrief.model_validate(brief_data)

            run_id = str(uuid4())

            graph, _ = get_graph()

            with st.spinner(
                "Ejecutando la investigación. Esto puede tardar..."
            ):
                result = start_run(
                    graph=graph,
                    run_id=run_id,
                    brief=brief.model_dump(),
                )

            st.session_state["last_created_run_id"] = run_id

            st.success(
                "Investigación registrada correctamente."
            )

            st.write("**Identificador:**")
            st.code(run_id)

            if isinstance(result, dict):

                status = result.get("status", "running")

                st.write(f"**Estado:** {status}")

                st.write(
                    f"**Etapa:** "
                    f"{result.get('current_stage', 'No disponible')}"
                )

                if status == "awaiting_approval":
                    st.info(
                        "La investigación espera aprobación humana."
                    )

                elif status == "completed":
                    st.success("Investigación completada.")

                elif status == "failed":
                    st.error("La investigación ha fallado.")

            else:
                st.info(
                    "Consulta el estado desde Investigaciones."
                )

        except Exception as exc:
            st.error("No se pudo iniciar la investigación.")
            st.exception(exc)
