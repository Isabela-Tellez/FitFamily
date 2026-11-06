"""Detalle visual de una investigación de FitFamily."""

from urllib.parse import urlsplit, urlunsplit
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

# --------------------------------------------------
# MERCADO
# --------------------------------------------------

with tab_market:

    st.subheader("Investigación de mercado")

    evidences = market.get("evidences", [])
    competitors = market.get("competitors", [])

    # --------------------------------------------------
    # AGRUPAR Y ELIMINAR EVIDENCIAS DUPLICADAS
    # --------------------------------------------------

    unique_evidences = {}

    for item in evidences:
        source = normalize_source_url(item.get("source_url"))

        if not source:
            source = item.get("evidence_id") or str(id(item))

        current = unique_evidences.get(source)

        if current is None:
            unique_evidences[source] = item
        else:
            # Conservar la evidencia con más información.
            current_score = (
                int(current.get("value") is not None)
                + int(bool(current.get("snippet")))
            )

            new_score = (
                int(item.get("value") is not None)
                + int(bool(item.get("snippet")))
            )

            if new_score > current_score:
                unique_evidences[source] = item

    evidences = list(unique_evidences.values())


    # Deduplicación de fuentes
    unique_sources = {
        normalize_source_url(item.get("source_url"))
        for item in evidences
        if isinstance(item, dict) and item.get("source_url")
    }

    unique_sources.discard(None)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Evidencias recopiladas",
        len(evidences)
    )

    col2.metric(
        "Competidores identificados",
        len(competitors)
    )

    col3.metric(
        "Fuentes únicas",
        len(unique_sources),
        help="Número de fuentes distintas, sin duplicados."
    )

    # --------------------------------------------------
    # COMPARATIVA DE PRECIOS
    # --------------------------------------------------

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
                website_lower = website.lower()

                if "energiefitness.es" in website_lower:
                    name = "Énergie Fitness"
                elif "winfitep.com" in website_lower:
                    name = "Winfit"
                else:
                    name = "Competidor no identificado"

            price = evidence.get("value")
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

    # --------------------------------------------------
    # FUENTES CONSULTADAS
    # --------------------------------------------------

    if evidences:
        st.subheader("Fuentes consultadas")

        # Recuperar precios asociados a cada fuente.
        prices_by_source = {}

        for item in evidences:
            source_url = normalize_source_url(item.get("source_url"))
            price = item.get("value")
            frequency = item.get("frequency")
            snippet = item.get("snippet") or ""

            if price is None:
                match = re.search(
                    r"(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:€|euros?)",
                    snippet,
                    re.IGNORECASE,
                )
                if match:
                    price = float(match.group(1).replace(",", "."))

            if price is not None and source_url:
                prices_by_source[source_url] = {
                    "value": price,
                    "frequency": frequency,
                }

        for evidence in evidences:
            source = evidence.get("source_url")
            normalized_source = normalize_source_url(source)
            snippet = (evidence.get("snippet") or "").strip()

            # Obtener nombre del establecimiento.
            domain = (
                source.split("//")[-1].split("/")[0].removeprefix("www.")
                if source else "Fuente no identificada"
            )

            claim = evidence.get("claim") or ""
            claim = re.sub(
                r"^Search result:\s*",
                "",
                claim,
                flags=re.IGNORECASE,
            ).strip()

            if source and "energiefitness.es" in source:
                name = "Énergie Fitness"
            elif source and "winfitep.com" in source:
                name = "Winfit"
            elif source and "rebelgym.es" in source:
                name = "Rebel Gym"
            elif source and "onemore" in source:
                name = "One More"
            elif source and "misclub.es" in source:
                name = "Misclub"
            else:
                name = claim or domain


            # Crear una descripción breve y evitar mostrar el snippet completo.
            if source and "onemore" in source:
                description = (
                    "Centro de fitness especializado en entrenamiento en grupos "
                    "reducidos, con seguimiento personalizado por coaches "
                    "profesionales y servicio de entrenamiento personal."
                )

            elif source and "energiefitness.es" in source:
                description = (
                    "Gimnasio de El Cañaveral con instalaciones deportivas, "
                    "servicios de entrenamiento y oferta de suscripción."
                )

            elif source and "winfitep.com" in source:
                description = (
                    "Centro de entrenamiento con presencia en El Cañaveral "
                    "y Plaza Castilla, con información sobre sus planes y servicios."
                )

            elif source and "rebelgym.es" in source:
                description = (
                    "Centro de entrenamiento situado en El Cañaveral, "
                    "con información sobre sus instalaciones y actividades."
                )

            elif source and "misclub.es" in source:
                description = (
                    "Directorio de centros deportivos y gimnasios de El Cañaveral "
                    "con información sobre la oferta deportiva de la zona."
                )

            else:
                description = (
                    "Fuente consultada para obtener información sobre "
                    "la oferta de gimnasios y servicios deportivos de la zona."
                )


            # Recuperar el precio.
            price_data = prices_by_source.get(normalized_source)

            price_display = None

            if price_data:
                price = price_data["value"]

                price_text = (
                    f"{price:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

                if price_text.endswith(",00"):
                    price_text = price_text[:-3]

                price_display = f"{price_text} €"

                if price_data["frequency"] == "monthly":
                    price_display += "/mes"

            with st.container(border=True):
                st.markdown(f"**{name}**")

                st.write(description)

                if price_display:
                    st.markdown(f"**Precio:** {price_display}")

                if source:
                    st.markdown(
                        f"[Consultar fuente original ↗]({source})"
                    )

                if snippet:
                    with st.expander(
                        "Consultar texto extraído completo"
                    ):
                        st.write(snippet)

    else:
        st.info("No hay fuentes consultadas registradas.")


# --------------------------------------------------
# NORMALIZACIÓN DE FUENTES
# --------------------------------------------------

def normalize_source_url(url):
    """Normaliza URL para identificar evidencias de una misma página."""

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
                        scenario.get('fixed_costs')
                    ) != "No disponible"
                    else "No disponible"
                ),
            )


            col4.metric(
                "Coste variable por cliente",
                (
                    f"{format_number(scenario.get('variable_cost_per_client'))} €"
                    if format_number(
                        scenario.get('variable_cost_per_client')
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


    if not report:
        st.info("Todavía no existe un informe.")


    else:


        report_title = report.get("title", "Informe de mercado")


        study_area = report.get(
            "study_area",
            brief.get("study_area", "No disponible"),
        )


        business_type = brief.get(
            "business_type",
            "Investigación",
        )

        st.markdown(f"### {report_title}")


        # --------------------------------------------------
        # CONSOLIDACIÓN DE CONTENIDOS
        # --------------------------------------------------


        import unicodedata


        def normalize_heading(value):
            value = str(value).strip().lower()
            value = unicodedata.normalize("NFKD", value)
            value = "".join(
                char for char in value
                if not unicodedata.combining(char)
            )
            value = re.sub(r"^\s*\d+[\.\)\-:]\s*", "", value)
            return value.strip()


        def clean_lot_content(content):
            """
            Combina los textos de los diferentes lotes
            en un único texto plano y elimina duplicados.
            """


            content = str(content or "").strip()


            if not content:
                return ""


            pattern = re.compile(
                r"(?im)^\s*Lote\s+\d+\s*"
                r"\([^)]*\)\s*:\s*"
            )


            matches = list(pattern.finditer(content))


            if not matches:
                return content


            parts = []


            # Texto anterior al primer lote, si existe.
            prefix = content[:matches[0].start()].strip()


            if prefix:
                parts.append(prefix)


            for index, match in enumerate(matches):


                end = (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(content)
                )


                part = content[match.end():end].strip()


                if part:
                    parts.append(part)


            unique_parts = []
            seen = set()


            for part in parts:


                normalized = re.sub(
                    r"\s+",
                    " ",
                    part.lower(),
                ).strip()


                if normalized not in seen:
                    seen.add(normalized)
                    unique_parts.append(part)


            return "\n\n".join(unique_parts)


        def is_pending_content(content):


            text = content.lower()


            pending_phrases = [
                "no se ha incorporado información",
                "queda pendiente de completar",
                "este apartado todavía no tiene contenido",
                "pendiente de investigación",
                "pendiente de análisis del entorno",
                "pendiente de evaluación estratégica",
                "pendiente de planificación",
                "pendiente de completar",
            ]


            return any(
                phrase in text
                for phrase in pending_phrases
            )


        # --------------------------------------------------
        # LIMPIEZA DE CONTENIDO
        # --------------------------------------------------

        def clean_report_content(content):
            """Limpia formato Markdown redundante del contenido."""

            if not content:
                return ""

            content = str(content)

            # Eliminar encabezados Markdown.
            content = re.sub(
                r"(?m)^\s*#{1,6}\s*",
                "",
                content,
            )

            # Eliminar negritas y cursivas.
            content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
            content = re.sub(r"\*(.*?)\*", r"\1", content)
            content = re.sub(r"__(.*?)__", r"\1", content)
            content = re.sub(r"_(.*?)_", r"\1", content)

            # Eliminar separadores repetidos.
            content = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", content)

            # Normalizar saltos de línea.
            content = re.sub(r"\n{3,}", "\n\n", content)

            return content.strip()


        # --------------------------------------------------
        # RECUPERAR LOS APARTADOS
        # --------------------------------------------------

        section_aliases = {
            "objetivo y alcance": "Objetivo y alcance",
            "metodo y fuentes de datos": "Método y fuentes de datos",
            "competencia": "Competencia",
            "precios y servicios": "Precios y servicios",
            "escenarios economicos": "Escenarios económicos",
            "incertidumbres": "Incertidumbres",
            "proximos pasos": "Próximos pasos",
        }


        expected_sections = [
            "Objetivo y alcance",
            "Método y fuentes de datos",
            "Competencia",
            "Precios y servicios",
            "Escenarios económicos",
            "Incertidumbres",
            "Próximos pasos",
            "Evidencias y fuentes",
        ]

        sections = report.get("sections") or []

        section_contents = {}

        for section in sections:

            if isinstance(section, dict):
                heading = section.get("title", "")
                content = section.get("content", "")
            else:
                lines = str(section).split("\n", 1)

                heading = lines[0].strip()
                content = lines[1].strip() if len(lines) > 1 else ""

            normalized = normalize_heading(heading)
            canonical = section_aliases.get(normalized)

            if not canonical:
                continue

            content = clean_report_content(content)

            if not content:
                continue

            # Separar contenido en párrafos.
            paragraphs = [
                paragraph.strip()
                for paragraph in content.split("\n\n")
                if paragraph.strip()
            ]

            existing = section_contents.get(canonical, [])

            for paragraph in paragraphs:
                if paragraph not in existing:
                    existing.append(paragraph)

            section_contents[canonical] = existing

        # Convertir los párrafos combinados en texto plano.
        section_contents = {
            heading: "\n\n".join(paragraphs)
            for heading, paragraphs in section_contents.items()
        }


        # --------------------------------------------------
        # PREPARAR FUENTES ÚNICAS
        # --------------------------------------------------


        report_sources = report.get("sources") or []


        if not report_sources:


            report_sources = [
                item.get("source_url")
                for item in market.get("evidences", [])
                if isinstance(item, dict)
                and item.get("source_url")
            ]


        unique_report_sources = {}


        for source in report_sources:


            if not isinstance(source, str):
                continue


            source = source.strip()


            if not source.startswith(("http://", "https://")):
                continue


            normalized = normalize_source_url(source)


            if normalized:
                unique_report_sources[normalized] = source


        # --------------------------------------------------
        # RESUMEN EJECUTIVO
        # --------------------------------------------------


        st.divider()
        st.subheader("Resumen del informe")


        executive_summary = clean_lot_content(
            report.get("executive_summary")
            or report.get("summary")
            or ""
        )


        summary_sections = [
            "Objetivo y alcance",
            "Competencia",
            "Precios y servicios",
        ]


        if not executive_summary:


            summary_items = []


            for heading in summary_sections:


                content = section_contents.get(heading, "")


                if not content:
                    continue


                # Limpiar saltos y espacios innecesarios.
                content = re.sub(r"\s+", " ", content).strip()


                # Evitar que el resumen reproduzca apartados enteros.
                sentences = re.split(
                    r"(?<=[.!?])\s+",
                    content,
                )


                excerpt = " ".join(sentences[:1]).strip()


                if excerpt:
                    summary_items.append((heading, excerpt))


        scenario_count = len(ordered_scenarios) if "ordered_scenarios" in locals() else len([
            item
            for item in analysis.get("scenarios", [])
            if isinstance(item, dict)
            and isinstance(item.get("scenario"), dict)
        ])


        col1, col2 = st.columns(2)


        col1.metric(
            "Apartados",
            len([
                heading for heading in expected_sections
                if section_contents.get(heading)
                or (
                    heading == "Escenarios económicos"
                    and scenario_count > 0
                )
                or (
                    heading == "Evidencias y fuentes"
                    and bool(unique_report_sources)
                )
            ]) + 1,
        )


        col2.metric(
            "Escenarios económicos",
            scenario_count,
        )


        if executive_summary:


            with st.container(border=True):
                st.markdown("**Resumen ejecutivo**")


                # Separar el texto en párrafos legibles.
                paragraphs = [
                    paragraph.strip()
                    for paragraph in re.split(r"\n\s*\n", executive_summary)
                    if paragraph.strip()
                ]


                for paragraph in paragraphs:
                    st.markdown(paragraph)


        elif summary_items:


            with st.container(border=True):


                st.markdown("**Resumen ejecutivo**")


                for heading, excerpt in summary_items:
                    st.markdown(f"**{heading}**")
                    st.markdown(f"- {excerpt}")


        else:


            st.info(
                "Todavía no hay información suficiente "
                "para elaborar el resumen ejecutivo."
            )



        # --------------------------------------------------
        # CONTENIDO DEL INFORME
        # --------------------------------------------------


        st.divider()
        st.subheader("Apartados del informe")


        ordered_scenarios = sorted(
            [
                item
                for item in analysis.get("scenarios", [])
                if isinstance(item, dict)
                and isinstance(item.get("scenario"), dict)
            ],
            key=lambda item: {
                "conservative": 0,
                "intermediate": 1,
                "optimistic": 2,
            }.get(
                item["scenario"].get("scenario_type"),
                99,
            ),
        )


        available_sections = [
            heading
            for heading in expected_sections
            if section_contents.get(heading)
            or (
                heading == "Escenarios económicos"
                and bool(ordered_scenarios)
            )
            or (
                heading == "Incertidumbres"
                and bool(market.get("unresolved_questions", []))
            )
            or (
                heading == "Evidencias y fuentes"
                and bool(unique_report_sources)
            )
        ]


        for index, heading in enumerate(
            available_sections,
            start=1,
        ):


            content = section_contents.get(heading, "")


            with st.expander(
                f"{index}. {heading}",
                expanded=False,
            ):


                # ------------------------------------------
                # EVIDENCIAS Y FUENTES
                # ------------------------------------------


                if heading == "Evidencias y fuentes":


                    if unique_report_sources:


                        st.caption(
                            f"{len(unique_report_sources)} fuentes consultadas."
                        )


                        for source in unique_report_sources.values():


                            domain = (
                                source.split("//")[-1]
                                .split("/")[0]
                                .removeprefix("www.")
                            )


                            st.markdown(
                                f"- **{domain}** · "
                                f"[Consultar fuente original ↗]({source})"
                            )


                    else:

                        st.info(
                            "No hay fuentes bibliográficas registradas."
                        )


                # ------------------------------------------
                # INCERTIDUMBRES
                # ------------------------------------------


                elif heading == "Incertidumbres":


                    unresolved_questions = market.get(
                        "unresolved_questions",
                        [],
                    )


                    unique_questions = []
                    seen_questions = set()


                    for question in unresolved_questions:


                        if not isinstance(question, str):
                            continue


                        question = question.strip()


                        if not question:
                            continue


                        normalized = re.sub(
                            r"\s+",
                            " ",
                            question.lower(),
                        )


                        if normalized not in seen_questions:
                            seen_questions.add(normalized)
                            unique_questions.append(question)


                    if unique_questions:


                        st.markdown(
                            "Estas cuestiones siguen pendientes de respuesta "
                            "y requieren investigación adicional."
                        )


                        for question in unique_questions:
                            st.markdown(f"- {question}")


                    elif content:

                        st.markdown(content)


                    else:

                        st.success(
                            "No hay preguntas pendientes registradas."
                        )


                # ------------------------------------------
                # ESCENARIOS ECONÓMICOS
                # ------------------------------------------


                elif heading == "Escenarios económicos":


                    if ordered_scenarios:


                        # Tarjetas resumen.
                        render_scenario_summary(
                            ordered_scenarios
                        )


                        st.divider()


                        # Gráfico comparativo.
                        render_scenario_comparison(
                            ordered_scenarios
                        )


                        st.divider()


                        # Gráfico de composición económica.
                        render_scenario_composition(
                            ordered_scenarios
                        )


                    else:
                        st.info(
                            "No existen escenarios económicos "
                            "persistidos."
                        )



                # ------------------------------------------
                # RESTO DE APARTADOS
                # ------------------------------------------


                elif content:
                    st.markdown(content)


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
