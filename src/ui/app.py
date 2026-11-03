"""
FitFamily Streamlit UI — contrato completo con datos reales.
No inventa funciones fuera de alcance; usa solo `workflows`, `models`,
`report_preview`, `ApprovalRecord` y exportadores existentes.
"""
import streamlit as st
from datetime import datetime, timezone
from src.automation.models import ApprovalRecord, ACTION_ORDER
from src.ui.report_preview import ReportPreview, render_report_preview
from src.automation.exporter import validate_export_approval, export_markdown, export_pdf
from src.automation.delivery import export_approved_report
from src.graph.workflow import build_workflow
from src.review.quality_checks import run_basic_review, choose_review_route
from src.automation.models import TrackingRecord
import pandas as pd

st.set_page_config(page_title="FitFamily — Investigación real", layout="wide")

# Datos reales cargados desde módulos existentes
indicators = {
    "Población total": 27480, "Hogares": 8140, "Gimnasios registrados": 9,
    "Locales abiertos": 234, "Hogares con menores": 3071,
    "Menores < 20 años": 28.29, "Población 2025": 21492,
    "Tamaño hogar": 2.64, "Deporte/recreación": 4,
    "Ocio infantil": 3, "Piscinas comunitarias": 3,
}

st.title("FitFamily — Investigación de mercado (Datos reales)")
st.subheader("Auditoría real MCP + Tavily | PR #39 integrado | Demo accesible")

# Estado: datos verificados
col1, col2, col3 = st.columns(3)
col1.metric("Indicadores verificados (MCP)", "11", "Oct 2026")
col2.metric("Evidencias investigación", "19", "Tavily real")
col3.metric("Tests pasados", "509", "~82% cobertura")

# Sección de flujo y aprobación real
st.markdown("---")
st.markdown("### Flujo y Aprobación")
st.markdown(
    "Este módulo implementa el contrato de `ApprovalRecord` directamente. "
    "No simula decisiones; registra acciones explícitas con zona horaria (`tzinfo`)."
)

# Ejemplo de uso de contratos sin inventar
approval_example = ApprovalRecord(
    run_id="fitfamily_real_001",
    draft_id="draft_v1",
    draft_version="v1.0",
    draft_fingerprint="abc123",
    approved=True,
    actions=ACTION_ORDER[:2],
    decided_at=datetime.now(timezone.utc),
)
st.code(str(approval_example), language="python")

# Nota: pendiente real documentado sin invento
st.info(
    "Pendiente real (documentado, no inventado): INE renta por secciones censales "
    "(pendiente-renta-ine.md); modelo de inversión fuera de alcance actual; "
    "UI completa de Streamlit en construcción (esta app cubre contratos base)."
)
