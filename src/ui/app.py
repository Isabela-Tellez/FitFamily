"""FitFamily Studio — interfaz Streamlit para el flujo real de investigación.

Arranque: python -m streamlit run src/ui/app.py
La app no lanza búsquedas al cargarse: cada operación externa requiere una
acción explícita. No incluye cifras de demostración ni aprobaciones ficticias.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)

from src.automation.delivery import ACTION_ORDER, export_approved_report
from src.automation.exporter import calculate_draft_fingerprint
from src.graph.persistence import build_thread_config, open_checkpointer
from src.graph.state import create_initial_state
from src.graph.workflow import build_workflow
from src.mcp.client import connect_mcp, list_mcp_tools, call_area_statistics
from src.schemas import ResearchBrief
from src.ui.controller import (
    create_approval_record,
    delivery_from_state,
    draft_from_state,
    metrics_from_state,
    research_from_state,
    review_from_state,
    validate_review_context,
)
from src.ui.report_preview import render_report_preview


# ---------------------------------------------------------------------------
# Identidad visual
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FitFamily Studio · Inteligencia de mercado",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap');
    :root {
      --ff-ink:#172c2b; --ff-muted:#657674; --ff-green:#176b55;
      --ff-mint:#dff3e9; --ff-lime:#d7ef8b; --ff-coral:#ff8e70;
      --ff-paper:#f7f8f3; --ff-line:#e5ebe5; --ff-white:#ffffff;
    }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp { background:var(--ff-paper); color:var(--ff-ink); }
    [data-testid="stHeader"] { background:rgba(247,248,243,.88); }
    [data-testid="stSidebar"] { background:#eef4ed; border-right:1px solid var(--ff-line); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--ff-muted); }
    h1,h2,h3 { font-family:'Manrope',sans-serif!important; letter-spacing:-.035em; color:var(--ff-ink); }
    h1 { font-weight:800!important; }
    .block-container { max-width:1440px; padding-top:1.5rem; padding-bottom:4rem; }
    .ff-eyebrow { color:var(--ff-green); text-transform:uppercase; font-size:.72rem; letter-spacing:.16em; font-weight:800; }
    .ff-hero { background:linear-gradient(116deg,#173b35 0%,#176b55 64%,#2f8c6d 100%); border-radius:28px; padding:34px 38px; color:white; overflow:hidden; position:relative; box-shadow:0 18px 50px rgba(23,65,53,.13); }
    .ff-hero h1 { color:white!important; font-size:clamp(2rem,4vw,3.25rem)!important; line-height:1.06; margin:.4rem 0 .7rem; }
    .ff-hero p { color:#e0eee7; max-width:660px; font-size:1.02rem; line-height:1.65; margin-bottom:1.2rem; }
    .ff-hero-tag { background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.22); border-radius:999px; padding:7px 12px; color:#f5ffe7; font-size:.76rem; font-weight:700; display:inline-block; }
    .ff-card { background:var(--ff-white); border:1px solid var(--ff-line); border-radius:18px; padding:19px 21px; box-shadow:0 5px 20px rgba(25,55,45,.035); height:100%; }
    .ff-card-label { color:var(--ff-muted); font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:.07em; }
    .ff-card-value { color:var(--ff-ink); font:800 1.9rem 'Manrope',sans-serif; margin:.25rem 0; }
    .ff-card-foot { color:var(--ff-muted); font-size:.78rem; }
    .ff-section-kicker { color:var(--ff-green); font-size:.73rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.35rem; }
    .ff-panel-title { font:800 1.45rem 'Manrope',sans-serif; color:var(--ff-ink); margin:0 0 .4rem; }
    .ff-muted { color:var(--ff-muted); }
    .ff-step { display:flex; gap:11px; align-items:center; background:white; border:1px solid var(--ff-line); border-radius:14px; padding:12px 14px; min-height:68px; }
    .ff-step-icon { width:36px;height:36px;border-radius:12px;background:var(--ff-mint);display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0; }
    .ff-step strong { display:block;color:var(--ff-ink);font-size:.84rem; }
    .ff-step span { display:block;color:var(--ff-muted);font-size:.72rem;margin-top:2px; }
    .ff-note { border-left:4px solid var(--ff-lime); background:#f1f7df; border-radius:0 12px 12px 0; padding:13px 16px; color:#344a34; font-size:.88rem; }
    .ff-status { display:inline-block; padding:5px 10px; border-radius:99px; font-size:.72rem; font-weight:800; letter-spacing:.02em; }
    .ff-status-ok { background:#e0f4e9;color:#176b48; }
    .ff-status-warn { background:#fff1d8;color:#8a5b12; }
    .ff-status-bad { background:#ffe6df;color:#a33d2c; }
    div[data-testid="stMetric"] { background:white; border:1px solid var(--ff-line); padding:15px 17px; border-radius:16px; }
    div[data-testid="stMetricLabel"] { color:var(--ff-muted); }
    div[data-testid="stMetricValue"] { font-family:'Manrope',sans-serif; color:var(--ff-ink); }
    .stButton>button, .stDownloadButton>button, .stFormSubmitButton>button { border-radius:12px; font-weight:800; min-height:44px; }
    .stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] { background:var(--ff-green); border-color:var(--ff-green); }
    [data-testid="stDataFrame"] { border:1px solid var(--ff-line); border-radius:14px; overflow:hidden; }
    [data-testid="stExpander"] { background:white; border:1px solid var(--ff-line); border-radius:14px; }
    .ff-footer { color:#83918c; font-size:.75rem; padding:18px 0 5px; border-top:1px solid var(--ff-line); margin-top:30px; }
    @media (max-width: 800px) { .ff-hero { padding:25px 22px; } .block-container { padding-left:1rem;padding-right:1rem; } }
    @media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms!important; animation-iteration-count:1!important; scroll-behavior:auto!important; } }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Modelo de recomendación real (determinista, explicable)
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("## 🧮 Modelo de recomendación de oportunidad (real, determinista)")
st.info("Este modelo usa exclusivamente datos reales: indicadores MCP (`mcp_ind_*`), registro oficial de competidores (`competitor_registry.json`), escenarios económicos (`analysis/economic_calculations.py`). No inventa cifras ni garantiza rentabilidad. Si faltan datos obligatorios, lo indica claramente.")

with st.form("ff_recommendation"):
    rec_scenario = st.selectbox("Tipo de escenario (real)", ["intermediate", "basic", "optimistic"], index=0)
    clients = st.number_input("Clientes previstos (supuesto usuario)", min_value=0, value=150)
    fee = st.number_input("Cuota mensual (EUR, supuesto usuario)", min_value=0, value=40)
    fixed = st.number_input("Costes fijos / mes (EUR, supuesto usuario)", min_value=0, value=8000)
    variable = st.number_input("Coste variable / cliente (EUR, supuesto usuario)", min_value=0, value=10)
    submit_rec = st.form_submit_button("Ejecutar recomendación determinista")

if submit_rec:
    try:
        from src.recommendation.service import recommend
        rec_result = recommend(
            scenario_type=rec_scenario,
            expected_clients=clients,
            monthly_fee=fee,
            fixed_costs=fixed,
            variable_cost_per_client=variable,
            indicator_source="MCP",
            competitor_registry_path="data/processed/competitor_registry.json",
            rent_status="pending",
            run_id="fitfamily-recommendation-final-001",
        )
        score = rec_result.score_global
        status_icon = "✅" if rec_result.status == "pending_review" else "⚠️"
        st.subheader(f"Resultado: {status_icon} {rec_result.recommendation}")
        st.metric("Puntuación (escala 0-100, basada en datos reales)", f"{score:.1f}" if score is not None else "No disponible")
        st.write("**Explicación determinista:**", rec_result.explanation if hasattr(rec_result, "explanation") else "Ver `docs/recommendation/RECOMMENDATION_MODEL.md` para metodología completa.")
        st.write("**Factores favorables (datos reales):**", ", ".join(rec_result.factors_favorable) if rec_result.factors_favorable else "Ninguno verificado.")
        st.write("**Factores desfavorables / riesgos (reales):**", ", ".join(rec_result.factors_unfavorable) if rec_result.factors_unfavorable else "Ninguno documentado.")
        st.write("**Datos faltantes (reales, no inventados):**", ", ".join(rec_result.missing_evidence) if rec_result.missing_evidence else "Ninguno documentado.")
        st.write("**Limitaciones (reales):**", "; ".join(rec_result.limitations) if rec_result.limitations else "No hay limitaciones documentadas adicionales.")
        st.write("**Versión del modelo:**", rec_result.model_version)
        st.write("**Fecha de evaluación:**", rec_result.evaluated_at.isoformat())
        st.caption("Nota: este modelo no garantiza rentabilidad. Usa exclusivamente datos verificados y supuestos del usuario claramente etiquetados. Ver `docs/recommendation/RECOMMENDATION_MODEL.md`.")
    except Exception as exc:
        st.error(f"Recomendación bloqueada (documentado real): {str(exc)[:200]}. Verifica datos de entrada y archivo `data/processed/competitor_registry.json`.")

# ---------------------------------------------------------------------------
# Logo real en panel lateral izquierdo
with st.sidebar:
    st.image(r"C:\Users\JUAN\Downloads\logo_fitfamily.jpg", width=160)

# ---------------------------------------------------------------------------
# Estado de sesión y utilidades
# ---------------------------------------------------------------------------
SESSION_DEFAULTS = {
    "ff_run_id": None,
    "ff_state": None,
    "ff_approval": None,
    "ff_delivery": None,
    "ff_mcp": None,
    "ff_mcp_error": None,
}
for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def _format_value(value: object) -> str:
    if value is None:
        return "No disponible"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return str(value)


def _redact_secrets(text: object) -> str:
    value = str(text)
    for name in ("TAVILY_API_KEY", "GROQ_API_KEY", "LANGSMITH_API_KEY"):
        secret = os.getenv(name, "")
        if secret:
            value = value.replace(secret, "[credencial ocultada]")
    return value


def _run_async(coroutine):
    """Ejecuta una operación async en el hilo principal de Streamlit."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("Ya existe un bucle async activo; no se abrió una segunda sesión MCP.")


