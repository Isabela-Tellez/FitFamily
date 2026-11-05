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
    render_scenario_comparison,
    render_cost_breakdown,
    render_scenario_revenue,
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

    st.caption(
        f"Se han recopilado {len(evidences)} evidencias de mercado."
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


    # --------------------------------------------------
    # ESCENARIOS ECONÓMICOS
    # --------------------------------------------------

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

    # Recuperar exclusivamente los escenarios persistidos.
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

    if ordered_scenarios:

        st.success(
            f"Se han recuperado {len(ordered_scenarios)} "
            "escenarios económicos persistidos."
        )

        # Los tres gráficos reciben los mismos resultados persistidos.
        render_scenario_comparison(ordered_scenarios)

        st.divider()

        render_scenario_revenue(ordered_scenarios)

        st.divider()

        # Los costes se muestran para el escenario intermedio.
        reference_scenario = next(
            (
                item
                for item in ordered_scenarios
                if item["scenario"].get("scenario_type")
                == "intermediate"
            ),
            None,
        )

        if reference_scenario is not None:
            render_cost_breakdown(reference_scenario)
        else:
            st.info(
                "No existe un escenario intermedio para mostrar "
                "la estructura de costes de referencia."
            )

        st.divider()

        # --------------------------------------------------
        # DETALLE INDIVIDUAL DE LOS ESCENARIOS
        # --------------------------------------------------

        st.subheader("Detalle de escenarios")

        calculation_names = {
            "monthly_revenue": "Ingresos mensuales",
            "monthly_variable_costs": "Costes variables mensuales",
            "monthly_result": "Resultado mensual",
            "break_even": "Punto de equilibrio",
        }

        for item in ordered_scenarios:

            scenario = item["scenario"]
            calculations = item.get("calculations") or []

            scenario_type = scenario.get("scenario_type")
            scenario_name = scenario_names.get(
                scenario_type,
                "Escenario económico",
            )

            with st.container(border=True):

                st.markdown(f"### {scenario_name}")

                # Parámetros originales persistidos.
                col1, col2, col3 = st.columns(3)

                expected_clients = scenario.get("expected_clients")
                monthly_fee = scenario.get("monthly_fee")
                fixed_costs = scenario.get("fixed_costs")

                def format_number(value, decimals=2):
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                    ):
                        return "No disponible"

                    return f"{value:,.{decimals}f}"

                col1.metric(
                    "Clientes previstos",
                    format_number(expected_clients, 0),
                )

                col2.metric(
                    "Cuota mensual",
                    (
                        f"{format_number(monthly_fee)} €"
                        if format_number(monthly_fee) != "No disponible"
                        else "No disponible"
                    ),
                )

                col3.metric(
                    "Costes fijos mensuales",
                    (
                        f"{format_number(fixed_costs)} €"
                        if format_number(fixed_costs) != "No disponible"
                        else "No disponible"
                    ),
                )

                variable_cost = scenario.get(
                    "variable_cost_per_client"
                )

                st.metric(
                    "Coste variable por cliente",
                    (
                        f"{format_number(variable_cost)} €"
                        if format_number(variable_cost) != "No disponible"
                        else "No disponible"
                    ),
                )

                # Mostrar los cálculos originales, sin recalcular.
                st.markdown("#### Resultados persistidos")

                valid_calculations = [
                    calculation
                    for calculation in calculations
                    if isinstance(calculation, dict)
                ]

                displayed_calculations = set()

                if valid_calculations:

                    calculation_columns = st.columns(2)
                    displayed_count = 0

                    for calculation in valid_calculations:

                        calculation_type = calculation.get(
                            "calculation_type"
                        )

                        # Evitar duplicar un mismo indicador.
                        if (
                            not calculation_type
                            or calculation_type in displayed_calculations
                        ):
                            continue

                        displayed_calculations.add(calculation_type)

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

                        if unit == "EUR/month":
                            display_value = f"{value:,.2f} €"

                        elif unit == "clients":
                            display_value = f"{value:,.0f} clientes"

                        else:
                            display_value = (
                                f"{value:,.2f} {unit}".strip()
                            )

                        calculation_columns[
                            displayed_count % 2
                        ].metric(
                            label,
                            display_value,
                        )

                        displayed_count += 1

                        for limitation in calculation.get(
                            "limitations",
                            [],
                        ):
                            st.caption(f"⚠️ {limitation}")

                    if displayed_count == 0:
                        st.info(
                            "No hay resultados numéricos disponibles "
                            "para este escenario."
                        )

                else:
                    st.info(
                        "No hay cálculos disponibles para este escenario."
                    )

                assumptions = scenario.get("assumptions") or []

                if assumptions:
                    with st.expander("Hipótesis utilizadas"):
                        for assumption in assumptions:
                            st.write(f"- {assumption}")

    else:
        st.warning(
            "Todavía no existen escenarios económicos persistidos "
            "con una estructura válida."
        )


    # --------------------------------------------------
    # INDICADORES CALCULADOS
    # --------------------------------------------------

    if metrics:

        st.divider()
        st.subheader("Indicadores calculados")

        metric_names = {
            "monthly_revenue": "Ingresos mensuales",
            "monthly_variable_costs": "Costes variables mensuales",
            "monthly_result": "Resultado mensual",
            "break_even_clients": "Punto de equilibrio",
        }

        scenario_names = {
            "conservative": "Conservador",
            "intermediate": "Intermedio",
            "optimistic": "Optimista",
        }

        grouped_metrics = {}

        for metric in metrics:

            if hasattr(metric, "model_dump"):
                metric = metric.model_dump(mode="json")

            if not isinstance(metric, dict):
                continue

            metric_id = metric.get("metric_id", "")

            if "." not in metric_id:
                continue

            scenario_id, metric_type = metric_id.split(".", 1)

            scenario_type = scenario_id.removeprefix("scenario_")

            if scenario_type not in scenario_names:
                continue

            if metric_type not in metric_names:
                continue

            # No sobrescribir un indicador ya registrado.
            grouped_metrics.setdefault(
                scenario_type,
                {},
            ).setdefault(
                metric_type,
                metric,
            )

        if grouped_metrics:

            rows = []

            for metric_type, label in metric_names.items():

                row = {"Indicador": label}

                for scenario_type, scenario_name in (
                    scenario_names.items()
                ):

                    metric = grouped_metrics.get(
                        scenario_type,
                        {},
                    ).get(metric_type)

                    if metric is None:
                        display = "No disponible"

                    else:

                        value = metric.get("value")
                        unit = metric.get("unit", "")

                        if (
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                        ):
                            display = "No disponible"

                        elif unit == "EUR/month":
                            display = format_number(
                                value,
                                2,
                                " €",
                            )

                        elif unit == "clients":
                            display = format_number(
                                value,
                                0,
                                " clientes",
                            )

                        else:
                            display = f"{value:,.2f} {unit}".strip()

                    row[scenario_name] = display

                rows.append(row)

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "No hay indicadores económicos con estructura válida."
            )

    else:
        st.info("No hay indicadores económicos calculados.")


    # --------------------------------------------------
    # LIMITACIONES
    # --------------------------------------------------

    if limitations:

        st.subheader("Limitaciones del análisis")

        for limitation in limitations:
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
