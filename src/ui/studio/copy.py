"""Textos y etiquetas visibles de FitFamily Studio.

Un único diccionario para toda la interfaz. Las pantallas no escriben
literales de producto: piden la etiqueta aquí y, si necesitan variables,
la formatean con ``t()``.

Convenciones:
- Español natural; nada de nombres internos del workflow.
- Moneda en euros y números con separador de miles español.
- Fechas siempre con :func:`formatting.format_datetime`.
"""
from __future__ import annotations

TEXTS: dict[str, str] = {
    # Identidad
    "app.title": "FitFamily Studio · Inteligencia de mercado",
    "app.tagline": "Inteligencia de mercado",
    "app.nav_heading": "Pasos del estudio",
    "app.sidebar_promise": "Evidencia antes que prosa. Nada se ejecuta hasta que tú lo pidas.",
    "app.footer_note": "Evidencia antes que prosa.",
    # Navegación
    "nav.inicio": "Inicio",
    "nav.nuevo_estudio": "Nuevo estudio",
    "nav.indicadores": "Indicadores",
    "nav.resultados": "Resultados",
    "nav.recomendacion": "Recomendación",
    "nav.aprobacion": "Aprobación",
    "nav.locked_help": "Primero ejecuta un estudio.",
    "nav.locked_help_report": "Primero genera un informe y su revisión.",
    # Estado
    "status.no_study": "Sin estudio activo",
    "status.study": "Estudio: {study}",
    "status.phase": "{phase}",
    "status.updated": "Actualizado el {date}",
    # Acciones
    "action.new_study": "Crear nuevo estudio",
    "action.view_indicators": "Ver indicadores",
    "action.view_results": "Ver resultados",
    "action.resume": "Reanudar",
    "action.start_study": "Iniciar estudio",
    "action.retry": "Reintentar",
    "action.update_indicators": "Actualizar indicadores oficiales",
    "action.calculate_recommendation": "Calcular recomendación",
    "action.register_decision": "Registrar decisión",
    "action.back_to_new_study": "Ir a Nuevo estudio",
    # Inicio
    "home.title": "Decisiones de negocio, con los pies en los datos.",
    "home.subtitle": (
        "Investiga tu mercado, identifica oportunidades y convierte información "
        "verificable en decisiones fundamentadas."
    ),
    "home.empty_title": "Aún no hay un estudio activo",
    "home.empty_body": (
        "Empieza con «Crear nuevo estudio» para investigar competidores, "
        "indicadores oficiales y escenarios económicos con trazabilidad completa."
    ),
    "home.current_title": "Estudio en curso",
    "home.previous_title": "Trabajos anteriores",
    "home.previous_subtitle": "Ejecuciones guardadas en esta instalación. Puedes retomarlas donde quedaron.",
    "home.previous_empty": "Aún no hay trabajos guardados. Cuando inicies un estudio aparecerá aquí.",
    "home.previous_fallback": "Estudio del {date}",
    "home.purpose_title": "Un solo espacio para investigar, interpretar y decidir",
    "home.purpose_subtitle": (
        "FitFamily reúne fuentes web, indicadores municipales, escenarios "
        "económicos opcionales y revisión del informe en un flujo guiado."
    ),
    "home.transparency_title": "Transparencia",
    "home.transparency_body": "Cada dato ausente queda declarado; nunca se rellena con una cifra inventada.",
    "home.control_title": "Control humano",
    "home.control_body": "La publicación siempre espera tu decisión y solo exporta lo que autorizas.",
    "home.how_title": "Cómo funciona",
    "home.how_subtitle": "Cinco etapas, cada una con su control de calidad.",
    # Nuevo estudio
    "new.title": "Nuevo estudio de mercado",
    "new.subtitle": (
        "Caso preconfigurado: gimnasio con ludoteca · El Cañaveral · Madrid. "
        "Revisa las preguntas y abre las opciones avanzadas solo si las necesitas."
    ),
    "new.note": (
        "Los campos económicos son <strong>opcionales</strong>. Si los añades, "
        "se tratarán como <strong>supuestos del escenario</strong>, nunca como "
        "datos observados del mercado."
    ),
    "new.section_scope": "Ámbito del estudio",
    "new.section_questions": "Preguntas del estudio",
    "new.section_questions_help": "Define qué debe responder la investigación. Una pregunta por línea.",
    "new.section_advanced": "Opciones avanzadas",
    "new.section_advanced_help": "Supuestos económicos para la recomendación. Son opcionales.",
    "new.max_results": "Máximo de resultados",
    "new.max_results_help": "Más resultados implican más tiempo y coste. Ocho suele ser un buen equilibrio.",
    "new.providers": "Servicios del estudio",
    "new.llm_ok": "Redacción ✓",
    "new.llm_missing": "Redacción ✗",
    "new.search_ok": "Búsqueda ✓",
    "new.search_missing": "Búsqueda ✗",
    "new.llm_help": "Añade la clave de redacción en el archivo .env y vuelve a abrir la aplicación.",
    "new.llm_error": "No se puede iniciar el estudio porque la redacción no está disponible.",
    "new.existing": (
        "Ya hay un estudio en esta sesión. Puedes consultarlo en Resultados; "
        "iniciar otro sustituirá el estudio activo."
    ),
    # Indicadores
    "indicators.title": "Indicadores municipales",
    "indicators.subtitle": (
        "Población, hogares y actividad económica de la zona, con su fuente, "
        "periodo y estado de verificación."
    ),
    "indicators.note": (
        "Los hogares no equivalen a familias. Un dato que no se puede verificar "
        "aparece como «No disponible», nunca como cero."
    ),
    "indicators.empty_title": "Sin consulta activa",
    "indicators.empty_body": (
        "Actualiza los indicadores oficiales para ver población, hogares y "
        "actividad económica de la zona."
    ),
    "indicators.empty_error_title": "No se pudieron actualizar",
    "indicators.empty_error_body": "Inténtalo de nuevo en unos segundos.",
    "indicators.table_title": "Indicadores de la zona",
    "indicators.search": "Buscar indicador",
    "indicators.filter": "Filtrar por estado",
    "indicators.no_match": "Ningún indicador coincide con la búsqueda.",
    "indicators.source_title": "Sobre estos datos",
    "indicators.limitations_title": "Limitaciones por indicador",
    "indicators.technical": "Detalles técnicos",
    # Resultados
    "results.title": "Resultados del estudio",
    "results.subtitle": "Información de la ejecución guardada. Abrir esta pantalla no vuelve a investigar.",
    "results.empty_title": "Todavía no hay resultados",
    "results.empty_body": "Esta pantalla muestra el resultado de un estudio real. Inicia uno para generar datos.",
    "results.metrics_evidence": "Evidencias recuperadas",
    "results.metrics_competitors": "Competidores",
    "results.metrics_indicators": "Indicadores calculados",
    "results.metrics_issues": "Incidencias",
    "results.scenario_title": "Escenario calculado",
    "results.scenario_subtitle": "Resultado de tus supuestos económicos; no son observaciones de mercado.",
    "results.tab_competitors": "Competidores",
    "results.tab_tariffs": "Tarifas",
    "results.tab_sources": "Fuentes",
    "results.tab_report": "Informe y revisión",
    "results.events_title": "Evolución del proceso",
    "results.technical": "Detalles técnicos",
    # Recomendación
    "recommendation.title": "Recomendación de oportunidad",
    "recommendation.subtitle": (
        "Valoración trazable: usa indicadores oficiales, el registro de "
        "competidores y tus supuestos económicos. No garantiza rentabilidad."
    ),
    "recommendation.note": (
        "Los campos económicos son <strong>supuestos tuyos</strong>, no "
        "observaciones de mercado. Si falta información, la valoración lo "
        "declara en lugar de inventarla."
    ),
    "recommendation.assumptions_title": "Escenario (supuestos tuyos)",
    "recommendation.assumptions_help": "Estos valores no son datos verificados: definen el escenario que quieres evaluar.",
    "recommendation.score_legend": (
        "La puntuación (0-10) es un promedio ponderado de cuatro dimensiones: "
        "demanda (25 %), competencia (15 %), escenario económico (35 %) y "
        "diferenciación (25 %). No es probabilidad de éxito."
    ),
    "recommendation.break_even_risk": (
        "Con estos supuestos no alcanzas el equilibrio: necesitas unos "
        "{break_even} clientes y has previsto {expected}."
    ),
    "recommendation.break_even_ok": (
        "Con estos supuestos cubres el punto de equilibrio: necesitas unos "
        "{break_even} clientes y has previsto {expected}."
    ),
    "recommendation.break_even_note": (
        "El punto de equilibrio procede de tus supuestos, no de datos observados."
    ),
    "recommendation.missing_title": "Datos pendientes",
    "recommendation.limitations_title": "Limitaciones",
    "recommendation.factors_ok": "Factores favorables",
    "recommendation.factors_risk": "Factores desfavorables y riesgos",
    "recommendation.verified_title": "Datos verificados",
    "recommendation.assumptions_box": "Supuestos utilizados",
    "recommendation.technical": "Detalles técnicos",
    # Aprobación
    "approval.title": "Aprobación y entrega",
    "approval.subtitle": "Revisa el informe, registra tu decisión y exporta únicamente los formatos autorizados.",
    "approval.empty_title": "Sin informe pendiente de aprobación",
    "approval.empty_body": (
        "Esta pantalla se habilita cuando el estudio ha producido un informe "
        "y una revisión. Inicia primero un estudio."
    ),
    "approval.preview_title": "Vista previa del informe",
    "approval.checklist_title": "Lista de revisión",
    "approval.decision_title": "Tu decisión",
    "approval.decision_approve": "Aprobar y exportar",
    "approval.decision_changes": "Solicitar cambios",
    "approval.decision_help": "Solicitar cambios rechaza esta versión y no exporta ningún archivo.",
    "approval.confirm_read": "He leído el informe, las fuentes y las limitaciones mostradas.",
    "approval.actions_title": "Acciones que autorizo",
    "approval.delivery_title": "Publicación controlada",
    # Errores genéricos
    "error.generic": "No se pudo completar la operación. Inténtalo de nuevo.",
}


def t(key: str, **values: object) -> str:
    """Devuelve un texto del catálogo, formateado si recibe variables."""
    text = TEXTS.get(key, key)
    return text.format(**values) if values else text
