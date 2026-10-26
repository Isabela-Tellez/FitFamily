# Mapa de módulos e interfaces

Base `dev` (`3586712`), 23/10/2026. Incluye PR #9, #10, #11, #12, #13, #14, #15, #16, #17, #18, #19.

## Flujo completo del proyecto

```text
Persona 1 (Juan) — Investigación y herramientas
  ResearchBrief
     │
     ▼
  run_research(brief) ─────► ResearchResult ──────► WriterAgent / CrewAI (Gema)
     │                              │
     ├── search_web()               ├── Evidence IDs (deterministas)
     ├── read_web_page()            ├── Competitor registry
     ├── competitor_search()        ├── Discovery sources
     └── discover_sources()         └── Coverage / unresolved questions

  MCP local (Juan)
     python -m src.mcp.server ──► get_area_statistics() ──► Datos municipales
     python -m src.mcp.client ──► connect_mcp() / call_area_statistics()

Persona 2 (Laura) — Análisis y escenarios
  ResearchResult ──► summarize_competitors(DataFrame) ──► dict (precios, ludoteca, escenarios)
  Scenarios: break-even, análisis descriptivo

Persona 3 (Gema) — Redacción, informes y automatización
  ResearchResult ──► WriterAgent.create_draft() (determinista) / run_writing() (CrewAI + Groq) ──► ReportDraft
     │
     ├── build_report(brief, research_result) ──► valida referencias (Writer determinista)
     └── build_report(brief, research_result, use_llm=True) ──► valida referencias (CrewAI + Groq)
  ReportDraft ──► render_report_markdown(draft) ──► Markdown (en memoria, no archivo)
  ReportDraft ──► render_report_pdf(draft) ──► PDF (bytes en memoria, no archivo)
  ReportDraft + ApprovalRecord ──► export_markdown() / export_pdf() ──► archivo publicado

Persona 4 (María) — Revisión crítica, validaciones y seguridad
  Review routes: validación de evidencias citadas, control de duplicados, SSRF,
  control de calidad (quality_checks.py, validation.py, review_routes.py)

Persona 5 (Isabella) — Streamlit, LangGraph, aprobación humana y estado compartido
  ApprovalRecord (autorización del borrador) ──► exportación PDF / Markdown
  Conexión Streamlit / LangGraph / flujo global
```

## Módulos y responsabilidades por persona

| Persona | Rol | Módulo / Archivo | Notas |
|---|---|---|---|
| **1 Juan** | Investigación / MCP | `src/agents/researcher.py` | `run_research`, `build_researcher`, `build_research_task` |
| **1 Juan** | Investigación / MCP | `src/mcp/server.py`, `src/mcp/client.py` | `get_area_statistics`, cliente con comprobación |
| **1 Juan** | Investigación / MCP | `src/tools/search_web.py` | Validación URL, SSRF, límites |
| **1 Juan** | Investigación / MCP | `src/tools/read_web_page.py` | Bloqueo IPs privadas, redirecciones |
| **1 Juan** | Investigación / MCP | `src/tools/competitor_search.py`, `source_discovery.py` | Registro de competidores, IDs deterministas |
| **2 Laura** | Análisis / escenarios | `src/analysis/market_analysis.py` | `summarize_competitors` (requiere DataFrame) |
| **2 Laura** | Análisis / escenarios | `src/analysis/scenarios.py` | Break-even, escenarios de mercado |
| **3 Gema** | Redactor / informes | `src/agents/writer_agent.py` | `WriterAgent.create_draft()` (sin LLM por defecto) |
| **3 Gema** | Redactor / informes | `src/agents/writer_llm.py` | `build_writer_llm()` (cliente CrewAI + Groq) |
| **3 Gema** | Redactor / informes | `src/agents/strategic_writer.py` | `build_writer()`, `build_writing_task()`, `run_writing()` |
| **3 Gema** | Redactor / informes | `src/reporting/report_builder.py` | `build_report`, `find_missing_evidence_ids`, `validate_report_references` |
| **3 Gema** | Redactor / informes | `src/reporting/markdown_renderer.py` | `render_report_markdown()` (texto en memoria) |
| **3 Gema** | Redactor / informes | `src/reporting/pdf_renderer.py` | `render_report_pdf()` (PDF en memoria) |
| **3 Gema** | Automatización | `src/automation/exporter.py`, `models.py` | `ApprovalRecord`, `export_markdown()` / `export_pdf()` con aprobación, publicación atómica |
| **4 María** | Revisión / validación | `src/review/validation.py` | Validación de referencias existentes |
| **4 María** | Revisión / validación | `src/review/quality_checks.py` | Control de calidad de evidencias citadas |
| **4 María** | Revisión / validación | `src/review/models.py` | Modelo de revisión |
| **4 María** | Revisión / validación | `tests/test_review_validation.py` | Pruebas de validación |
| **4 María** | Revisión / validación | `tests/test_evidence_quality.py`, `test_quality_checks.py` | Pruebas de calidad |
| **5 Isabella** | Streamlit / aprobación | `docs/streamlit-approval.md` | Contrato de UI y aprobación |
| **5 Isabella** | Streamlit / aprobación | `docs/langgraph-flow.md` | Estado, nodos y transiciones |
| **5 Isabella** | Streamlit / aprobación | `src/ui/` | Carpeta reservada para la app Streamlit |

## Limitaciones conocidas

- `run_research` usa `max_results=5` por defecto (configurable con `brief.search_limits`).
- `WriterAgent.create_draft()` no conecta automáticamente con `summarize_competitors`; requiere adaptador manual o integración futura.
- El análisis de mercado (`market_analysis`) no consume automáticamente `ResearchResult`.
- La orquestación LLM (`CrewAI`) se integra como ruta separada (`run_writing`) y se conectará al flujo global (`main.py`).
- `coverage_percentage` sigue como `0.0` en `ResearchResult`; no se calcula automáticamente.
- `docs/streamlit-approval.md` y `docs/langgraph-flow.md` documentan el diseño de la Persona 5; la UI y el grafo se conectarán en la orquestación.
- `tests/` cubre investigación, web, MCP, redacción, exportación, validación y revisión; la cobertura del análisis (`market_analysis`) es limitada.
- `docs/arquitectura-modulos.md` fue actualizado para esta rama (`dev`) con referencias a todos los PRs nuevos.

## Documentación por persona

| Persona | Ficha | Documentos de módulo |
|---|---|---|
| **1 · Juan** | [equipo.md#persona-1](equipo.md#persona-1) | [research-module.md](research-module.md), [research-implementation.md](research-implementation.md), [auditoria-fuentes-datos.md](auditoria-fuentes-datos.md), [research-changelog.md](research-changelog.md) |
| **2 · Laura** | [equipo.md#persona-2](equipo.md#persona-2) | [analysis.md](analysis.md) |
| **3 · Gema** | [equipo.md#persona-3](equipo.md#persona-3) | [report-export.md](report-export.md), [writer-llm.md](writer-llm.md) |
| **4 · María** | [equipo.md#persona-4](equipo.md#persona-4) | [review-quality.md](review-quality.md) |
| **5 · Isabella** | [equipo.md#persona-5](equipo.md#persona-5) | [streamlit-approval.md](streamlit-approval.md), [langgraph-flow.md](langgraph-flow.md) |
