"""Componentes visuales reutilizables de FitFamily Studio.

Cabeceras, tarjetas, pasos, estados y pies de página. Todo componente
recibe datos ya resueltos: no consulta servicios ni inventa contenido.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import streamlit as st

from src.ui.studio.state import format_value

# ---------------------------------------------------------------------------
# Cabecera de página — un solo H1 por pantalla (accesibilidad)
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str, eyebrow: str = "FITFAMILY STUDIO") -> None:
    st.markdown(
        f'<div class="ff-eyebrow">{eyebrow}</div>'
        f'<h1 style="margin:4px 0 6px;">{title}</h1>'
        f'<p class="ff-muted" style="margin:0 0 4px; max-width:720px; line-height:1.55;">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    body = f'<div class="ff-panel-title">{title}</div>'
    if subtitle:
        body += f'<div class="ff-muted" style="font-size:.88rem; margin-bottom:6px;">{subtitle}</div>'
    st.markdown(body, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tarjetas de información
# ---------------------------------------------------------------------------
def metric_card(label: str, value: str, foot: str = "") -> str:
    """Devuelve HTML de una tarjeta de métrica (para usar dentro de columns)."""
    foot_html = f'<div class="ff-card-foot">{foot}</div>' if foot else ""
    return (
        f'<div class="ff-card"><div class="ff-card-label">{label}</div>'
        f'<div class="ff-card-value">{value}</div>{foot_html}</div>'
    )


def render_metrics(items: Sequence[tuple[str, str, str]], columns: int = 4) -> None:
    """Dibuja una fila de tarjetas métricas. items = [(label, value, foot)]."""
    if not items:
        return
    cols = st.columns(min(columns, len(items)))
    for i, (label, value, foot) in enumerate(items):
        cols[i].markdown(metric_card(label, value, foot), unsafe_allow_html=True)


def render_cards(items: Sequence[tuple[str, str, str]], columns: int = 2) -> None:
    """Tarjetas de propósito con icono/título/pie (mismo patrón que metric_card)."""
    if not items:
        return
    cols = st.columns(min(columns, len(items)))
    for i, (label, value, foot) in enumerate(items):
        cols[i].markdown(metric_card(label, value, foot), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Estados visuales — siempre con texto, nunca solo color
# ---------------------------------------------------------------------------
def badge(text: str, kind: str = "muted") -> str:
    return f'<span class="ff-badge ff-badge-{kind}">{text}</span>'


def render_badge(text: str, kind: str = "muted") -> None:
    st.markdown(badge(text, kind), unsafe_allow_html=True)


def empty_state(title: str, message: str, action_label: str | None = None) -> None:
    """Estado vacío informativo con acción opcional."""
    st.markdown(
        f'<div class="ff-card" style="text-align:center; padding:34px 24px;">'
        f'<div class="ff-panel-title" style="margin-bottom:6px;">{title}</div>'
        f'<div class="ff-muted" style="font-size:.9rem; line-height:1.6; max-width:520px; margin:0 auto;">{message}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    if action_label:
        if st.button(action_label, type="primary", use_container_width=False):
            from src.ui.studio import navigation
            navigation.go("Nuevo estudio")
            st.rerun()


def error_state(message: str) -> None:
    st.markdown(
        f'<div class="ff-note" style="border-left-color:var(--ff-danger); background:#FBEAEA;">'
        f"<strong>No se pudo completar la operación.</strong><br>{message}</div>",
        unsafe_allow_html=True,
    )


def note(text: str) -> None:
    st.markdown(f'<div class="ff-note">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pasos del flujo (investigar → analizar → redactar → revisar → aprobar)
# ---------------------------------------------------------------------------
STAGES: list[tuple[str, str, str, str]] = [
    ("🔎", "Investigar", "Fuentes y competidores", "research"),
    ("📐", "Analizar", "Cálculos con supuestos", "analysis"),
    ("📝", "Redactar", "Informe trazable", "writing"),
    ("🛡️", "Revisar", "Control de calidad", "review"),
    ("✍️", "Aprobar", "Decisión humana", "approval"),
]
_COMPLETED_ORDER = ["analysis", "writing", "review", "approval"]


def render_steps(state: dict[str, Any] | None) -> None:
    """Muestra el progreso del flujo. Sin estado: pasos en gris neutro."""
    current = state.get("current_stage") if state else None
    cols = st.columns(len(STAGES))
    for col, (icon, label, detail, stage) in zip(cols, STAGES):
        if state and current in _COMPLETED_ORDER and stage in _COMPLETED_ORDER:
            done = _COMPLETED_ORDER.index(stage) < _COMPLETED_ORDER.index(current)
        elif state:
            done = stage == "research" and current != "research"
        else:
            done = False
        active = bool(state) and current == stage
        color = "var(--ff-accent)" if (done or active) else "var(--ff-muted)"
        mark = "✓" if done else icon
        col.markdown(
            f'<div class="ff-step"><div class="ff-step-icon">{mark}</div>'
            f'<div><strong style="color:{color}">{label}</strong><span>{detail}</span></div></div>',
            unsafe_allow_html=True,
        )
    if state and state.get("status") == "failed":
        st.warning("El control de revisión ha bloqueado la aprobación. Consulta las incidencias en Resultados.")


# ---------------------------------------------------------------------------
# Tablas de datos con valores «No disponibles» explícitos
# ---------------------------------------------------------------------------
def render_table(rows: Iterable[dict[str, Any]], empty_message: str, height: int | None = None) -> None:
    import pandas as pd

    rows = list(rows)
    if not rows:
        st.info(empty_message)
        return
    df = pd.DataFrame(rows).fillna("No disponible")
    kwargs: dict[str, Any] = {"hide_index": True, "use_container_width": True}
    if height:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


def footer() -> None:
    st.markdown(
        '<div class="ff-footer">FitFamily Studio · Evidencia antes que prosa · '
        "Los datos ausentes siguen siendo no disponibles · La exportación requiere aprobación humana.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Ilustración de marca — compatibilidad con Streamlit 1.56+
# ---------------------------------------------------------------------------
def render_mascot(height: int = 260) -> None:
    """Ilustración original en SVG/CSS embebida con ``st.iframe``.

    Streamlit 1.56 depreca ``st.components.v1.html`` (retirada tras
    2026-06-01). ``st.iframe`` acepta HTML en crudo y evita la
    dependencia deprecada: no se importa ``streamlit.components.v1``
    en ninguna parte de esta interfaz.
    """
    html = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;background:transparent;font-family:Arial,sans-serif}
    .scene{width:100%;height:260px;position:relative;overflow:hidden;background:linear-gradient(135deg,#e8f5ed,#d8efe2 60%,#f4f7df);border-radius:24px}
    .sun{position:absolute;width:72px;height:72px;right:9%;top:23px;border-radius:50%;background:#f6d66e;box-shadow:0 0 0 14px #f6d66e33}
    .cloud{position:absolute;width:95px;height:26px;left:9%;top:35px;border-radius:30px;background:#fff;opacity:.8}.cloud:before,.cloud:after{content:"";position:absolute;background:#fff;border-radius:50%}.cloud:before{width:34px;height:34px;left:14px;top:-17px}.cloud:after{width:43px;height:43px;left:40px;top:-22px}
    .floor{position:absolute;left:0;right:0;bottom:0;height:50px;background:#bddfc8;border-top:3px solid #9fceb0}
    .sign{position:absolute;left:6%;top:15px;color:#176b55;font-size:11px;font-weight:800;letter-spacing:2px}
    svg{position:absolute;inset:0;width:100%;height:100%;transform:scale(0.88);transform-origin:top center}.float{animation:float 3.4s ease-in-out infinite}.bob{transform-box:fill-box;transform-origin:center bottom;animation:bob 1.9s ease-in-out infinite}.ball{animation:roll 3s ease-in-out infinite}.spark{animation:twinkle 1.7s ease-in-out infinite alternate}
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
    st.iframe(html, height=height)


def format_values(values: Iterable[object], empty: str = "Ninguno documentado.") -> str:
    values = list(values)
    return ", ".join(format_value(v) for v in values) if values else empty
