"""Detalle visual de una investigación de FitFamily."""

import streamlit as st
import pandas as pd
import re

from src.ui.runtime import get_research_by_id
from src.ui.components.status import (
    get_status_label,
    get_stage_label,
)
from src.ui.components.charts import (
    render_scenario_summary,
    render_scenario_comparison,
    render_scenario_composition,
)

st.set_page_config(
    page_title="Detalle de investigación",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Detalle de investigación")

run_id = st.session_state.get("selected_research_id")

if not run_id:
    st.info("Selecciona una investigación desde Investigaciones.")
    st.stop()

research = get_research_by_id(run_id)

if not research:
    st.error("No se ha encontrado la investigación.")
    st.stop()

# Recuperación de los resultados persistidos.
brief = research.get("brief") or {}
market = research.get("research_result") or {}
analysis = research.get("analysis_result") or {}
review = research.get("review_result") or {}
report = research.get("report_draft") or {}

# --------------------------------------------------
# INFORMACIÓN GENERAL
# --------------------------------------------------

st.caption(f"Identificador: {run_id}")

st.subheader(
    brief.get("business_type", "Investigación")
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Estado",
    get_status_label(research.get("status")),
)

col2.metric(
    "Etapa",
    get_stage_label(research.get("current_stage")),
)

col3.metric(
    "Rondas de corrección",
    research.get("correction_rounds", 0),
)

col1.write("**Localidad**")
col1.write(brief.get("location", "No disponible"))

col2.write("**Zona de estudio**")
col2.write(brief.get("study_area", "No disponible"))

st.divider()

# --------------------------------------------------
# NAVEGACIÓN
# --------------------------------------------------

tab_market, tab_economic, tab_report, tab_review, tab_delivery = (
    st.tabs([
        "📊 Mercado",
        "💰 Análisis económico",
        "📑 Informe",
        "🔎 Revisión",
        "📦 Entrega",
    ])
)

# --------------------------------------------------
# MERCADO
# --------------------------------------------------

with tab_market:

    st.subheader("Investigación de mercado")

    evidences = market.get("evidences", [])
    competitors = market.get("competitors", [])

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Evidencias recopiladas",
        len(evidences)
    )

    col2.metric(
        "Competidores identificados",
        len(competitors)
    )

    unique_sources = {
        item.get("source_url", "").rstrip("/").lower()
        for item in evidences
        if item.get("source_url")
    }

    col3.metric(
        "Fuentes únicas",
        len(unique_sources),
        help="Número de fuentes distintas, sin duplicados."
    )

    st.subheader("Comparativa de precios")

    competitor_rows = []

    for competitor in competitors:
        competitor_evidences = competitor.get("evidences", [])

        for evidence in competitor_evidences:
            website = evidence.get("source_url")

            if not website:
                continue

            name = competitor.get("name")

            if not name:
                website = evidence.get("source_url", "").lower()

                if "energiefitness.es" in website:
                    name = "Énergie Fitness"
                elif "winfitep.com" in website:
                    name = "Winfit"
                else:
                    name = "Competidor no identificado"

            price = evidence.get("value")
            unit = evidence.get("unit") or "euros"

            frequency = evidence.get("frequency")

            if price is not None:
                price_text = f"{price:g} €"

                if frequency == "monthly":
                    price_text += "/mes"
            else:
                price_text = "No disponible"

            competitor_rows.append({
                "Competidor": name,
                "Web": website,
                "Precio": price_text,
                "Servicio": "Gimnasio con ludoteca",
            })

    if competitor_rows:
        st.dataframe(
            pd.DataFrame(competitor_rows),
            column_config={
                "Web": st.column_config.LinkColumn(
                    "Web",
                    display_text="Consultar web",
                ),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No hay competidores registrados.")


st.subheader("Evidencias y fuentes")


def normalize_source_url(url):
    """Normaliza URL para identificar evidencias de una misma página."""
    from urllib.parse import urlsplit, urlunsplit

    if not url:
        return None

    parsed = urlsplit(url.strip())

    return urlunsplit((
        parsed.scheme.lower() or "https",
        parsed.netloc.lower().removeprefix("www."),
        parsed.path.rstrip("/"),
        parsed.query,
        "",
    ))


# Agrupar evidencias de la misma página.
unique_evidences = {}

for item in evidences:
    source = item.get("source_url")
    key = normalize_source_url(source)

    # Las evidencias sin URL no deben desaparecer.
    if not key:
        key = f"sin-url:{item.get('evidence_id') or id(item)}"

    current = unique_evidences.get(key)

    if current is None:
        unique_evidences[key] = item
    else:
        # Preferir la evidencia con información de precio.
        current_score = (
            int(current.get("value") is not None)
            + int(bool(current.get("snippet")))
            + int(bool(current.get("limitations")))
        )

        new_score = (
            int(item.get("value") is not None)
            + int(bool(item.get("snippet")))
            + int(bool(item.get("limitations")))
        )

        if new_score > current_score:
            unique_evidences[key] = item


# Sustituir las evidencias originales por las únicas.
evidences = list(unique_evidences.values())


if evidences:

    st.markdown(
        f"""
        <div class="ff-summary">
            <p>✓ Se han recopilado {len(evidences)} evidencias de mercado.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Recuperar precios de todas las evidencias,
    # relacionándolos mediante la URL normalizada.
    prices_by_source = {}

    for item in evidences:
        source_url = normalize_source_url(item.get("source_url"))
        price = item.get("value")
        frequency = item.get("frequency")
        snippet_text = item.get("snippet") or ""

        if price is None:
            match = re.search(
                r"(\d{1,4}(?:[.,]\d{1,2})?)\s*"
                r"(?:€|euros?)",
                snippet_text,
                re.IGNORECASE,
            )

            if match:
                price = float(
                    match.group(1).replace(",", ".")
                )

        if price is not None and source_url:
            prices_by_source[source_url] = {
                "value": price,
                "frequency": frequency,
            }

    for index, evidence in enumerate(evidences, 1):

        claim = evidence.get("claim") or "Fuente sin descripción"
        claim = claim.replace("Search result:", "").strip()

        source = evidence.get("source_url")
        normalized_source = normalize_source_url(source)
        snippet = evidence.get("snippet") or ""

        domain = (
            source.split("//")[-1].split("/")[0]
            if source else "Fuente no identificada"
        )

        # Descripciones breves basadas en las fuentes.
        if source and "energiefitness.es" in source:
            description = (
                "Página del centro Énergie Fitness de El Cañaveral, "
                "con información del gimnasio, ubicación y tarifas."
            )

        elif source and "winfitep.com" in source:
            description = (
                "Centro de entrenamiento con presencia en El Cañaveral "
                "y Plaza Castilla. Su web presenta información sobre "
                "sus planes, instalaciones y contacto."
            )

        elif source and "onemorecanaveral.wodbuster.com" in source:
            description = (
                "Centro deportivo que ofrece entrenamiento funcional, "
                "fuerza y diferentes actividades dirigidas."
            )

        elif source and "instagram.com" in source:
            if "CAÑAVERAL, ESTAMOS LLEGANDO" in snippet.upper():
                description = (
                    "Publicación de Nine Fitness que anuncia su "
                    "próxima apertura en El Cañaveral."
                )
            elif "SE ABRE EN BREVE" in snippet.upper():
                description = (
                    "Publicación sobre la apertura de un gimnasio "
                    "en El Cañaveral y su equipo de profesionales."
                )
            else:
                description = (
                    "Publicación en Instagram relacionada con "
                    "la oferta de gimnasios de la zona."
                )

        else:
            description = claim

        # Recuperar el precio de la propia evidencia
        # o de otra evidencia de la misma página.
        price_data = prices_by_source.get(normalized_source)

        if price_data:
            price = float(price_data["value"])

            price_text = f"{price:,.2f}"
            price_text = (
                price_text
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

            if price_text.endswith(",00"):
                price_text = price_text[:-3]

            price_display = f"{price_text} €"

            if price_data["frequency"] == "monthly":
                price_display += "/mes"
        else:
            price_display = "No publicado en la evidencia"

        limitations = evidence.get("limitations")

        with st.container(border=True):

            st.markdown(f"**📄 {index}. {claim}**")

            st.caption(f"🌐 {domain}")

            st.write(description)

            st.markdown(f"**Precio: {price_display}**")

            if source:
                st.markdown(
                    f"[Consultar fuente original ↗]({source})"
                )

            if snippet:
                with st.expander("Consultar texto extraído completo"):
                    st.write(snippet)

            if limitations:
                st.caption(f"Nota: {limitations}")

            else:
                st.info("No hay evidencias registradas.")


    st.subheader("Preguntas pendientes")

    for question in market.get("unresolved_questions", []):
        st.warning(question)


# --------------------------------------------------
# ANÁLISIS ECONÓMICO
# --------------------------------------------------

with tab_economic:

    st.subheader("Análisis económico")

    scenarios = analysis.get("scenarios", [])
    metrics = analysis.get("calculated_metrics", [])
    limitations = analysis.get("limitations", [])

    scenario_order = {
        "conservative": 0,
        "intermediate": 1,
        "optimistic": 2,
    }

    scenario_names = {
        "conservative": "Conservador",
        "intermediate": "Intermedio",
        "optimistic": "Optimista",
    }

    calculation_names = {
        "monthly_revenue": "Ingresos mensuales",
        "monthly_variable_costs": "Costes variables mensuales",
        "monthly_result": "Resultado mensual",
        "break_even": "Punto de equilibrio",
    }

    metric_names = {
        "monthly_revenue": "Ingresos mensuales",
        "monthly_variable_costs": "Costes variables mensuales",
        "monthly_result": "Resultado mensual",
        "break_even_clients": "Punto de equilibrio",
    }

    def format_number(value, decimals=2):
        """Formatea valores numéricos sin aceptar booleanos."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            return "No disponible"

        return f"{value:,.{decimals}f}"

    def get_persisted_value(calculations, calculation_type):
        """Recupera un resultado numérico persistido."""
        matches = [
            calculation
            for calculation in calculations
            if isinstance(calculation, dict)
            and calculation.get("calculation_type") == calculation_type
        ]

        if len(matches) != 1:
            return None

        result = matches[0].get("result")

        if not isinstance(result, dict):
            return None

        value = result.get("value")

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            return None

        return value

    def format_economic_value(value, unit):
        """Presenta un resultado según su unidad."""
        if value is None:
            return "No disponible"

        if unit == "EUR/month":
            return f"{value:,.2f} €"

        if unit == "clients":
            return f"{value:,.0f} clientes"

        return f"{value:,.2f} {unit}".strip()

    # --------------------------------------------------
    # RECUPERACIÓN Y ORDEN DE ESCENARIOS
    # --------------------------------------------------

    valid_scenarios = []

    if isinstance(scenarios, list):
        for item in scenarios:

            if not isinstance(item, dict):
                continue

            scenario = item.get("scenario")

            if not isinstance(scenario, dict):
                continue

            valid_scenarios.append(item)

    ordered_scenarios = sorted(
        valid_scenarios,
        key=lambda item: scenario_order.get(
            item["scenario"].get("scenario_type"),
            99,
        ),
    )

    if not ordered_scenarios:

        st.warning(
            "Todavía no existen escenarios económicos persistidos "
            "con una estructura válida."
        )

    else:

        st.markdown(
            f"""
            <div class="ff-summary">
                <p>✓ Se han recuperado {len(ordered_scenarios)}
                escenarios económicos persistidos.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # --------------------------------------------------
    # 1. RESUMEN ECONÓMICO DE LOS TRES ESCENARIOS
    # --------------------------------------------------

    render_scenario_summary(ordered_scenarios)

    st.divider()


    # --------------------------------------------------
    # 2. COMPARACIÓN HORIZONTAL DE ESCENARIOS
    # --------------------------------------------------

    render_scenario_comparison(ordered_scenarios)

    st.divider()


    # --------------------------------------------------
    # 3. DISTRIBUCIÓN DE INGRESOS
    # --------------------------------------------------

    render_scenario_composition(ordered_scenarios)

    st.divider()


    # --------------------------------------------------
    # 4. DETALLE DE ESCENARIOS
    # --------------------------------------------------

    st.subheader("Detalle de escenarios")

    for item in ordered_scenarios:

        scenario = item["scenario"]
        calculations = item.get("calculations") or []

        scenario_type = scenario.get("scenario_type")

        scenario_name = scenario_names.get(
            scenario_type,
            "Escenario económico",
        )

        with st.expander(
            f"Escenario {scenario_name}",
            expanded=False,
        ):

            st.markdown("#### Parámetros del escenario")

            col1, col2 = st.columns(2)

            col1.metric(
                "Clientes previstos",
                format_number(
                    scenario.get("expected_clients"),
                    0,
                ),
            )

            col2.metric(
                "Cuota mensual",
                (
                    f"{format_number(scenario.get('monthly_fee'))} €"
                    if format_number(
                        scenario.get("monthly_fee")
                    ) != "No disponible"
                    else "No disponible"
                ),
            )

            col3, col4 = st.columns(2)

            col3.metric(
                "Costes fijos mensuales",
                (
                    f"{format_number(scenario.get('fixed_costs'))} €"
                    if format_number(
                        scenario.get("fixed_costs")
                    ) != "No disponible"
                    else "No disponible"
                ),
            )

            col4.metric(
                "Coste variable por cliente",
                (
                    f"{format_number(scenario.get('variable_cost_per_client'))} €"
                    if format_number(
                        scenario.get("variable_cost_per_client")
                    ) != "No disponible"
                    else "No disponible"
                ),
            )

            st.markdown("#### Resultados económicos")

            valid_calculations = [
                calculation
                for calculation in calculations
                if isinstance(calculation, dict)
            ]

            displayed_types = set()
            result_columns = st.columns(2)
            displayed_count = 0

            for calculation in valid_calculations:

                calculation_type = calculation.get(
                    "calculation_type"
                )

                if (
                    not calculation_type
                    or calculation_type in displayed_types
                ):
                    continue

                displayed_types.add(calculation_type)

                result = calculation.get("result")

                if not isinstance(result, dict):
                    continue

                value = result.get("value")
                unit = result.get("unit", "")

                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                ):
                    continue

                label = calculation_names.get(
                    calculation_type,
                    calculation_type,
                )

                result_columns[
                    displayed_count % 2
                ].metric(
                    label,
                    format_economic_value(value, unit),
                )

                displayed_count += 1

            if displayed_count == 0:
                st.info(
                    "No hay resultados numéricos disponibles "
                    "para este escenario."
                )


            assumptions = scenario.get("assumptions") or []

            if assumptions:

                st.markdown("#### Hipótesis utilizadas")

                for assumption in assumptions:

                    if not isinstance(assumption, str):
                        continue

                    # Compatibilidad con escenarios antiguos persistidos.
                    if "assumed_params" in assumption:
                        assumption = (
                            "Los parámetros utilizados proceden de los valores "
                            "asumidos definidos para este encargo."
                        )

                    st.markdown(f"- {assumption}")


            calculation_limitations = list(dict.fromkeys(
                limitation
                for calculation in valid_calculations
                for limitation in (
                    calculation.get("limitations") or []
                )
                if isinstance(limitation, str)
            ))

            if calculation_limitations:

                st.markdown("#### Limitaciones de los cálculos")

                for limitation in calculation_limitations:
                    st.caption(f"⚠️ {limitation}")


    # --------------------------------------------------
    # 5. INDICADORES CALCULADOS
    # --------------------------------------------------

    st.subheader("Indicadores calculados")

    metric_definitions = [
        ("monthly_revenue", "Ingresos mensuales"),
        ("monthly_variable_costs", "Costes variables mensuales"),
        ("monthly_result", "Resultado mensual"),
        ("break_even", "Punto de equilibrio"),
    ]

    rows = []

    for calculation_type, label in metric_definitions:

        row = {"Indicador": label}

        for item in ordered_scenarios:

            scenario = item.get("scenario", {})
            calculations = item.get("calculations", [])

            scenario_type = scenario.get("scenario_type")
            scenario_name = scenario_names.get(
                scenario_type,
                "Escenario",
            )

            value = get_persisted_value(
                calculations,
                calculation_type,
            )

            if calculation_type == "break_even":
                display = format_economic_value(
                    value,
                    "clients",
                )
            else:
                display = format_economic_value(
                    value,
                    "EUR/month",
                )

            row[scenario_name] = display

        rows.append(row)

    if rows and ordered_scenarios:

        indicators_df = pd.DataFrame(rows)

        st.dataframe(
            indicators_df,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "No hay indicadores económicos persistidos "
            "para comparar."
        )


    # --------------------------------------------------
    # 6. LIMITACIONES GENERALES
    # --------------------------------------------------

    if limitations:

        st.divider()
        st.subheader("Limitaciones del análisis")

        unique_limitations = list(dict.fromkeys(
            limitation
            for limitation in limitations
            if isinstance(limitation, str) and limitation.strip()
        ))

        for limitation in unique_limitations:
            st.warning(limitation)


# --------------------------------------------------
# INFORME
# --------------------------------------------------

with tab_report:

    st.subheader("Informe de viabilidad")

    if report:

        st.title(report.get("title", "Informe de investigación"))

        st.caption(
            f"Zona de estudio: "
            f"{report.get('study_area', 'No disponible')}"
        )

        sections = report.get("sections", [])

        for index, section in enumerate(sections, 1):

            if isinstance(section, dict):
                heading = section.get(
                    "title",
                    f"Sección {index}",
                )
                content = section.get("content", "")

                with st.expander(heading, expanded=True):
                    st.markdown(content)

            else:
                st.markdown(f"### Sección {index}")
                st.markdown(str(section))

        st.subheader("Fuentes consultadas")

        for source in report.get("sources", []):
            st.markdown(f"- [{source}]({source})")

        st.subheader("Limitaciones del informe")

        for limitation in report.get("limitations", []):
            st.warning(limitation)

    else:
        st.info("Todavía no existe un informe.")

# --------------------------------------------------
# REVISIÓN
# --------------------------------------------------

with tab_review:

    st.subheader("Revisión del informe")

    if review:

        st.write(
            "**Estado de revisión:**",
            research.get("review_route", "No disponible"),
        )

        st.subheader("Controles realizados")

        for check in review.get("checks_performed", []):
            st.write(f"✓ {check}")

        issues = review.get("issues", [])

        st.subheader("Incidencias")

        if issues:
            for issue in issues:
                st.warning(issue)
        else:
            st.success("No se han registrado incidencias.")

        st.json(review)

    else:
        st.info("No existe una revisión registrada.")

    st.write(
        "**Decisión de aprobación:**",
        research.get("approval_decision") or "Pendiente",
    )

# --------------------------------------------------
# ENTREGA
# --------------------------------------------------

with tab_delivery:

    st.subheader("Entrega de resultados")

    col1, col2 = st.columns(2)

    col1.metric(
        "Estado",
        research.get("delivery_status", "not_started"),
    )

    col2.metric(
        "Archivos generados",
        len(research.get("export_paths") or []),
    )

    st.subheader("Archivos")

    for path in research.get("export_paths") or []:
        st.write(f"📄 {path}")

    if not research.get("export_paths"):
        st.info("Todavía no se han generado archivos.")

st.divider()

if st.button("← Volver a investigaciones"):
    st.switch_page("src/ui/pages/research.py")
