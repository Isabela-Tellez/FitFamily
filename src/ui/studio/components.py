"""Componentes visuales reutilizables de FitFamily Studio.

Los componentes reciben datos ya resueltos: no consultan servicios ni
inventan contenido. Siempre que existe un componente nativo de
Streamlit se prefiere (``st.metric``, ``st.container(border=True)``,
``st.dataframe``); el HTML propio queda para la ilustración y para
pequeños bloques de estado.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import streamlit as st

from src.ui.studio.copy import t
from src.ui.studio.formatting import (
    humanize,
    phase_kind,
    status_label,
    study_headline,
)
from src.ui.studio.state import format_value

# ---------------------------------------------------------------------------
# Cabeceras de página — un solo H1 por pantalla (accesibilidad)
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str = "", eyebrow: str | None = None) -> None:
    eyebrow_html = f'<div class="ff-eyebrow">{eyebrow}</div>' if eyebrow else ""
    subtitle_html = f'<p class="ff-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'{eyebrow_html}<h1>{title}</h1>{subtitle_html}',
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    subtitle_html = f'<div class="ff-section-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="ff-section-title">{title}</div>{subtitle_html}',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tarjetas y métricas
# ---------------------------------------------------------------------------
def metric_card(label: str, value: str, foot: str = "") -> str:
    """HTML de una tarjeta de métrica; se conserva para usos puntuales."""
    foot_html = f'<div class="ff-card-foot">{foot}</div>' if foot else ""
    return (
        f'<div class="ff-card"><div class="ff-card-label">{label}</div>'
        f'<div class="ff-card-value">{value}</div>{foot_html}</div>'
    )


def render_metrics(items: Sequence[tuple[str, str, str]], columns: int = 4) -> None:
    """Dibuja métricas nativas en tarjetas, con ayuda contextual."""
    compact = [item for item in items if len(item) >= 2]
    if not compact:
        return
    cols = st.columns(min(columns, len(compact)))
    for col, item in zip(cols, compact):
        label, value = item[0], item[1]
        help_text = item[2] if len(item) > 2 and item[2] else None
        col.metric(label, value, help=help_text, border=True)


def render_cards(items: Sequence[tuple[str, ...]], columns: int = 2) -> None:
    """Tarjetas de propósito con título y cuerpo, usando contenedores nativos."""
    if not items:
        return
    cols = st.columns(min(columns, len(items)))
    for col, item in zip(cols, items):
        title = item[0] if item else ""
        body = item[1] if len(item) > 1 else ""
        detail = item[2] if len(item) > 2 else ""
        with col:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                if body:
                    st.caption(body)
                if detail:
                    st.caption(detail)


# ---------------------------------------------------------------------------
# Estados visuales — siempre con texto, nunca solo color
# ---------------------------------------------------------------------------
def badge(text: str, kind: str = "muted") -> str:
    return f'<span class="ff-badge ff-badge-{kind}">{text}</span>'


def render_badge(text: str, kind: str = "muted") -> None:
    st.markdown(badge(text, kind), unsafe_allow_html=True)


def study_status_text(state: dict[str, Any] | None) -> str:
    """Frase única de estado del estudio, igual en toda la aplicación."""
    if not state:
        return t("status.no_study")
    return t("status.study", study=study_headline(state))


def render_study_status(state: dict[str, Any] | None) -> None:
    """Indicador compacto usado en la barra lateral y en las pantallas."""
    if not state:
        value = t("status.no_study")
        kind = "muted"
        phase = ""
    else:
        value = t("status.study", study=study_headline(state))
        raw = state.get("current_stage") or state.get("status")
        phase = status_label(raw)
        kind = phase_kind(raw)
    phase_html = badge(phase, kind) if phase else ""
    st.markdown(
        f'<div class="ff-study-status">'
        f'<div class="ff-study-status-title">Estudio activo</div>'
        f'<div class="ff-study-status-value">{value}</div>'
        f"{phase_html}</div>",
        unsafe_allow_html=True,
    )


def empty_state(
    title: str,
    message: str,
    action_label: str | None = None,
    page: str = "Nuevo estudio",
) -> None:
    """Estado vacío coherente con el resto del producto."""
    with st.container(border=True):
        st.markdown('<div class="ff-empty">', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        st.caption(message)
        st.markdown("</div>", unsafe_allow_html=True)
        if action_label:
            if st.button(
                action_label,
                type="primary",
                use_container_width=False,
                key=f"ff_empty_{page}_{action_label}",
            ):
                from src.ui.studio import navigation

                navigation.go(page)
                st.rerun()


def error_state(message: str) -> None:
    st.error(humanize(message))


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
_STAGE_ORDER = ["research", "analysis", "writing", "review", "approval", "delivery"]


def render_steps(state: dict[str, Any] | None) -> None:
    """Muestra el progreso del flujo. Sin estado: pasos en gris neutro."""
    current = str(state.get("current_stage") or "") if state else ""
    status = str(state.get("status") or "") if state else ""
    cols = st.columns(len(STAGES))
    for col, (icon, label, detail, stage) in zip(cols, STAGES):
        active = bool(state) and current == stage
        if not state:
            done = False
        elif status in {"completed", "rejected", "delivery_partial", "delivery_failed"}:
            done = stage != "approval" or status == "completed"
        elif current in _STAGE_ORDER and stage in _STAGE_ORDER:
            done = _STAGE_ORDER.index(stage) < _STAGE_ORDER.index(current)
        else:
            done = False
        color = "var(--ff-accent)" if (done or active) else "var(--ff-muted)"
        mark = "✓" if done else icon
        col.markdown(
            f'<div class="ff-step"><div class="ff-step-icon">{mark}</div>'
            f'<div><strong style="color:{color}">{label}</strong><span>{detail}</span></div></div>',
            unsafe_allow_html=True,
        )
    if state and status == "failed":
        st.warning("La revisión ha bloqueado la aprobación. Consulta las incidencias en Resultados.")


def render_how_it_works() -> None:
    """Cinco pasos numerados, en una fila y con altura homogénea."""
    steps = [
        ("Define el estudio", "Negocio, zona y preguntas."),
        ("Investigamos", "Fuentes y competidores."),
        ("Analizamos", "Indicadores y escenarios."),
        ("Redactamos", "Informe con fuentes."),
        ("Tú decides", "Apruebas o pides cambios."),
    ]
    cols = st.columns(5)
    for number, (col, (title, body)) in enumerate(zip(cols, steps), start=1):
        with col:
            with st.container(border=True, height=158):
                st.markdown(f"**{number}. {title}**")
                st.caption(body)


# ---------------------------------------------------------------------------
# Tablas de datos con valores «No disponibles» explícitos
# ---------------------------------------------------------------------------
def render_table(
    rows: Iterable[dict[str, Any]],
    empty_message: str,
    height: int | None = None,
    column_config: dict[str, Any] | None = None,
) -> None:
    import pandas as pd

    rows = list(rows)
    if not rows:
        st.info(empty_message)
        return
    df = pd.DataFrame(rows).fillna("No disponible")
    kwargs: dict[str, Any] = {"hide_index": True, "use_container_width": True}
    if height:
        kwargs["height"] = height
    if column_config:
        kwargs["column_config"] = column_config
    st.dataframe(df, **kwargs)


def footer() -> None:
    """Pie discreto; la aplicación lo muestra una sola vez en la sidebar."""
    st.caption(t("app.footer_note"))


# ---------------------------------------------------------------------------
# Ilustración de marca — sin texto superpuesto
# ---------------------------------------------------------------------------
def render_mascot(height: int = 260) -> None:
    """Ilustración original en SVG/CSS embebida con ``st.iframe``.

    No lleva rótulos encima: el mensaje de marca vive en la cabecera y
    en la barra lateral, nunca dentro de la imagen.
    """
    html = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;background:transparent;font-family:Arial,sans-serif}
    .scene{width:100%;height:260px;position:relative;overflow:hidden;background:linear-gradient(135deg,#e8f5ed,#d8efe2 60%,#f4f7df);border-radius:24px}
    .sun{position:absolute;width:72px;height:72px;right:9%;top:23px;border-radius:50%;background:#f6d66e;box-shadow:0 0 0 14px #f6d66e33}
    .cloud{position:absolute;width:95px;height:26px;left:9%;top:35px;border-radius:30px;background:#fff;opacity:.8}.cloud:before,.cloud:after{content:"";position:absolute;background:#fff;border-radius:50%}.cloud:before{width:34px;height:34px;left:14px;top:-17px}.cloud:after{width:43px;height:43px;left:40px;top:-22px}
    .floor{position:absolute;left:0;right:0;bottom:0;height:50px;background:#bddfc8;border-top:3px solid #9fceb0}
    svg{position:absolute;inset:0;width:100%;height:100%;transform:scale(0.9);transform-origin:center}.float{animation:float 3.4s ease-in-out infinite}.bob{transform-box:fill-box;transform-origin:center bottom;animation:bob 1.9s ease-in-out infinite}.ball{animation:roll 3s ease-in-out infinite}.spark{animation:twinkle 1.7s ease-in-out infinite alternate}
    @keyframes float{50%{transform:translateY(-7px)}}@keyframes bob{50%{transform:rotate(3deg) translateY(-2px)}}@keyframes roll{0%,100%{transform:translateX(0) rotate(0)}50%{transform:translateX(20px) rotate(180deg)}}@keyframes twinkle{to{opacity:.25;transform:scale(.7)}}
    @media(prefers-reduced-motion:reduce){.float,.bob,.ball,.spark{animation:none!important}}
    </style></head><body><div class="scene" role="img" aria-label="Ilustración animada de una familia: una persona entrena mientras una niña juega en una zona infantil segura.">
    <div class="sun"></div><div class="cloud"></div><div class="floor"></div>
    <svg viewBox="0 0 760 285" aria-hidden="true">
      <g class="spark" fill="#e5a63b"><path d="M118 105l5 12 12 5-12 5-5 12-5-12-12-5 12-5z"/><path d="M632 89l4 9 9 4-9 4-4 9-4-9-9-4 9-4z"/></g>
      <rect x="72" y="216" width="340" height="12" rx="6" fill="#8fc2a0"/><path d="M682 219q-23-40-4-67q28 18 15 67" fill="#65a77c"/><path d="M690 220q-5-44 23-58q13 32-12 58" fill="#438f68"/><rect x="676" y="218" width="40" height="17" rx="5" fill="#e9a27f"/>
      <g class="float"><path d="M246 148q-12 28-10 63" stroke="#176b55" stroke-width="22" stroke-linecap="round"/><path d="M246 148q26 5 39 28" stroke="#176b55" stroke-width="19" stroke-linecap="round"/><circle cx="248" cy="112" r="23" fill="#d99568"/><path d="M226 109q3-28 29-27q23 2 22 24q-23-8-51 3" fill="#283d37"/><path d="M238 170l-31 43" stroke="#176b55" stroke-width="14" stroke-linecap="round"/><path d="M267 176l34 30" stroke="#176b55" stroke-width="14" stroke-linecap="round"/><path d="M196 207h25M293 207h25" stroke="#d99568" stroke-width="10" stroke-linecap="round"/><path d="M279 135l42-24" stroke="#d99568" stroke-width="10" stroke-linecap="round"/><path d="M316 105h39" stroke="#31544a" stroke-width="7" stroke-linecap="round"/><rect x="311" y="94" width="8" height="23" rx="3" fill="#31544a"/><rect x="352" y="94" width="8" height="23" rx="3" fill="#31544a"/></g>
      <g class="bob"><circle cx="486" cy="152" r="18" fill="#ad6f4d"/><path d="M468 147q3-24 23-20q17 4 14 20q-16-8-37 0" fill="#4b3831"/><path d="M486 172l-3 42" stroke="#ff8e70" stroke-width="18" stroke-linecap="round"/><path d="M482 184l-28 22" stroke="#ad6f4d" stroke-width="9" stroke-linecap="round"/><path d="M490 183l26 15" stroke="#ad6f4d" stroke-width="9" stroke-linecap="round"/><path d="M483 212l-16 20M489 212l18 20" stroke="#405d9c" stroke-width="10" stroke-linecap="round"/><path d="M458 232h15M501 232h14" stroke="#fff" stroke-width="5" stroke-linecap="round"/></g>
      <g class="ball"><circle cx="550" cy="218" r="14" fill="#f1c94f"/><path d="M539 211q11 5 12 20M549 204q-3 11 12 18" stroke="#fff" stroke-width="3" fill="none"/></g>
      <rect x="545" y="133" width="78" height="78" rx="8" fill="#fff4db" stroke="#d9c69c" stroke-width="3"/><path d="M536 137l48-38 49 38" fill="#ff8e70" stroke="#d47a61" stroke-width="4"/><rect x="574" y="170" width="22" height="41" rx="10" fill="#b6d9c1"/><circle cx="561" cy="157" r="8" fill="#8ec5a4"/><circle cx="609" cy="157" r="8" fill="#8ec5a4"/>
    </svg></div></body></html>"""
    st.iframe(html, height=height)


def format_values(values: Iterable[object], empty: str = "Ninguno documentado.") -> str:
    values = list(values)
    return ", ".join(format_value(v) for v in values) if values else empty
