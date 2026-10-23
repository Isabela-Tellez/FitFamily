# Mapa de módulos e interfaces — Estado actualizado

Estado: base `dev` (`3586712`), 23/10/2026. Incluye PR #9, #10, #11, #12, #13, #14, #15, #16, #17, #18, #19.

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
  ResearchResult ──► WriterAgent.create_draft() / run_writing(use_llm=True) ──► ReportDraft
     │
     ├── build_report(brief, research_result) ──► valida referencias (ValueError si faltan)
     └── build_report_markdown() ──► texto Markdown
  ReportDraft ──► build_report_markdown() ──► Markdown (en memoria, no archivo)
  ApprovalRecord ──► exporter.py (PDF / Markdown) ──► archivo publicado

Persona 4 (María) — Revisión crítica, validaciones y seguridad
  Review routes: validación de evidencias citadas, control de duplicados, SSRF,
  control de calidad (quality_checks.py, validation.py, review_routes.py)

Persona 5 (Isabella) — Streamlit, LangGraph, aprobación humana y estado compartido
  ApprovalRecord (autorización del borrador) ──► exportación PDF / Markdown
  Estado compartido pendiente: conexión Streamlit / LangGraph / flujo global
```

## Módulos implementados por persona

| Persona | Rol | Módulo / Archivo | Estado | Notas |
|---|---|---|---|---|
| **1 Juan** | Investigación / MCP | `src/agents/researcher.py` | Funcional | `run_research`, `build_researcher`, `build_research_task` |
| **1 Juan** | Investigación / MCP | `src/mcp/server.py`, `src/mcp/client.py` | Funcional | `get_area_statistics`, cliente con comprobación |
| **1 Juan** | Investigación / MCP | `src/tools/search_web.py` | Funcional | Validación URL, SSRF, límites |
| **1 Juan** | Investigación / MCP | `src/tools/read_web_page.py` | Funcional | Bloqueo IPs privadas, redirecciones |
| **1 Juan** | Investigación / MCP | `src/tools/competitor_search.py`, `source_discovery.py` | Funcional | Registro de competidores, IDs deterministas |
| **2 Laura** | Análisis / escenarios | `src/analysis/market_analysis.py` | Funcional | `summarize_competitors` (requiere DataFrame) |
| **2 Laura** | Análisis / escenarios | `src/analysis/scenarios.py` | Funcional | Break-even, escenarios de mercado |
| **3 Gema** | Redactor / informes | `src/agents/writer_agent.py` | Funcional | `WriterAgent.create_draft()` (sin LLM por defecto) |
| **3 Gema** | Redactor / informes | `src/agents/writer_llm.py` | Funcional | `run_writing(use_llm=True)` con CrewAI + Groq |
| **3 Gema** | Redactor / informes | `src/reporting/report_builder.py` | Funcional | `build_report`, `find_missing_evidence_ids`, `validate_report_references` |
| **3 Gema** | Redactor / informes | `src/reporting/markdown_renderer.py` | Funcional | `render_report_markdown()` (texto en memoria) |
| **3 Gema** | Redactor / informes | `src/reporting/pdf_renderer.py` | Funcional | `build_pdf_report()` (exportación con autorización) |
| **3 Gema** | Automatización | `src/automation/exporter.py`, `models.py` | Funcional | `ApprovalRecord`, huella del borrador, publicación atómica |
| **4 María** | Revisión / validación | `src/review/validation.py` | Funcional | Validación de referencias existentes |
| **4 María** | Revisión / validación | `src/review/quality_checks.py` | Funcional | Control de calidad de evidencias citadas |
| **4 María** | Revisión / validación | `src/review/models.py` | Funcional | Modelo de revisión |
| **4 María** | Revisión / validación | `tests/test_review_validation.py` | Funcional | Pruebas de validación |
| **4 María** | Revisión / validación | `tests/test_evidence_quality.py`, `test_quality_checks.py` | Funcional | Pruebas de calidad |
| **5 Isabella** | Streamlit / aprobación | `docs/streamlit-approval.md` | **Diseño** | Contrato de UI y aprobación; implementación pendiente |
| **5 Isabella** | Streamlit / aprobación | `docs/langgraph-flow.md` | **Diseño** | Estado, nodos y transiciones; código pendiente |
| **5 Isabella** | Streamlit / aprobación | `src/ui/` | **Pendiente** | Solo `.gitkeep`; sin app Streamlit |

## Estado del flujo completo

| Paso | Persona responsable | Estado |
|---|---|---|
| Investigación (`run_research`) | Juan | ✅ Funcional |
| MCP (`get_area_statistics`) | Juan | ✅ Funcional |
| Análisis descriptivo (`summarize_competitors`) | Laura | ✅ Funcional |
| Redacción determinista (`WriterAgent`) | Gema | ✅ Funcional |
| Redacción con LLM (`run_writing`) | Gema | ✅ Funcional (integrado con `build_report`) |
| Validación referencias (`validate_report_references`) | Gema / María | ✅ Funcional |
| Revisión calidad (`quality_checks`) | María | ✅ Funcional |
| Exportación Markdown (`markdown_renderer`) | Gema | ✅ Funcional |
| Exportación PDF (`pdf_renderer`) | Gema | ✅ Funcional (requiere autorización) |
| Aprobación humana / UI (`ApprovalRecord` → exportación) | Isabella | ⚠️ Pendiente |
| Orquestación completa (`main.py` o CLI) | Isabella / Gema | ❌ No implementado |

## Limitaciones conocidas

- `run_research` usa `max_results=5` por defecto (configurable con `brief.search_limits`).
- `WriterAgent.create_draft()` no conecta automáticamente con `summarize_competitors`; requiere adaptador manual o integración futura.
- El análisis de mercado (`market_analysis`) no consume automáticamente `ResearchResult`.
- La orquestación LLM (`CrewAI`) funciona como ruta separada (`run_writing`), pero la conexión al flujo global (`main.py`) sigue pendiente.
- `coverage_percentage` sigue como `0.0` en `ResearchResult`; no se calcula automáticamente.
- `docs/streamlit-approval.md` y `docs/langgraph-flow.md` documentan el diseño de la Persona 5; la UI y el grafo siguen pendientes.
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
