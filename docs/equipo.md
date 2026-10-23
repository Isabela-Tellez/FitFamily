# Equipo y responsabilidades

FitFamily se construye entre cinco personas con responsabilidades separadas y contratos explícitos. Este documento registra a cada integrante por igual: qué aporta, qué módulos mantiene, en qué estado está su trabajo y dónde está su documentación.

| Persona | Rol | Módulos principales | Documento | Estado |
|---|---|---|---|---|
| **1 · Juan** | Investigación, fuentes y MCP | `src/agents/researcher.py`, `src/tools/`, `src/mcp/`, `data/raw/` | [research-module.md](research-module.md) | ✅ Funcional |
| **2 · Laura** | Análisis de mercado y escenarios | `src/analysis/market_analysis.py`, `src/analysis/scenarios.py` | [analysis.md](analysis.md) | ✅ Funcional |
| **3 · Gema** | Redacción, informes y automatización | `src/agents/writer_agent.py`, `src/agents/strategic_writer.py`, `src/agents/writer_llm.py`, `src/reporting/`, `src/automation/` | [report-export.md](report-export.md) · [writer-llm.md](writer-llm.md) | ✅ Funcional |
| **4 · María** | Revisión, validación y seguridad | `src/review/`, `src/graph/review_routes.py` | [review-quality.md](review-quality.md) | ✅ Funcional |
| **5 · Isabella** | Streamlit, LangGraph y aprobación humana | `src/ui/` (pendiente), orquestación global | [streamlit-approval.md](streamlit-approval.md) · [langgraph-flow.md](langgraph-flow.md) | ⚠️ Diseño / pendiente |

## Persona 1 — Juan: investigación y datos

<a id="persona-1"></a>

**Responsabilidad.** Convertir un `ResearchBrief` en un `ResearchResult` trazable, con evidencias identificables, competidores y fuentes descubiertas. También mantiene el servidor MCP que publica los indicadores municipales.

**Entregables principales.**

- `src/agents/researcher.py`: `run_research(brief)`, `build_researcher`, `build_research_task`.
- `src/tools/`: búsqueda web, lectura de páginas, búsqueda de competidores y descubrimiento de fuentes.
- `src/mcp/`: servidor y cliente MCP (`get_area_statistics`).
- `data/raw/`: scripts de preparación del registro de competidores y fuentes documentadas.
- `.github/workflows/ci.yml` y pruebas deterministas del investigador.

**Interfaces que consume.** Un `ResearchBrief` definido por la persona usuaria o la UI, y las fuentes municipales y web.

**Interfaces que produce.** `ResearchBrief` → `ResearchResult` (`evidences`, `competitors`, `unresolved_questions`, `coverage_percentage`).

**Estado.** Funcional. La investigación web requiere red; el MCP funciona en local por `stdio`.

**Documentación.** [research-module.md](research-module.md), [research-implementation.md](research-implementation.md), [auditoria-fuentes-datos.md](auditoria-fuentes-datos.md), [research-changelog.md](research-changelog.md).

## Persona 2 — Laura: análisis y escenarios

<a id="persona-2"></a>

**Responsabilidad.** Convertir los datos de competidores en indicadores descriptivos y calcular escenarios de punto de equilibrio con supuestos explícitos.

**Entregables principales.**

- `src/analysis/market_analysis.py`: `normalize_playroom_value`, `summarize_competitors`.
- `src/analysis/scenarios.py`: `calculate_break_even_clients`.
- `tests/test_market_analysis.py`, `tests/test_scenarios.py`.

**Interfaces que consume.** Un `DataFrame` con `gym_name`, `monthly_price_eur` y `has_playroom`.

**Interfaces que produce.** Un diccionario de indicadores (`competitor_count`, precios, ludoteca) y un entero de clientes mínimos para el punto de equilibrio.

**Estado.** Funcional. La conexión automática desde `ResearchResult` a `DataFrame` sigue pendiente y hoy requiere un adaptador explícito.

**Documentación.** [analysis.md](analysis.md).

## Persona 3 — Gema: redacción, informes y automatización

<a id="persona-3"></a>

**Responsabilidad.** Generar el borrador del informe a partir de la investigación, validar sus referencias y publicarlo en Markdown o PDF solo después de una aprobación humana válida.

