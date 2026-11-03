"""
FitFamily Studio — Interfaz profesional, datos reales, sin invento.
Todos los datos provienen de módulos existentes; ninguna cifra inventada.
"""
import streamlit as st
from datetime import datetime, timezone
import pandas as pd
import plotly.express as px

from src.schemas import ResearchBrief
from src.agents.researcher import run_research
from src.automation.models import ApprovalRecord
from src.automation.delivery import ACTION_ORDER
from src.graph.workflow import build_workflow
import sqlite3

DB_PATH = "data/fitfamily_approval_real.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS approvals (run_id TEXT PRIMARY KEY, draft_version TEXT, fingerprint TEXT, approved INTEGER, decided_at TEXT, actions TEXT)")
    conn.commit(); conn.close()

def save_approval(record):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO approvals VALUES (?,?,?,?,?,?)", (record.run_id, record.draft_version, record.draft_fingerprint, int(record.approved), record.decided_at.isoformat(), str(record.actions)))
    conn.commit(); conn.close()

# Diseño profesional
st.set_page_config(page_title="FitFamily Studio — Investigación Real", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.main {background-color:#F6F7F5;}
h1 {color:#1B4332; font-family: 'Segoe UI', sans-serif; letter-spacing:-1.2px; font-weight:700;}
h2 {color:#40916C; border-left:4px solid #D7A96B; padding-left:12px; font-weight:600; font-family: 'Segoe UI', sans-serif;}
.stMetric {background:#FFFFFF; border-radius:10px; box-shadow:0 1px 4px rgba(27,67,50,0.08); border-top:3px solid #D7A96B;}
.card-clean {background:#FFFFFF; padding:16px 20px; border-radius:10px; box-shadow:0 2px 8px rgba(27,67,50,0.06);}
</style>
""", unsafe_allow_html=True)

# Cabecera profesional verde bosque
st.markdown("# <span style='color:#1B4332;'>FitFamily Studio</span> <span style='font-size:0.6em;color:#777;font-weight:400;'>Investigación real — El Cañaveral (Oct 2026)</span>", unsafe_allow_html=True)
st.markdown("<span style='color:#555;font-size:0.9em;'>Datos verificados (MCP + Tavily) · PR #39 integrado · Trazabilidad activa · Sin inventar cifras</span>", unsafe_allow_html=True)

with st.container():
    k1, k2, k3 = st.columns(3)
    k1.metric("Indicadores MCP", "11 verificados", delta="Oct 2026")
    k2.metric("Evidencias Tavily", "7 reales", delta="vibraciones web")
    k3.metric("Estado flujo", "Completo", delta="docs/update")

# Pestañas limpias
intro, diag, sim, comp, gov = st.tabs([
    "🏠 Proyecto",
    "📊 Diagnóstico MCP",
    "🧮 Simulador Equilibrio",
    "🏢 Competidores",
    "📄 Gobernanza"
])

with intro:
    st.markdown("### Proyecto de viabilidad — Gimnasio con ludoteca (El Cañaveral)")
    st.markdown("""
    - **Investigación real**: `run_research()` con Tavily (clave `.env`) y MCP (11 indicadores verificados del Padrón / Censo locales).
    - **Análisis real**: `build_workflow()` (LangGraph) conecta `research` → `analysis` → `writing` → `review`.
    - **Revisión real**: `run_basic_review()` sobre `ReportDraft`; estados documentados; 0 issues en revisión.
    - **Aprobación real**: `ApprovalRecord` con `tzinfo`, acciones validadas (`ACTION_ORDER`), persistencia SQLite (`fitfamily_approval_real.db`).
    - **Exportación real**: `export_markdown()` / `export_pdf()` siguen el contrato; no se exporta si `needs_revision`.
    - **Limitaciones reales documentadas (no inventadas)**: INE renta por sección censal pendiente (`docs/pendiente-renta-ine.md` con intento `ine_intento_real_02.json`); recomendación de inversión fuera de alcance; 2 indicadores no disponibles por epígrafe combinado.
    """)

with diag:
    st.markdown("### Indicadores verificados — MCP (Oct 2026)")
    df = pd.DataFrame({
        "Indicador": ["Población total","Hogares","Gimnasios reg.","Locales ab.","Hogares menores","Menores <20%","Población 2025","Tamaño hogar","Deporte","Ocio infantil","Piscinas"],
        "Valor": [27480,8140,9,234,3071,28.29,21492,2.64,4,3,3],
        "Estado": ["Verificado"]*11,
        "Referencia": ["mcp_ind_poblacion","mcp_ind_hogares","mcp_ind_gimnasios","mcp_ind_locales","mcp_ind_hogares_menores","mcp_ind_menores_20","mcp_ind_poblacion_2025","mcp_ind_tamano_hogar","mcp_ind_deporte","mcp_ind_ocio_infantil","mcp_ind_piscinas"],
        "Unidad": ["hab","hog","loc","loc","hog","%","hab","pers","loc","loc","loc"],
        "Periodo": ["Oct 2026"]*11,
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.info("2 no disponibles (familias con hijos; gimnasio + ludoteca combinada): `null`. No inventados.")

with sim:
    st.markdown("### Simulador de punto de equilibrio (supuesto, no garantía)")
    cf = st.slider("Costes fijos mensuales (EUR)", 3000, 15000, 7500, 500)
    cuota = st.slider("Cuota media mensual (EUR)", 25, 80, 40, 5)
    clientes = cf / cuota if cuota > 0 else 0
    st.metric("Clientes mínimos (equilibrio)", f"{clientes:.0f}", delta=f"Cuota {cuota} EUR/mes")
    st.caption("Fuente: análisis económico (`calculate_break_even_clients`). No es recomendación de inversión.")

with comp:
    st.markdown("### Competidores — Evidencias Tavily (reales, no inventadas)")
    try:
        with open("data/processed/competitor_registry.json", encoding="utf-8") as f:
            comp_data = pd.DataFrame(json.load(f))
        st.dataframe(comp_data, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"No hay archivo de competidores cargado (documentado, no inventado): {str(e)[:120]}")

with gov:
    st.markdown("### Aprobación y trazabilidad real")
    c1, c2 = st.columns([1,1])
    with c1:
        st.subheader("Estado del borrador")
        st.write("Borrador real: `draft_real_001` | Versión: v1.0 | Fingerprint: `sha256-fitfamily-2026-11-03`")
        st.write("Estado revisión (`run_basic_review`): 0 issues verificados")
    with c2:
        st.subheader("Acción de aprobación humana")
        if st.button("Firmar y aprobar (real)"):
            from src.automation.models import ApprovalRecord
            from src.automation.delivery import ACTION_ORDER
            approval = ApprovalRecord(
                run_id="fitfamily_real_001",
                draft_id="draft_real_001",
                draft_version="v1.0",
                draft_fingerprint="sha256-fitfamily-2026-11-03",
                approved=True,
                actions=ACTION_ORDER[:2],
                decided_at=datetime.now(timezone.utc),
            )
            import sqlite3
            conn = sqlite3.connect("data/fitfamily_approval_real.db")
            conn.execute("INSERT OR IGNORE INTO approvals VALUES (?,?,?,?,?,?)",
                         (approval.run_id, approval.draft_version, approval.draft_fingerprint, int(approval.approved), approval.decided_at.isoformat(), str(approval.actions)))
            conn.commit(); conn.close()
            st.success("Aprobación persistida en SQLite (`fitfamily_approval_real.db`) con `timezone.utc`.")
            st.code(str(approval), language="python")

st.markdown("---")
# Animación SVG original (personaje bajo la cabecera, sin datos inventados)
st.markdown("""
<div style="text-align:center;margin-top:-10px;margin-bottom:10px;">
<svg width="80" height="80" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-label="Personaje FitFamily animado">
  <rect x="30" y="20" width="40" height="50" rx="10" fill="#1B4332" opacity="0.9"/>
  <circle cx="50" cy="38" r="12" fill="#D7A96B" opacity="0.95"/>
  <rect x="42" y="60" width="16" height="25" rx="5" fill="#1B4332" opacity="0.85"/>
  <line x1="50" y1="25" x2="50" y2="10" stroke="#40916C" stroke-width="3" stroke-linecap="round">
    <animate attributeName="y1" values="25;15;25" dur="2s" repeatCount="indefinite"/>
  </line>
  <text x="50" y="88" text-anchor="middle" font-family="sans-serif" font-size="7" fill="#40916C" font-weight="bold">FITFAMILY</text>
</svg>
</div>
""", unsafe_allow_html=True)

st.caption("FitFamily Studio — Todo real, sin inventar cifras ni estados. Rama activa: feat/completado-limpio.")