def _get_state() -> dict | None:
    state = st.session_state.get("ff_state")
    return state if isinstance(state, dict) else None


def _get_review_bundle():
    state = _get_state()
    if not state or not state.get("report_draft") or not state.get("review_result"):
        return None
    draft = draft_from_state(state["report_draft"])
    research = research_from_state(state["research_result"])
    metrics = metrics_from_state(state.get("analysis_result"))
    review = review_from_state(state["review_result"])
    validate_review_context(draft=draft, research=research, metrics=metrics, review=review)
    return draft, research, metrics, review


def _run_study(brief: ResearchBrief, writer_mode: str) -> None:
    """Ejecuta el grafo real con checkpoint SQLite y actualizaciones de etapa."""
    run_id = uuid4().hex
    initial_state = create_initial_state(run_id, brief.model_dump(mode="json"))
    initial_state["writer_mode"] = writer_mode
    db_path = ROOT / "data" / "fitfamily_ui_checkpoints.sqlite"
    final_state = None
    labels = {
        "research": "1/4 · Investigando fuentes web y competidores",
        "analysis": "2/4 · Analizando los supuestos proporcionados",
        "writing": "3/4 · Construyendo el informe trazable",
        "review": "4/4 · Revisando evidencias y cifras",
    }
    with st.status("Preparando el estudio…", expanded=True) as progress:
        try:
            with open_checkpointer(db_path) as checkpointer:
                graph = build_workflow(checkpointer=checkpointer)
                config = build_thread_config(run_id)
                for snapshot in graph.stream(initial_state, config=config, stream_mode="values"):
                    final_state = snapshot
                    stage = snapshot.get("current_stage", "research")
                    progress.update(label=labels.get(stage, "Procesando estudio…"), state="running")
            if final_state is None:
                raise RuntimeError("El workflow terminó sin devolver un estado.")
            st.session_state["ff_run_id"] = run_id
            st.session_state["ff_state"] = final_state
            st.session_state["ff_approval"] = None
            st.session_state["ff_delivery"] = None
            final_status = final_state.get("status", "unknown")
            progress.update(
                label=("Estudio listo para revisión humana" if final_status == "awaiting_approval"
                       else "Estudio completado con incidencias que requieren atención"),
                state="complete" if final_status == "awaiting_approval" else "error",
                expanded=False,
            )
        except Exception as exc:
            progress.update(label="No se pudo completar el estudio", state="error", expanded=True)
            st.error(f"{type(exc).__name__}: {_redact_secrets(exc)}")