**Entregables principales.**

- `src/agents/writer_agent.py`: `WriterAgent.create_draft`.
- `src/agents/strategic_writer.py`: `run_writing`.
- `src/agents/writer_llm.py`: integración con CrewAI + Groq.
- `src/reporting/`: `ReportDraft`, `build_report`, `build_report_markdown`, renderizadores Markdown y PDF.
- `src/automation/`: `ApprovalRecord`, `validate_export_approval`, `export_markdown`, `export_pdf`.

**Interfaces que consume.** `ResearchBrief` + `ResearchResult`.

**Interfaces que produce.** `ReportDraft` (con `draft_id`, `version`, `claims`) y archivos Markdown/PDF aprobados.

**Estado.** Funcional. La ruta determinista es la predeterminada; la ruta LLM se activa con `use_llm=True` y requiere `GROQ_API_KEY`.

**Documentación.** [report-export.md](report-export.md), [writer-llm.md](writer-llm.md).

## Persona 4 — María: revisión, validación y seguridad

<a id="persona-4"></a>

**Responsabilidad.** Revisar el borrador antes de la aprobación: referencias inexistentes, hechos sin evidencia, evidencias sin fuente, accesos fallidos usados como prueba, fuentes descartadas y duplicados. También decide a qué etapa devolver cada corrección.

**Entregables principales.**

- `src/review/validation.py`: `validate_claim_references`, `validate_evidence_quality`.
- `src/review/quality_checks.py`: `run_basic_review`.
- `src/review/models.py`: `ReviewIssue`, `ReviewResult`.
- `src/graph/review_routes.py`: `choose_review_route`.
- Pruebas: `test_review_validation.py`, `test_evidence_quality.py`, `test_quality_checks.py`, `test_review_routes.py`.

**Interfaces que consume.** `ReportDraft` + `ResearchResult`.

**Interfaces que produce.** `ReviewResult` con incidencias, huella del borrador y estado (`needs_revision` o `pending_review`).

**Estado.** Funcional. No aprueba ni exporta: solo emite el diagnóstico y la ruta de corrección.

**Documentación.** [review-quality.md](review-quality.md).

## Persona 5 — Isabella: Streamlit, LangGraph y aprobación humana

<a id="persona-5"></a>

**Responsabilidad.** Unir el flujo completo en una interfaz y una orquestación con aprobación humana: mostrar investigación, análisis, borrador y revisión; recoger la decisión de la persona usuaria; y autorizar la exportación.

**Entregables previstos.**

- `src/ui/`: aplicación Streamlit (hoy solo existe `.gitkeep`).
- Orquestación LangGraph con estado compartido y bucle de correcciones.
- Flujo de aprobación que construye un `ApprovalRecord` válido y llama al exportador de Gema.
- Pruebas de la interfaz y del flujo de aprobación.

**Interfaces que consume.** `ResearchResult`, `ReportDraft`, `ReviewResult` y `ApprovalRecord`.

**Interfaces que produce.** Decisión humana registrada y archivo Markdown/PDF publicado.

**Estado.** Diseño documentado; implementación pendiente. No hay código de UI ni dependencias de Streamlit/LangGraph en `requirements.txt`.

**Documentación.** [streamlit-approval.md](streamlit-approval.md), [langgraph-flow.md](langgraph-flow.md).

## Contratos compartidos

| Contrato | Lo produce | Lo consumen |
|---|---|---|
| `ResearchResult` | Juan | Laura, Gema |
| `DataFrame` de competidores | Adaptador pendiente (Juan/Laura) | Laura |
| `ReportDraft` | Gema | María, Isabella |
| `ReviewResult` | María | Isabella |
| `ApprovalRecord` | Isabella (decisión humana) | Gema (exportación) |
| Markdown / PDF | Gema | Isabella (UI), persona usuaria |

## Regla de documentación

Cada integrante mantiene el documento de su rol. Si un cambio afecta a un contrato compartido, se actualizan el documento del rol y [arquitectura-modulos.md](arquitectura-modulos.md) en el mismo pull request. Ningún rol se considera "secundario": la documentación debe reflejar las cinco responsabilidades por igual.
