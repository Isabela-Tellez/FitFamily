# FitFamily

FitFamily analiza la viabilidad de abrir un gimnasio con ludoteca en El Cañaveral (Madrid). Es una plataforma de investigación de mercado con trazabilidad completa, redacción con o sin LLM, análisis descriptivo, exportación aprobada (Markdown y PDF) y revisión crítica de evidencias.

Estado: **funcional**. Todos los módulos principales implementados; pendiente la interfaz de usuario y la orquestación global (`main.py` / Streamlit).

| Módulo | Responsable | Estado |
|---|---|---|
| Investigación / MCP | Juan | ✅ Funcional |
| Análisis descriptivo | Laura | ✅ Funcional |
| Redacción (determinista + CrewAI) | Gema | ✅ Funcional |
| Exportación Markdown + PDF con aprobación | Gema | ✅ Funcional |
| Revisión crítica / validación / seguridad | María | ✅ Funcional |
| Streamlit / aprobación humana / LangGraph | Isabella | ⚠️ Pendiente |

## Caso de uso principal

Un investigador configura `ResearchBrief`, obtiene `ResearchResult` con evidencias trazables (`evidence_id`), genera un `ReportDraft` con validación de referencias, obtiene aprobación (`ApprovalRecord`) y exporta a Markdown o PDF con huella de contenido.

## Estado actual

| Área | Estado |
|---|---|
| Investigación web y búsqueda de competidores | Funcional |
| Evidencias con IDs deterministas y límites de búsqueda | Funcional |
| Descubrimiento de fuentes para variables pendientes | Funcional |
| Servidor MCP con 13 indicadores locales | Funcional |
| Registro de competidores desde el censo municipal | Funcional; preparación offline |
| Análisis descriptivo (`summarize_competitors`, `scenarios`) | Funcional |
| Borrador de informe determinista (`WriterAgent`) | Funcional |
| Borrador con LLM (`run_writing`, `use_llm=True`) | Funcional (integrado en `build_report`) |
| Trazabilidad del borrador (`draft_id`, `version`, `claims`) | Funcional |
| Validación de referencias (`validate_report_references`) | Funcional |
| Control de calidad y revisión crítica (`review`) | Funcional |
| Exportación Markdown (`markdown_renderer`) | Funcional |
| Exportación PDF (`pdf_renderer`) | Funcional; requiere autorización |
| Configuración básica de trazas LangSmith | Funcional (`.env.example`) |
| CLI / orquestador / UI (`main.py`, Streamlit) | Pendiente |
| Conexión completa del flujo global (investigación → análisis → informe → exportación) | Pendiente; contrato funcional pero sin orquestador automático |

## Requisitos

- Python 3.13, Git, conexión a internet para herramientas web.
- `GROQ_API_KEY` para usar CrewAI (`use_llm=True`).
- `pyproj` opcional para conversión de coordenadas UTM → WGS84.
- `reportlab` para exportación PDF.

```bash
git clone https://github.com/Isabela-Tellez/FitFamily.git
cd FitFamily
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Uso rápido

### Investigación básica

```python
from src.agents.researcher import run_research
from src.schemas import ResearchBrief

brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location="Madrid",
    study_area="El Cañaveral",
    questions=["precios", "servicios"],
    search_limits={"max_results": 5},
)
result = run_research(brief)
```

### Borrador con validación

```python
from src.reporting.report_builder import build_report
from src.schemas import ResearchBrief

draft = build_report(brief, result)
```

### Borrador con LLM (CrewAI + Groq)

```python
draft_llm = build_report(brief, result, use_llm=True)
```

### Exportación a Markdown y PDF (requiere aprobación)

```python
from src.automation.exporter import build_pdf_report, build_markdown_report
from src.reporting.report_builder import build_report_markdown
# Tras validar ApprovalRecord:
pdf = build_pdf_report(draft, approval=approval_record)
md_text = build_report_markdown(brief, result)
```

### Pruebas

```bash
python -m pytest -q
python -m compileall -q src tests data/raw
```

- **193 tests pasan**, 36 warnings de deprecación en CrewAI (no fallos).
- Pruebas del investigador sustituyen herramientas web por respuestas controladas.
- MCP arranca subproceso local.

## Documentación por módulo

- [Arquitectura y módulos](docs/arquitectura-modulos.md)
- [Investigación](docs/research-module.md)
- [Implementación](docs/research-implementation.md)
- [Auditoría de fuentes](docs/auditoria-fuentes-datos.md)
- [Changelog de investigación](docs/research-changelog.md)
- [Report export y PDF](docs/report-export.md)
- [LLM writer con CrewAI](docs/writer-llm.md)
- [Pendiente renta/ine y análisis](docs/pendiente-renta-ine.md)

## Licencia

MIT. Ver [LICENSE](LICENSE).