async def _query_mcp() -> dict:
    async with connect_mcp() as session:
        tools = await list_mcp_tools(session)
        tool_names = [tool.name for tool in tools]
        if "get_area_statistics" not in tool_names:
            raise RuntimeError("El servidor MCP no publica get_area_statistics.")
        return await call_area_statistics(session, "el-cañaveral")


def _load_mcp() -> None:
    try:
        with st.spinner("Consultando el servidor MCP local…"):
            payload = _run_async(_query_mcp())
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        st.session_state["ff_mcp"] = payload
        st.session_state["ff_mcp_error"] = None
    except Exception as exc:
        st.session_state["ff_mcp"] = None
        st.session_state["ff_mcp_error"] = _redact_secrets(exc)


def _indicator_rows(payload: dict) -> pd.DataFrame:
    labels = {
        "population_total": "Población total",
        "population_total_2025": "Población total · 2025",
        "households_total": "Hogares totales",
        "average_household_size": "Tamaño medio del hogar",
        "population_under_20_share": "Población menor de 20 años",
        "households_with_minors": "Hogares con menores",
        "families_with_children": "Familias con hijos",
        "businesses_open": "Locales abiertos",
        "gyms_registered": "Gimnasios registrados",
        "gyms_with_ludoteca": "Gimnasios con ludoteca",
        "sports_recreation": "Deporte y recreación",
        "child_leisure": "Ocio infantil",
        "community_pools": "Piscinas comunitarias",
    }
    rows = []
    for key, item in (payload.get("results") or {}).items():
        item = item if isinstance(item, dict) else {"value": item}
        value = item.get("value")
        verification = item.get("verification_status")
        if value is None or verification == "unavailable":
            status = "No disponible"
        elif verification == "verified":
            status = "Verificado"
        else:
            status = "Sin verificar"
        rows.append({
            "Indicador": labels.get(key, key.replace("_", " ").capitalize()),
            "Valor": _format_value(value),
            "Unidad": item.get("unit") or "—",
            "Periodo de referencia": item.get("reference_period") or "—",
            "Estado": status,
            "Fuente": item.get("source_url") or "—",
            "Limitación / nota": item.get("limitations") or "—",
        })
    return pd.DataFrame(rows)


