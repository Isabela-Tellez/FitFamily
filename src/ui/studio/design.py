"""FitFamily Studio — sistema de diseño centralizado.

Todos los componentes visuales importan los tokens de este módulo.
No hay CSS disperso: una sola fuente de verdad para color, tipografía,
espaciado, radios y sombras.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Tokens de color (paleta verde bosque)
# ---------------------------------------------------------------------------
COLORS = {
    "primary": "#102B2A",        # tinta principal / cabeceras
    "primary_hover": "#19403D",
    "accent": "#237A67",         # acento interactivo
    "accent_soft": "#E6F2ED",
    "bg": "#F5F7F6",             # papel
    "surface": "#FFFFFF",
    "text": "#182624",
    "muted": "#667570",
    "border": "#E1E8E4",
    "success": "#23845D",
    "success_bg": "#E6F2ED",
    "warning": "#B7791F",
    "warning_bg": "#FFF6E0",
    "danger": "#B54747",
    "danger_bg": "#FBEAEA",
    "info": "#316C9B",
    "info_bg": "#EAF2F8",
}

# ---------------------------------------------------------------------------
# Tipografía y espaciado
# ---------------------------------------------------------------------------
FONT_FAMILY = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"
RADIUS = {"sm": "8px", "md": "12px", "lg": "16px", "xl": "20px"}
SPACING = {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px"}
SHADOW = "0 3px 14px rgba(16, 43, 42, 0.05)"

# ---------------------------------------------------------------------------
# CSS global — se inyecta una sola vez desde app.py
# ---------------------------------------------------------------------------
GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  --ff-primary: {COLORS['primary']};
  --ff-primary-hover: {COLORS['primary_hover']};
  --ff-accent: {COLORS['accent']};
  --ff-accent-soft: {COLORS['accent_soft']};
  --ff-bg: {COLORS['bg']};
  --ff-surface: {COLORS['surface']};
  --ff-text: {COLORS['text']};
  --ff-muted: {COLORS['muted']};
  --ff-border: {COLORS['border']};
  --ff-success: {COLORS['success']};
  --ff-warning: {COLORS['warning']};
  --ff-danger: {COLORS['danger']};
  --ff-info: {COLORS['info']};
  --ff-radius-sm: {RADIUS['sm']};
  --ff-radius-md: {RADIUS['md']};
  --ff-radius-lg: {RADIUS['lg']};
  --ff-radius-xl: {RADIUS['xl']};
  --ff-shadow: {SHADOW};
  --ff-font: {FONT_FAMILY};
}}

html, body, [class*="css"] {{ font-family: var(--ff-font); }}
.stApp {{ background: var(--ff-bg); color: var(--ff-text); }}

/* ---- Tipografía: un solo H1 por página, jerarquía estable ---- */
h1 {{ font-weight: 800 !important; letter-spacing: -0.02em; color: var(--ff-primary); }}
h2 {{ font-weight: 700 !important; letter-spacing: -0.01em; color: var(--ff-primary); }}
h3 {{ font-weight: 650 !important; color: var(--ff-text); }}

/* ---- Contenedor ---- */
.block-container {{ max-width: 1360px; padding-top: 1.6rem; padding-bottom: 3.5rem; }}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {{
  background: var(--ff-surface);
  border-right: 1px solid var(--ff-border);
}}
[data-testid="stHeader"] {{ background: rgba(245, 247, 246, 0.9); }}

/* ---- Tarjetas ---- */
.ff-card {{
  background: var(--ff-surface);
  border: 1px solid var(--ff-border);
  border-radius: var(--ff-radius-lg);
  padding: 20px 22px;
  box-shadow: var(--ff-shadow);
  height: 100%;
}}
.ff-card-label {{
  font-size: 0.74rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--ff-muted);
}}
.ff-card-value {{
  font-size: 1.75rem; font-weight: 800; letter-spacing: -0.03em;
  color: var(--ff-primary); margin: 6px 0 4px;
}}
.ff-card-foot {{ font-size: 0.78rem; color: var(--ff-muted); line-height: 1.45; }}

/* ---- Secciones ---- */
.ff-eyebrow {{
  font-size: 0.72rem; font-weight: 800; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ff-accent);
}}
.ff-panel-title {{ font-size: 1.4rem; font-weight: 800; letter-spacing: -0.02em; color: var(--ff-primary); margin: 2px 0 4px; }}
.ff-muted {{ color: var(--ff-muted); }}

/* ---- Estados (etiquetas con texto, no solo color) ---- */
.ff-badge {{
  display: inline-block; padding: 5px 11px; border-radius: 999px;
  font-size: 0.71rem; font-weight: 800; letter-spacing: 0.04em;
  text-transform: uppercase;
}}
.ff-badge-ok {{ background: var(--ff-success-bg, #E6F2ED); color: var(--ff-success); }}
.ff-badge-warn {{ background: #FFF6E0; color: var(--ff-warning); }}
.ff-badge-danger {{ background: #FBEAEA; color: var(--ff-danger); }}
.ff-badge-muted {{ background: #F0F2F5; color: var(--ff-muted); }}

/* ---- Nota informativa ---- */
.ff-note {{
  border-left: 4px solid var(--ff-accent);
  background: var(--ff-accent-soft);
  border-radius: 0 var(--ff-radius-md) var(--ff-radius-md) 0;
  padding: 13px 16px; font-size: 0.87rem; color: var(--ff-primary);
  line-height: 1.55;
}}

/* ---- Pasos del flujo ---- */
.ff-step {{
  display: flex; gap: 11px; align-items: center;
  background: var(--ff-surface); border: 1px solid var(--ff-border);
  border-radius: var(--ff-radius-md); padding: 12px 14px; min-height: 66px;
}}
.ff-step-icon {{
  width: 34px; height: 34px; border-radius: var(--ff-radius-sm);
  background: var(--ff-accent-soft); display: flex; align-items: center;
  justify-content: center; font-size: 1rem; flex-shrink: 0;
}}
.ff-step strong {{ display: block; font-size: 0.83rem; color: var(--ff-text); }}
.ff-step span {{ display: block; font-size: 0.71rem; color: var(--ff-muted); margin-top: 2px; }}

/* ---- Botones ---- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: var(--ff-radius-md); font-weight: 700; min-height: 42px;
  transition: all .15s ease;
}}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
  background: var(--ff-accent); border-color: var(--ff-accent); color: #fff;
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {{
  background: var(--ff-primary-hover); border-color: var(--ff-primary-hover);
}}

/* ---- Formularios ---- */
.stTextInput input, .stTextArea textarea, .stNumberInput input {{
  border-radius: var(--ff-radius-md) !important;
  border-color: var(--ff-border) !important;
}}
[data-testid="stExpander"] {{
  background: var(--ff-surface); border: 1px solid var(--ff-border);
  border-radius: var(--ff-radius-md);
}}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border: 1px solid var(--ff-border); border-radius: var(--ff-radius-md);
  overflow: hidden;
}}
div[data-testid="stMetric"] {{
  background: var(--ff-surface); border: 1px solid var(--ff-border);
  padding: 15px 17px; border-radius: var(--ff-radius-lg);
}}
div[data-testid="stMetricLabel"] {{ color: var(--ff-muted); }}
div[data-testid="stMetricValue"] {{ color: var(--ff-primary); font-weight: 800; }}

/* ---- Pie ---- */
.ff-footer {{
  font-size: 0.74rem; color: var(--ff-muted); padding: 16px 0 4px;
  border-top: 1px solid var(--ff-border); margin-top: 28px;
}}

/* ---- Accesibilidad ---- */
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration: .01ms !important; transition-duration: .01ms !important; }}
}}
@media (max-width: 900px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
  .ff-card {{ padding: 16px; }}
}}
</style>
"""


def inject() -> None:
    """Inyecta el CSS global una sola vez (idempotente por sesión)."""
    import streamlit as st

    if st.session_state.get("_ff_css_injected"):
        return
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.session_state["_ff_css_injected"] = True
