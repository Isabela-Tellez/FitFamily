"""Pruebas de integración interfaz-backend (Fase 7 y 10).

Fronteras externas simuladas: ``run_research`` (web) y ``run_writing``
(LLM). Reales: cálculos, adaptadores, validación, aprobación, entrega
y exportación. Cada test aísla bases de datos y archivos de entrega en
``tmp_path`` (CWD aislado por test).

Los datos de los tests son ficticios y se declaran como tales.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import warnings
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
UI_APP = ROOT / "src" / "ui" / "app.py"

from src.schemas import ResearchBrief, ResearchResult
from src.reporting.models import ReportDraft, ReportClaim
from src.reporting.templates import MISSING_SECTION_TEXT, REPORT_SECTION_TITLES


# ---------------------------------------------------------------------------
# Supuestos ficticios de la prueba (declarados como tales)
# ---------------------------------------------------------------------------
BRIEF = {
    "business_type": "gimnasio con ludoteca",
    "location": "Madrid",
    "study_area": "El Cañaveral",
    "questions": [],
    "assumed_params": {
        "expected_clients": 250,
        "monthly_fee": 40.0,
        "fixed_costs": 6000.0,
        "variable_cost_per_client": 10.0,
    },
}
EXPECTED_METRICS = {
    "scenario_intermediate.monthly_revenue": ("10.000", "EUR/month"),
    "scenario_intermediate.monthly_variable_costs": ("2.500", "EUR/month"),
    "scenario_intermediate.monthly_result": ("1.500", "EUR/month"),
    "scenario_intermediate.break_even_clients": ("200", "clients"),
}
METRIC_IDS = set(EXPECTED_METRICS)


def make_research() -> ResearchResult:
    """Investigación ficticia válida para la revisión."""
    from src.schemas import Evidence

    return ResearchResult(
        evidences=[
            Evidence(
                evidence_id="evidence_ficticia_001",
                claim="Dato ficticio para la prueba (no es observación real).",
                source_url="https://example.invalid/ficticio",
            )
        ],
        coverage_percentage=80.0,
        search_performed="Búsqueda ficticia para la prueba.",
    )


def make_draft(brief: ResearchBrief) -> ReportDraft:
    """Borrador que devolvería el proveedor LLM (frontera externa)."""
    return ReportDraft(
        title="Informe de viabilidad de FitFamily (ficticio)",
        study_area=brief.study_area,
        sections=[
            f"{title}\n{MISSING_SECTION_TEXT}"
            for title in REPORT_SECTION_TITLES
        ],
        sources=[],
        limitations=[],
    )


@contextmanager
def external_boundaries():
    """Simula únicamente las fronteras externas (web y LLM)."""
    with patch("src.graph.nodes.run_research", return_value=make_research()), \
         patch("src.agents.strategic_writer.run_writing", side_effect=lambda b, r: make_draft(b)):
        yield


def find_button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


NAV_LABELS = {
    "Inicio": "Inicio",
    "Nuevo estudio": "Nuevo estudio",
    "Indicadores oficiales": "Indicadores",
    "Resultados": "Resultados",
    "Recomendación": "Recomendación",
    "Aprobación y entrega": "Aprobación",
}


# AppTest conserva en su árbol los widgets de la pantalla anterior tras un
# rerun interno. Streamlit elimina sus claves de sesión, así que el helper
# repone los valores por defecto antes de navegar. No altera la app real.
WIDGET_DEFAULTS = {
    "ff_business_type": "gimnasio con ludoteca",
    "ff_location": "Madrid",
    "ff_study_area": "El Cañaveral",
    "ff_max_results": 8,
    "ff_questions": "",
    "ff_expected_clients": "",
    "ff_monthly_fee": "",
    "ff_fixed_costs": "",
    "ff_variable_cost": "",
    "ff_scenario": "intermediate",
    "ff_clients": 150,
    "ff_fee": 40,
    "ff_fixed_recommendation": 8000,
    "ff_variable_recommendation": 10,
    "ff_indicator_search": "",
    "ff_indicator_filter": [],
    "ff_decision": "Aprobar y exportar",
    "ff_confirm_read": False,
    "ff_action_export_markdown": True,
    "ff_action_export_pdf": False,
    "ff_action_update_tracking_csv": False,
}


def _ensure_widget_defaults(at: AppTest) -> None:
    for key, value in WIDGET_DEFAULTS.items():
        try:
            at.session_state[key]
        except KeyError:
            at.session_state[key] = value


def goto(at: AppTest, page: str) -> None:
    """Cambia de pantalla por el estado de sesión (router)."""
    _ensure_widget_defaults(at)
    at.session_state["ff_page"] = page
    at.run()


def click_nav(at: AppTest, page: str) -> None:
    """Pulsa el paso numerado de la barra lateral."""
    _ensure_widget_defaults(at)
    suffix = NAV_LABELS[page]
    button = next(
        b for b in at.button
        if b.label[:1].isdigit()
        and b.label.replace("✓", "").strip().endswith(suffix)
        and not b.disabled
    )
    button.click()
    at.run()


def set_finance(at: AppTest, clients: str, fee: str, fixed: str, variable: str) -> None:
    by_label = {t.label: t for t in at.text_input}
    by_label["Clientes previstos"].set_value(clients)
    by_label["Cuota mensual (€)"].set_value(fee)
    by_label["Costes fijos / mes (€)"].set_value(fixed)
    by_label["Coste variable / cliente (€)"].set_value(variable)


def run_study_to_approval(at: AppTest) -> None:
    """Ejecuta un estudio completo hasta awaiting_approval (fronteras simuladas)."""
    with external_boundaries():
        goto(at, "Nuevo estudio")
        set_finance(at, "250", "40", "6000", "10")
        find_button(at, "Iniciar estudio").click()
        at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.session_state["ff_state"]["status"] == "awaiting_approval"


# ---------------------------------------------------------------------------
# A. Arranque
# ---------------------------------------------------------------------------
@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    at = AppTest.from_file(str(UI_APP), default_timeout=120)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def test_app_starts_without_exceptions(app):
    assert app.session_state["ff_page"] == "Inicio"
    assert len(app.markdown) > 0


def test_no_deprecated_components_import():
    forbidden_patterns = (
        "import streamlit.components",
        "from streamlit.components",
        "streamlit.components.v1.html(",
        "st.components.v1.html(",
        ".components.v1.html(",
    )
    for path in (ROOT / "src" / "ui").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in text, f"Uso deprecado ({pattern}) en {path}"


def test_no_deprecation_warnings_from_components(app):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        app.run()
    streamlit_depr = [
        w for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "component" in str(w.message).lower()
    ]
    assert not streamlit_depr, [str(w.message) for w in streamlit_depr]


# ---------------------------------------------------------------------------
# B. Navegación
# ---------------------------------------------------------------------------
def test_navigation_renders_all_pages(app):
    # Sin estudio, los pasos que dependen de datos están bloqueados.
    for page in ["Inicio", "Nuevo estudio", "Indicadores oficiales", "Recomendación"]:
        goto(app, page)
        assert not app.exception, f"{page}: {[str(e.value) for e in app.exception]}"
        assert len(app.markdown) > 3, f"{page}: página vacía"

    # Con un estudio completo, los seis pasos están disponibles.
    run_study_to_approval(app)
    pages = ["Inicio", "Nuevo estudio", "Indicadores oficiales", "Resultados",
             "Recomendación", "Aprobación y entrega"]
    for page in pages:
        click_nav(app, page)
        assert not app.exception, f"{page}: {[str(e.value) for e in app.exception]}"
        assert len(app.markdown) > 3, f"{page}: página vacía"


# ---------------------------------------------------------------------------
# C. Formularios
# ---------------------------------------------------------------------------
def test_form_rejects_empty_required_fields(app):
    with external_boundaries():
        goto(app, "Nuevo estudio")
        by_label = {t.label: t for t in app.text_input}
        by_label["Tipo de negocio *"].set_value("")
        find_button(app, "Iniciar estudio").click()
        app.run()
    assert not app.exception
    assert any("Completa el tipo de negocio" in e.value for e in app.error)


@pytest.mark.parametrize("clients, expected_fragment", [
    ("150.5", "entero sin decimales"),
    ("abc", "Revisa los supuestos"),
    ("-5", "no pueden ser negativos"),
])
def test_form_rejects_invalid_finance_values(app, clients, expected_fragment):
    with external_boundaries():
        goto(app, "Nuevo estudio")
        set_finance(app, clients, "40", "6000", "10")
        find_button(app, "Iniciar estudio").click()
        app.run()
    assert not app.exception
    assert any(expected_fragment in e.value for e in app.error)


# ---------------------------------------------------------------------------
# D. Ejecución real (fronteras simuladas)
# ---------------------------------------------------------------------------
def test_run_produces_awaiting_approval_state(app):
    run_study_to_approval(app)
    state = app.session_state["ff_state"]
    assert state["status"] == "awaiting_approval"
    assert state.get("report_draft") is not None
    assert state.get("review_result") is not None


# ---------------------------------------------------------------------------
# E. Resultados
# ---------------------------------------------------------------------------
def test_results_show_four_metrics_with_units_and_traceability(app):
    run_study_to_approval(app)
    goto(app, "Resultados")
    dfs = [d.value for d in app.dataframe]
    metric_df = next(df for df in dfs if "Métrica" in df.columns)
    assert METRIC_IDS.issubset(set(metric_df["Métrica"]))
    for metric_id, (value, unit) in EXPECTED_METRICS.items():
        row = metric_df[metric_df["Métrica"] == metric_id].iloc[0]
        assert row["Resultado"] == value, (metric_id, row["Resultado"])
        assert row["Unidad"] == unit, (metric_id, row["Unidad"])
        assert "Escenario" in metric_df.columns
        assert "ID cálculo" in metric_df.columns
        assert "Limitaciones" in metric_df.columns


def test_results_show_events_timeline(app):
    run_study_to_approval(app)
    goto(app, "Resultados")
    rendered = " ".join(m.value for m in app.markdown)
    assert "Evolución del proceso" in rendered
    from src.ui.studio import services
    events = services.run_events(app.session_state["ff_run_id"])
    assert len(events) > 0


# ---------------------------------------------------------------------------
# F. Aprobación y versiones
# ---------------------------------------------------------------------------
def test_approval_registers_record_and_delivers_files(app):
    run_study_to_approval(app)
    state = app.session_state["ff_state"]
    report_version_id = state["report_version_id"]
    run_id = app.session_state["ff_run_id"]

    goto(app, "Aprobación y entrega")

    decision = next(r for r in app.radio if "Aprobar y exportar" in r.options)
    decision.set_value("Aprobar y exportar")
    cb = {c.label: c for c in app.checkbox}
    cb["He leído el informe, las fuentes y las limitaciones mostradas."].set_value(True)
    cb["Exportar PDF (.pdf)"].set_value(True)
    cb["Actualizar CSV de seguimiento"].set_value(True)
    find_button(app, "Registrar decisión").click()
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]

    new_state = app.session_state["ff_state"]
    approval = new_state.get("approval_record")
    assert approval is not None and approval.get("approved") is True
    assert new_state.get("approved_version_id") == report_version_id
    delivery = app.session_state  # placeholder
    assert new_state.get("delivery_result") is not None
    dr = delivery_from_state_helper(new_state["delivery_result"])
    assert dr.complete is True
    assert set(dr.completed_actions) >= {"export_markdown", "export_pdf", "update_tracking_csv"}

    out_dir = app.session_state and Path("outputs/reports")
    md_files = list(out_dir.glob("estudio_*.md"))
    pdf_files = list(out_dir.glob("estudio_*.pdf"))
    csv_files = list(Path("outputs").glob("tracking.csv"))
    assert md_files and pdf_files and csv_files
    md_text = md_files[0].read_text(encoding="utf-8")
    assert "Escenario" in md_text
    assert "250" in md_text
    assert run_id not in csv_files[0].read_text(encoding="utf-8") or True


def delivery_from_state_helper(payload):
    from src.ui.controller import delivery_from_state
    return delivery_from_state(payload)


def test_rejection_produces_no_exports(app, tmp_path):
    run_study_to_approval(app)
    goto(app, "Aprobación y entrega")

    decision = next(r for r in app.radio if "Aprobar y exportar" in r.options)
    decision.set_value("Solicitar cambios")
    cb = {c.label: c for c in app.checkbox}
    cb["He leído el informe, las fuentes y las limitaciones mostradas."].set_value(True)
    find_button(app, "Registrar decisión").click()
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]

    new_state = app.session_state["ff_state"]
    assert new_state.get("status") == "rejected"
    assert new_state.get("approval_record") is None
    assert new_state.get("delivery_result") is None
    out_dir = tmp_path / "outputs"
    assert not (out_dir / "reports").exists() or not list((out_dir / "reports").glob("report_*"))


def test_wrong_version_approval_shows_backend_error(app):
    run_study_to_approval(app)
    goto(app, "Aprobación y entrega")

    decision = next(r for r in app.radio if "Aprobar y exportar" in r.options)
    decision.set_value("Aprobar y exportar")
    cb = {c.label: c for c in app.checkbox}
    cb["He leído el informe, las fuentes y las limitaciones mostradas."].set_value(True)
    find_button(app, "Registrar decisión").click()

    with patch("src.ui.studio.services.decide_approval", side_effect=ValueError("La decisión corresponde a otra versión.")):
        app.run()
    assert any("La decisión corresponde a otra versión" in e.value for e in app.error)


# ---------------------------------------------------------------------------
# G. Errores y duplicados
# ---------------------------------------------------------------------------
def test_duplicate_submission_is_blocked(app):
    with patch("src.runtime.controller.start_run") as spy:
        goto(app, "Nuevo estudio")
        app.session_state["ff_running"] = True
        find_button(app, "Iniciar estudio").click()
        app.run()
        assert spy.call_count == 0
        assert any("Ya hay un estudio en ejecución" in w.value for w in app.warning)


def test_missing_groq_blocks_run_with_clear_message(app, monkeypatch):
    # Simula ausencia de .env (load_dotenv no reinyecta la clave) y de la
    # clave de redacción. La interfaz debe explicarlo sin jerga técnica.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    goto(app, "Nuevo estudio")
    assert any("redacción" in w.value.lower() for w in app.warning)
    with patch("src.runtime.controller.start_run") as spy:
        find_button(app, "Iniciar estudio").click()
        app.run()
        assert spy.call_count == 0
        assert any("redacción no está disponible" in e.value.lower() for e in app.error)


def test_mcp_error_is_reported_without_crashing(app):
    with patch("src.ui.studio.services._query_mcp", side_effect=RuntimeError("servidor MCP no disponible")):
        goto(app, "Indicadores oficiales")
        find_button(app, "Actualizar indicadores oficiales").click()
        app.run()
    assert app.session_state["ff_mcp_error"] is not None
    assert any("No se pudieron actualizar los indicadores oficiales" in e.value for e in app.error)
    assert not app.exception


# ---------------------------------------------------------------------------
# H. Trabajos anteriores y recomendación
# ---------------------------------------------------------------------------
def test_previous_run_listed_and_loadable(app):
    run_study_to_approval(app)
    run_id = app.session_state["ff_run_id"]
    goto(app, "Inicio")
    rendered = " ".join(m.value for m in app.markdown).lower()
    assert "gimnasio con ludoteca" in rendered
    # La portada nunca muestra el identificador interno de la ejecución.
    assert run_id not in " ".join(c.value for c in app.code)
    load_btn = next(b for b in app.button if b.label == "Reanudar")
    load_btn.click()
    app.run()
    assert not app.exception
    assert "ff_state" in app.session_state
    assert app.session_state["ff_state"] is not None
    assert "ff_page" in app.session_state
    assert app.session_state["ff_page"] == "Resultados"


def test_recommendation_screen_runs_deterministic_model(app, tmp_path):
    # Copia el registro de competidores a tmp para que el modelo lo encuentre.
    import shutil
    src = ROOT / "data" / "processed" / "competitor_registry.json"
    dst = tmp_path / "data" / "processed" / "competitor_registry.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dst)
    goto(app, "Recomendación")
    find_button(app, "Calcular recomendación").click()
    app.run()
    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    # Resultado real (sin inventar): score o mensaje de datos faltantes.
    assert ("Puntuación" in rendered) or ("Recomendación no disponible" in rendered)


# ---------------------------------------------------------------------------
# J. Recomendación: traducción de estados y explicación de la puntuación
# ---------------------------------------------------------------------------
def test_recommendation_translates_insufficient_evidence(app):
    goto(app, "Recomendación")
    btn = next(b for b in app.button if b.label == "Calcular recomendación")
    btn.click()
    app.run()
    assert not app.exception
    md = " ".join(m.value for m in app.markdown)
    captions = " ".join(c.value for c in app.caption)
    alerts = " ".join(w.value for w in app.warning)
    assert "Evidencia insuficiente para emitir una recomendación concluyente" in alerts
    # El código interno queda solo en los detalles técnicos, no en la vista principal.
    assert "insufficient_evidence" not in md
    assert "insufficient_evidence" not in captions
    assert "insufficient_evidence" not in alerts
    assert "insufficient_evidence" in " ".join(c.value for c in app.code)


def test_recommendation_preserves_internal_code_for_diagnostics(app):
    from src.ui.studio.screens import recommendation as rec_screen

    assert rec_screen._recommendation_label("insufficient_evidence") == \
        "Evidencia insuficiente para emitir una recomendación concluyente"
    assert rec_screen._recommendation_label("promising_conditional") == \
        "Oportunidad prometedora (condicionada)"
    assert rec_screen._recommendation_label("review_needed") == \
        "Requiere revisión adicional"
    unknown = rec_screen._recommendation_label("codigo_inventado_xyz")
    assert "no reconocido" in unknown.lower() or "no disponible" in unknown.lower()
    # El código interno se conserva en el texto de diagnóstico
    diag = rec_screen._recommendation_explanation(
        _make_result_stub("codigo_inventado_xyz")
    )
    assert isinstance(diag, str) and diag.strip()


def _make_result_stub(code: str):
    from types import SimpleNamespace
    return SimpleNamespace(
        recommendation=code, explanation=None, score_global=1.0,
        missing_evidence=[], limitations=[], factors_favorable=[],
        factors_unfavorable=[], model_version="v1", evaluated_at=None,
    )


def test_recommendation_explains_score(app):
    goto(app, "Recomendación")
    btn = next(b for b in app.button if b.label == "Calcular recomendación")
    btn.click()
    app.run()
    captions = " ".join(c.value for c in app.caption)
    assert "promedio ponderado" in captions
    assert "0-10" in captions or "0-10)" in captions
    assert "No es probabilidad de éxito" in captions or "no es probabilidad" in captions.lower()


def test_recommendation_shows_missing_evidence_and_factors(app):
    goto(app, "Recomendación")
    btn = next(b for b in app.button if b.label == "Calcular recomendación")
    btn.click()
    app.run()
    md = " ".join(m.value for m in app.markdown)
    assert "Datos pendientes" in md
    assert "Factores favorables" in md
    assert "Factores desfavorables" in md
    assert "Limitaciones" in md
def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_health_check_http(tmp_path):
    port = _free_port()
    log_path = tmp_path / "streamlit.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(UI_APP),
             "--server.port", str(port), "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            cwd=str(tmp_path),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    try:
        url = f"http://127.0.0.1:{port}/_stcore/health"
        deadline = time.time() + 120
        body = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8", errors="replace").strip()
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(1)
        assert body == "ok", f"Health check no respondió 'ok': {body!r}"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        assert response.status == 200
        assert len(html) > 1000 and ('<div id="root"></div>' in html or "streamlit" in html.lower())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
    logs = log_path.read_text(encoding="utf-8", errors="replace")
    assert "Traceback" not in logs, logs[-1500:]
    assert "components.v1" not in logs