def _render_mascot() -> None:
    """Ilustración original en SVG/CSS: animación decorativa y accesible."""
    html = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;background:transparent;font-family:Arial,sans-serif}
    .scene{width:100%;height:285px;position:relative;overflow:hidden;background:linear-gradient(135deg,#e8f5ed,#d8efe2 60%,#f4f7df);border-radius:24px}
    .sun{position:absolute;width:72px;height:72px;right:9%;top:23px;border-radius:50%;background:#f6d66e;box-shadow:0 0 0 14px #f6d66e33}
    .cloud{position:absolute;width:95px;height:26px;left:9%;top:35px;border-radius:30px;background:#fff;opacity:.8}.cloud:before,.cloud:after{content:"";position:absolute;background:#fff;border-radius:50%}.cloud:before{width:34px;height:34px;left:14px;top:-17px}.cloud:after{width:43px;height:43px;left:40px;top:-22px}
    .floor{position:absolute;left:0;right:0;bottom:0;height:65px;background:#bddfc8;border-top:3px solid #9fceb0}
    .sign{position:absolute;left:6%;top:15px;color:#176b55;font-size:11px;font-weight:800;letter-spacing:2px}
    svg{position:absolute;inset:0;width:100%;height:100%}.float{animation:float 3.4s ease-in-out infinite}.bob{transform-box:fill-box;transform-origin:center bottom;animation:bob 1.9s ease-in-out infinite}.ball{animation:roll 3s ease-in-out infinite}.spark{animation:twinkle 1.7s ease-in-out infinite alternate}
    @keyframes float{50%{transform:translateY(-7px)}}@keyframes bob{50%{transform:rotate(3deg) translateY(-2px)}}@keyframes roll{0%,100%{transform:translateX(0) rotate(0)}50%{transform:translateX(20px) rotate(180deg)}}@keyframes twinkle{to{opacity:.25;transform:scale(.7)}}
    @media(prefers-reduced-motion:reduce){.float,.bob,.ball,.spark{animation:none!important}}
    </style></head><body><div class="scene" role="img" aria-label="Ilustración animada de una familia: una persona entrena mientras una niña juega en una zona infantil segura.">
    <div class="sign">FITFAMILY · BIENESTAR EN FAMILIA</div><div class="sun"></div><div class="cloud"></div><div class="floor"></div>
    <svg viewBox="0 0 760 285" aria-hidden="true">
      <g class="spark" fill="#e5a63b"><path d="M118 105l5 12 12 5-12 5-5 12-5-12-12-5 12-5z"/><path d="M632 89l4 9 9 4-9 4-4 9-4-9-9-4 9-4z"/></g>
      <!-- Gym mat and plant --> <rect x="72" y="216" width="340" height="12" rx="6" fill="#8fc2a0"/><path d="M682 219q-23-40-4-67q28 18 15 67" fill="#65a77c"/><path d="M690 220q-5-44 23-58q13 32-12 58" fill="#438f68"/><rect x="676" y="218" width="40" height="17" rx="5" fill="#e9a27f"/>
      <!-- Adult lifting a light bar --> <g class="float"><path d="M246 148q-12 28-10 63" stroke="#176b55" stroke-width="22" stroke-linecap="round"/><path d="M246 148q26 5 39 28" stroke="#176b55" stroke-width="19" stroke-linecap="round"/><circle cx="248" cy="112" r="23" fill="#d99568"/><path d="M226 109q3-28 29-27q23 2 22 24q-23-8-51 3" fill="#283d37"/><path d="M238 170l-31 43" stroke="#176b55" stroke-width="14" stroke-linecap="round"/><path d="M267 176l34 30" stroke="#176b55" stroke-width="14" stroke-linecap="round"/><path d="M196 207h25M293 207h25" stroke="#d99568" stroke-width="10" stroke-linecap="round"/><path d="M279 135l42-24" stroke="#d99568" stroke-width="10" stroke-linecap="round"/><path d="M316 105h39" stroke="#31544a" stroke-width="7" stroke-linecap="round"/><rect x="311" y="94" width="8" height="23" rx="3" fill="#31544a"/><rect x="352" y="94" width="8" height="23" rx="3" fill="#31544a"/></g>
      <!-- Child playing --> <g class="bob"><circle cx="486" cy="152" r="18" fill="#ad6f4d"/><path d="M468 147q3-24 23-20q17 4 14 20q-16-8-37 0" fill="#4b3831"/><path d="M486 172l-3 42" stroke="#ff8e70" stroke-width="18" stroke-linecap="round"/><path d="M482 184l-28 22" stroke="#ad6f4d" stroke-width="9" stroke-linecap="round"/><path d="M490 183l26 15" stroke="#ad6f4d" stroke-width="9" stroke-linecap="round"/><path d="M483 212l-16 20M489 212l18 20" stroke="#405d9c" stroke-width="10" stroke-linecap="round"/><path d="M458 232h15M501 232h14" stroke="#fff" stroke-width="5" stroke-linecap="round"/></g>
      <g class="ball"><circle cx="550" cy="218" r="14" fill="#f1c94f"/><path d="M539 211q11 5 12 20M549 204q-3 11 12 18" stroke="#fff" stroke-width="3" fill="none"/></g>
      <!-- Friendly playhouse --> <rect x="545" y="133" width="78" height="78" rx="8" fill="#fff4db" stroke="#d9c69c" stroke-width="3"/><path d="M536 137l48-38 49 38" fill="#ff8e70" stroke="#d47a61" stroke-width="4"/><rect x="574" y="170" width="22" height="41" rx="10" fill="#b6d9c1"/><circle cx="561" cy="157" r="8" fill="#8ec5a4"/><circle cx="609" cy="157" r="8" fill="#8ec5a4"/>
    </svg></div></body></html>"""
    components.html(html, height=300, scrolling=False)


def _render_header(title: str, subtitle: str, eyebrow: str = "FITFAMILY STUDIO") -> None:
    st.markdown(f'<div class="ff-section-kicker">{eyebrow}</div><div class="ff-panel-title">{title}</div><div class="ff-muted">{subtitle}</div>', unsafe_allow_html=True)


def _render_status_steps(state: dict | None) -> None:
    current = state.get("current_stage") if state else None
    status = state.get("status") if state else None
    steps = [
        ("🔎", "Investigar", "Fuentes y competidores", "research"),
        ("📐", "Analizar", "Cálculos con supuestos", "analysis"),
        ("📝", "Redactar", "Informe trazable", "writing"),
        ("🛡️", "Revisar", "Control de calidad", "review"),
        ("✍️", "Aprobar", "Decisión humana", "approval"),
    ]
    cols = st.columns(len(steps))
    completed_order = ["analysis", "writing", "review", "approval"]
    for col, (icon, label, detail, stage) in zip(cols, steps):
        done = bool(state) and (
            stage in completed_order and completed_order.index(stage) < completed_order.index(current)
            if current in completed_order and stage in completed_order
            else stage == "research" and current != "research"
        )
        active = bool(state) and current == stage
        color = "#176b55" if done or active else "#87958f"
        mark = "✓" if done else icon
        col.markdown(
            f'<div class="ff-step"><div class="ff-step-icon">{mark}</div><div><strong style="color:{color}">{label}</strong><span>{detail}</span></div></div>',
            unsafe_allow_html=True,
        )
    if state and status == "failed":
        st.warning("El control de revisión ha bloqueado la aprobación. Consulta las incidencias en Resultados.")


def _render_footer() -> None:
    st.markdown(
        '<div class="ff-footer">FitFamily Studio · Evidencia antes que prosa · Los datos ausentes siguen siendo no disponibles · La exportación requiere aprobación humana.</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------
if "ff_navigation" not in st.session_state:
    st.session_state["ff_navigation"] = "Visión general"

with st.sidebar:
    st.markdown("<div style='font:800 1.55rem Manrope;color:#176b55;padding:8px 0 2px'>fit<span style='color:#ff8e70'>family</span>.</div>", unsafe_allow_html=True)
    st.caption("Inteligencia de mercado · El Cañaveral")
    page = st.radio(
        "NAVEGACIÓN",
        ["Visión general", "Nuevo estudio", "Resultados", "Indicadores oficiales", "Aprobación y entrega"],
        label_visibility="collapsed",
        key="ff_navigation",
    )
    st.divider()
    current = _get_state()
    if current:
        st.markdown("<span class='ff-status ff-status-ok'>● ESTUDIO EN SESIÓN</span>", unsafe_allow_html=True)
        st.caption(f"ID · {st.session_state['ff_run_id']}")
        st.caption(f"Estado · {current.get('status', '—')}")
    else:
        st.markdown("<span class='ff-status ff-status-warn'>○ SIN ESTUDIO ACTIVO</span>", unsafe_allow_html=True)
    st.divider()
    st.caption("Las búsquedas, consultas MCP y exportaciones solo se ejecutan al pulsar sus controles.")


# ---------------------------------------------------------------------------
# Página: visión general
# ---------------------------------------------------------------------------
if page == "Visión general":
    st.markdown(
        """
        <div class="ff-hero">
          <span class="ff-hero-tag">MARKET INTELLIGENCE · REAL DATA</span>
          <h1>Decisiones de negocio,<br>con los pies en los datos.</h1>
          <p>Investiga el entorno, entiende la oferta local y convierte evidencias verificables en un informe claro. Sin rellenar huecos. Sin cifras inventadas.</p>
          <span class="ff-hero-tag">Investigación → análisis → revisión → aprobación humana</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.18, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown("<div class='ff-section-kicker'>UN ESTUDIO MÁS FÁCIL DE ENTENDER</div><div class='ff-panel-title'>Un solo espacio para investigar, interpretar y decidir.</div>", unsafe_allow_html=True)
        st.markdown("FitFamily reúne las fuentes web, los indicadores municipales, los escenarios económicos opcionales y la revisión del informe en un flujo guiado. Cada cifra conserva su fuente y cada dato ausente se muestra como tal.")
        a, b = st.columns(2)
        with a:
            st.markdown('<div class="ff-card"><div class="ff-card-label">Transparencia</div><div class="ff-card-value">Visible</div><div class="ff-card-foot">Cada dato ausente queda declarado.</div></div>', unsafe_allow_html=True)
        with b:
            st.markdown('<div class="ff-card"><div class="ff-card-label">Control humano</div><div class="ff-card-value">Explícito</div><div class="ff-card-foot">La publicación espera tu decisión.</div></div>', unsafe_allow_html=True)
        st.write("")
        if st.button("Empezar un nuevo estudio", type="primary", use_container_width=True):
            st.info("Usa la navegación lateral para cambiar a 'Nuevo estudio'.")
    with right:
        _render_mascot()
    st.write("")
    _render_header("Así funciona", "Cinco pasos comprensibles; cada uno usa los módulos reales del proyecto.")
    cols = st.columns(5)
    for col, icon, title, desc in zip(
        cols,
        ["🔎", "📊", "📝", "🛡️", "✅"],
        ["Investigar", "Analizar", "Redactar", "Revisar", "Aprobar"],
        ["Tavily / DDGS", "Supuestos visibles", "Informe trazable", "Errores y avisos", "Tú decides"],
    ):
        col.markdown(f'<div class="ff-card"><div style="font-size:1.6rem">{icon}</div><strong>{title}</strong><div class="ff-card-foot">{desc}</div></div>', unsafe_allow_html=True)
    st.write("")
    _render_status_steps(_get_state())


# ---------------------------------------------------------------------------
# Página: nuevo estudio
# ---------------------------------------------------------------------------
elif page == "Nuevo estudio":
    _render_header("Diseña tu investigación", "Define el encargo. La búsqueda real solo comienza cuando pulses «Ejecutar estudio».")
    st.markdown('<div class="ff-note">Los campos financieros son opcionales. Si los añades, FitFamily los tratará como <strong>supuestos de escenario</strong>, nunca como datos observados del mercado.</div>', unsafe_allow_html=True)
    st.write("")
    with st.form("ff_brief_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            business_type = st.text_input("Tipo de negocio", value="gimnasio con ludoteca")
            location = st.text_input("Ciudad / municipio", value="Madrid")
        with col_b:
            study_area = st.text_input("Zona de estudio", value="El Cañaveral")
            max_results = st.slider("Máximo de resultados de búsqueda", min_value=1, max_value=20, value=8)
        questions_text = st.text_area(
            "Preguntas que debe resolver el estudio",
            value=(
                "¿Qué competidores ofrecen servicios deportivos similares?\n"
                "¿Qué tarifas y servicios publican?\n"
                "¿Qué información oficial existe sobre población y hogares?\n"
                "¿Qué aspectos siguen sin poder verificarse?"
            ),
            height=125,
        )
        st.markdown("#### Escenario económico (opcional)")
        include_finance = st.checkbox("Añadir mis propios supuestos para calcular un escenario", value=False)
        finance_values = {}
        if include_finance:
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                finance_values["expected_clients"] = st.text_input("Clientes previstos", placeholder="Entero")
            with f2:
                finance_values["monthly_fee"] = st.text_input("Cuota mensual (€)", placeholder="Ej. 45")
            with f3:
                finance_values["fixed_costs"] = st.text_input("Costes fijos / mes (€)", placeholder="Ej. 8000")
            with f4:
                finance_values["variable_cost_per_client"] = st.text_input("Coste variable / cliente (€)", placeholder="Ej. 8")
            st.caption("Estos valores se almacenarán como supuestos del encargo. No se incorporarán a los datos oficiales ni a la investigación de competidores.")
        writer_mode_label = st.radio(
            "Modo de redacción",
            ["Determinista · sin llamadas LLM", "LLM Groq · requiere credenciales"],
            horizontal=True,
            help="El modo determinista es la opción recomendada para reproducibilidad. El LLM solo redacta con evidencias recibidas.",
        )
        submitted = st.form_submit_button("Ejecutar estudio real", type="primary", use_container_width=True)

    if submitted:
        if not business_type.strip() or not location.strip() or not study_area.strip():
            st.error("Completa el tipo de negocio, la ciudad y la zona de estudio.")
        else:
            assumed_params = None
            if include_finance:
                try:
                    raw_clients = str(finance_values["expected_clients"]).strip()
                    if not raw_clients or any(c in raw_clients for c in ".,"):
                        raise ValueError("Clientes previstos debe ser un entero sin decimales.")
                    clients = int(raw_clients)
                    monthly_fee = float(str(finance_values["monthly_fee"]).replace(",", "."))
                    fixed_costs = float(str(finance_values["fixed_costs"]).replace(",", "."))
                    variable_cost = float(str(finance_values["variable_cost_per_client"]).replace(",", "."))
                    assumed_params = {
                        "expected_clients": clients,
                        "monthly_fee": monthly_fee,
                        "fixed_costs": fixed_costs,
                        "variable_cost_per_client": variable_cost,
                    }
                    if clients < 0 or min(monthly_fee, fixed_costs, variable_cost) < 0:
                        raise ValueError("Los supuestos económicos no pueden ser negativos.")
                except (TypeError, ValueError) as exc:
                    st.error(f"Revisa los supuestos: {exc}")
                    assumed_params = "invalid"
            if assumed_params != "invalid":
                try:
                    brief = ResearchBrief(
                        business_type=business_type.strip(),
                        location=location.strip(),
                        study_area=study_area.strip(),
                        questions=[line.strip() for line in questions_text.splitlines() if line.strip()],
                        assumed_params=assumed_params,
                        search_limits={"max_results": max_results},
                    )
                    mode = "llm" if writer_mode_label.startswith("LLM") else "deterministic"
                    if mode == "llm" and not os.getenv("GROQ_API_KEY"):
                        st.error("Has seleccionado redacción LLM, pero GROQ_API_KEY no está configurada en el .env.")
                    else:
                        _run_study(brief, mode)
                        st.rerun()
                except Exception as exc:
                    st.error(f"No se pudo validar el encargo: {_redact_secrets(exc)}")
    if _get_state():
        st.info("Ya existe un estudio en esta sesión. Puedes consultarlo en Resultados; ejecutar otro estudio sustituirá el estudio activo de esta sesión.")


# ---------------------------------------------------------------------------
# Página: resultados
# ---------------------------------------------------------------------------
elif page == "Resultados":
    state = _get_state()
    if not state:
        st.info("Todavía no hay un estudio en esta sesión. Ve a «Nuevo estudio» para comenzar.")
    else:
        _render_header("Resultados del estudio", "Información procedente de la ejecución guardada del workflow; no se vuelve a investigar al abrir esta pantalla.")
        draft = draft_from_state(state["report_draft"]) if state.get("report_draft") else None
        research = research_from_state(state["research_result"]) if state.get("research_result") else None
        review = review_from_state(state["review_result"]) if state.get("review_result") else None
        metrics = metrics_from_state(state.get("analysis_result"))
        evidence_items = list(research.evidences) if research else []
        if research:
            evidence_ids = {item.evidence_id for item in evidence_items}
            for competitor in research.competitors:
                for evidence in competitor.evidences:
                    if evidence.evidence_id not in evidence_ids:
                        evidence_items.append(evidence)
                        evidence_ids.add(evidence.evidence_id)
        verified_note = "Proveedor Tavily" if os.getenv("TAVILY_API_KEY") else "Proveedor de búsqueda alternativo (DDGS si está disponible)"
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Evidencias recuperadas", len(evidence_items))
        k2.metric("Competidores", len(research.competitors) if research else 0)
        k3.metric("Indicadores calculados", len(metrics))
        k4.metric("Incidencias", len(review.issues) if review else 0)
        st.caption(f"{verified_note} · Ejecución {st.session_state['ff_run_id']} · Estado {state.get('status', '—')}")

        tab_summary, tab_competitors, tab_evidence, tab_report = st.tabs(["Resumen", "Competidores", "Evidencias", "Informe y revisión"])
        with tab_summary:
            st.markdown("#### Progreso del workflow")
            _render_status_steps(state)
            if research:
                st.markdown("#### Método de investigación")
                st.write(research.search_performed or "El módulo no devolvió un resumen del método.")
                if research.notes:
                    st.caption(research.notes)
                if research.unresolved_questions:
                    st.markdown("#### Preguntas pendientes")
                    for question in research.unresolved_questions:
                        st.markdown(f"- {question}")
            analysis = state.get("analysis_result") or {}
            if analysis.get("limitations"):
                st.markdown("#### Alcance del análisis económico")
                for limitation in analysis["limitations"]:
                    st.markdown(f"- {limitation}")
            if metrics:
                st.markdown("#### Escenario calculado")
                st.dataframe(pd.DataFrame([
                    {"Métrica": metric.metric_id, "Resultado": _format_value(float(metric.value)) if metric.value is not None else "No disponible", "Unidad": metric.unit, "Cálculo": metric.calculation}
                    for metric in metrics
                ]), hide_index=True, use_container_width=True)
                st.info("Las proyecciones se calculan exclusivamente a partir de los supuestos introducidos en el encargo. No son observaciones de mercado.")
        with tab_competitors:
            if research and research.competitors:
                rows = []
                for item in research.competitors:
                    rows.append({
                        "Competidor": item.name or "Nombre no disponible",
                        "Ubicación": item.location or "No disponible",
                        "Servicios declarados": ", ".join(item.services) if item.services else "No disponible",
                        "Tarifas registradas": json.dumps(item.tariffs, ensure_ascii=False) if item.tariffs else "No disponible",
                        "Ludoteca": "Sí" if item.has_playroom is True else "No" if item.has_playroom is False else "No disponible",
                        "Verificación": item.verification_status or "No disponible",
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                st.caption("«No disponible» significa que la fuente no permitió verificar ese campo; no equivale a «no». ")
            else:
                st.info("La búsqueda no devolvió competidores estructurados. Revisa el método y las preguntas pendientes.")
        with tab_evidence:
            if evidence_items:
                rows = [{
                    "ID": item.evidence_id,
                    "Afirmación / fragmento": item.claim,
                    "Extracto": item.snippet or "—",
                    "URL": item.source_url or "—",
                    "Fecha observada": item.date_observed or "—",
                    "Limitaciones": item.limitations or "—",
                } for item in evidence_items]
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, column_config={"URL": st.column_config.LinkColumn("Fuente", display_text="Abrir fuente")}, height=440)
            else:
                st.warning("No hay evidencias para mostrar. El flujo no habilita aprobación si la investigación no aporta evidencia utilizable.")
        with tab_report:
            if draft:
                preview = render_report_preview(draft)
                st.markdown(f"**{preview.draft_id}** · versión {preview.draft_version}")
                st.markdown(preview.markdown)
                with st.expander("Trazabilidad e identidad del documento"):
                    st.code(preview.draft_fingerprint, language="text")
                    st.caption("La huella se calcula sobre el ReportDraft real mostrado. Cualquier cambio invalida la aprobación previa.")
            if review:
                st.divider()
                st.markdown("#### Revisión automática")
                st.markdown(f"Estado: **{review.status}** · Comprobaciones: {', '.join(review.checks_performed) or '—'}")
                if review.issues:
                    for issue in review.issues:
                        icon = "⛔" if issue.severity == "error" else "⚠️"
                        st.markdown(f"{icon} **{issue.code}** · {issue.message}  \nReferencia: `{issue.reference_id}` · Corrección: `{issue.correction_stage}`")
                else:
                    st.success("La revisión automática no ha detectado errores bloqueantes. Esto no sustituye la lectura humana ni acredita la veracidad semántica de las fuentes.")


# ---------------------------------------------------------------------------
# Página: indicadores municipales (consulta MCP real)
# ---------------------------------------------------------------------------
elif page == "Indicadores oficiales":
    _render_header("Indicadores municipales", "Consulta en tiempo real el servidor MCP local. Los valores, estados, periodos y fuentes se leen de su respuesta; esta pantalla no conserva cifras duplicadas.")
    st.markdown('<div class="ff-note">Los hogares no equivalen a familias. Un indicador con valor <strong>null</strong> se presenta como «No disponible» y nunca como cero.</div>', unsafe_allow_html=True)
    st.write("")
    if st.button("Consultar indicadores MCP", type="primary"):
        _load_mcp()
    payload = st.session_state.get("ff_mcp")
    if st.session_state.get("ff_mcp_error"):
        st.error(f"No se pudo consultar MCP: {st.session_state['ff_mcp_error']}")
    if payload:
        result_df = _indicator_rows(payload)
        verified_count = int((result_df["Estado"] == "Verificado").sum()) if not result_df.empty else 0
        null_count = int((result_df["Estado"] == "No disponible").sum()) if not result_df.empty else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Indicadores devueltos", len(result_df))
        m2.metric("Verificados", verified_count)
        m3.metric("No disponibles", null_count)
        st.dataframe(result_df, hide_index=True, use_container_width=True, height=510, column_config={"Fuente": st.column_config.LinkColumn("Fuente", display_text="Abrir fuente")})
        st.markdown("#### Contexto de la fuente")
        st.write(payload.get("geo_scope") or "Ámbito no especificado por MCP")
        st.write(payload.get("period") or "Periodo no especificado por MCP")
        st.caption(payload.get("source") or "MCP no ha devuelto una fuente general.")
        if payload.get("limitations"):
            st.info(payload["limitations"])
        with st.expander("Respuesta estructurada original de MCP"):
            st.json(payload)
    else:
        st.info("Pulsa «Consultar indicadores MCP» para recuperar los datos oficiales desde el servidor local.")


# ---------------------------------------------------------------------------
# Página: aprobación y entrega
# ---------------------------------------------------------------------------
elif page == "Aprobación y entrega":
    _render_header("Aprobación y entrega", "Revisa el informe, registra tu decisión y genera únicamente los formatos autorizados.")
    bundle = None
    try:
        bundle = _get_review_bundle()
    except Exception as exc:
        st.error(f"La revisión ya no corresponde al contenido actual: {_redact_secrets(exc)}. Ejecuta una nueva revisión / estudio antes de aprobar.")
    if not bundle:
        st.info("Esta pantalla se habilita cuando el workflow ha producido borrador y revisión. Ejecuta primero un estudio real.")
    else:
        draft, research, metrics, review = bundle
        run_id = st.session_state["ff_run_id"]
        errors = [issue for issue in review.issues if issue.severity == "error"]
        warnings = [issue for issue in review.issues if issue.severity == "warning"]
        preview = render_report_preview(draft)
        c1, c2, c3 = st.columns(3)
        c1.metric("Documento", draft.draft_id[:12])
        c2.metric("Versión", draft.version)
        c3.metric("Errores bloqueantes", len(errors))
        st.markdown("#### Confirmación del contenido")
        with st.expander("Abrir informe completo antes de decidir", expanded=True):
            st.markdown(preview.markdown)
        if warnings:
            with st.expander(f"Avisos informativos ({len(warnings)})"):
                for issue in warnings:
                    st.warning(f"{issue.code}: {issue.message}")
        if errors:
            st.error("La aprobación está bloqueada hasta corregir todos los errores de revisión.")
            for issue in errors:
                st.markdown(f"- **{issue.code}** · {issue.message} · etapa: `{issue.correction_stage}`")
        else:
            st.success("No hay errores bloqueantes. La decisión sigue siendo exclusivamente humana.")

        existing_approval = st.session_state.get("ff_approval")
        if existing_approval:
            if existing_approval.approved:
                st.markdown('<span class="ff-status ff-status-ok">APROBACIÓN REGISTRADA</span>', unsafe_allow_html=True)
                st.caption(f"Decisión: {existing_approval.decided_at.isoformat()} · Huella: {existing_approval.draft_fingerprint[:20]}…")
            else:
                st.markdown('<span class="ff-status ff-status-warn">INFORME RECHAZADO</span>', unsafe_allow_html=True)
                st.caption(f"Decisión registrada: {existing_approval.decided_at.isoformat()}")

        if not existing_approval:
            st.divider()
            with st.form("ff_human_approval"):
                decision = st.radio("Tu decisión", ["Aprobar para exportar", "Rechazar informe"], horizontal=True)
                confirm_read = st.checkbox("He leído el informe, las fuentes y las limitaciones mostradas.")
                st.markdown("**Acciones que autorizo**")
                export_md = st.checkbox("Exportar Markdown (.md)", value=True, disabled=bool(errors) or decision.startswith("Rechazar"))
                export_pdf = st.checkbox("Exportar PDF (.pdf)", value=False, disabled=bool(errors) or decision.startswith("Rechazar"))
                update_csv = st.checkbox("Actualizar CSV de seguimiento", value=False, disabled=bool(errors) or decision.startswith("Rechazar"))
                submit_decision = st.form_submit_button("Registrar decisión humana", type="primary", use_container_width=True)
            if submit_decision:
                if not confirm_read:
                    st.error("Confirma que has leído el informe y sus limitaciones antes de registrar la decisión.")
                elif decision.startswith("Aprobar"):
                    chosen_actions = []
                    if export_md:
                        chosen_actions.append("export_markdown")
                    if export_pdf:
                        chosen_actions.append("export_pdf")
                    if update_csv:
                        chosen_actions.append("update_tracking_csv")
                    try:
                        record = create_approval_record(
                            run_id=run_id,
                            draft=draft,
                            research=research,
                            metrics=metrics,
                            review=review,
                            actions=chosen_actions,
                            approved=True,
                        )
                        st.session_state["ff_approval"] = record
                        st.session_state["ff_delivery"] = None
                        st.success("Decisión aprobada y ligada a la huella real del borrador.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No se pudo registrar la aprobación: {_redact_secrets(exc)}")
                else:
                    try:
                        record = create_approval_record(
                            run_id=run_id,
                            draft=draft,
                            research=research,
                            metrics=metrics,
                            review=review,
                            actions=(),
                            approved=False,
                        )
                        st.session_state["ff_approval"] = record
                        st.session_state["ff_delivery"] = None
                        st.warning("Rechazo registrado. No se podrá exportar este informe.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"No se pudo registrar el rechazo: {_redact_secrets(exc)}")

        approval = st.session_state.get("ff_approval")
        if approval and approval.approved:
            st.divider()
            st.markdown("#### Publicación controlada")
            allowed = ", ".join(approval.actions)
            st.caption(f"Acciones autorizadas en ApprovalRecord: {allowed}")
            previous_result = delivery_from_state(st.session_state.get("ff_delivery"))
            if st.button("Generar / reintentar entregables autorizados", type="primary", use_container_width=True):
                try:
                    # Última validación de la huella antes de crear archivos.
                    if calculate_draft_fingerprint(draft) != approval.draft_fingerprint:
                        raise ValueError("El borrador cambió después de aprobar; registra una nueva aprobación.")
                    result = export_approved_report(
                        draft,
                        approval,
                        run_id,
                        ROOT / "reports" / "generated",
                        csv_path=(ROOT / "reports" / "generated" / "tracking.csv")
                        if "update_tracking_csv" in approval.actions else None,
                        previous_result=previous_result,
                    )
                    st.session_state["ff_delivery"] = result
                    st.rerun()
                except Exception as exc:
                    st.error(f"La exportación no se ha completado: {_redact_secrets(exc)}")

            result = delivery_from_state(st.session_state.get("ff_delivery"))
            if result:
                if result.complete:
                    st.success("Todos los formatos autorizados se han publicado correctamente.")
                else:
                    st.warning("Entrega parcial: revisa los fallos y vuelve a intentar las acciones pendientes.")
                for action, path in (
                    ("Markdown", result.markdown_path),
                    ("PDF", result.pdf_path),
                    ("Seguimiento CSV", result.tracking_path),
                ):
                    if path and Path(path).is_file():
                        file_path = Path(path)
                        mime = "text/markdown" if file_path.suffix == ".md" else "application/pdf" if file_path.suffix == ".pdf" else "text/csv"
                        st.download_button(
                            f"Descargar {action}",
                            data=file_path.read_bytes(),
                            file_name=file_path.name,
                            mime=mime,
                            key=f"download_{file_path.suffix}_{file_path.name}",
                        )
                if result.errors:
                    for action, message in result.errors:
                        st.error(f"{action}: {_redact_secrets(message)}")


_render_footer()
