# Equipo y responsabilidades

FitFamily se construye entre cinco personas con responsabilidades separadas y contratos explícitos. Este documento registra qué aporta cada integrante, qué módulos mantiene y dónde está la documentación.

> **Roles humanos, no agentes.** Las cinco personas son roles de desarrollo. Los nombres `ResearchAgent`, `WriterAgent`, `ReviewResult` o `ApprovalRecord` designan componentes de software, no personas. La única ruta que ejecuta un `Crew` de CrewAI es el redactor LLM; el investigador usa las herramientas directamente.

## Resumen

| Persona | Rol | Módulos principales | Documentación |
|---|---|---|---|
| **1 · Juan** | Investigación, fuentes y MCP | `src/schemas.py`, `src/agents/researcher.py`, `src/tools/`, `src/mcp/`, `data/raw/` | [research-module.md](research-module.md) |
| **2 · Laura** | Análisis de mercado y escenarios | `src/analysis/` | [analysis.md](analysis.md) |
| **3 · Gema** | Redacción, informes y exportación | `src/agents/writer_agent.py`, `src/agents/strategic_writer.py`, `src/agents/writer_llm.py`, `src/reporting/`, `src/automation/` | [report-export.md](report-export.md) · [writer-llm.md](writer-llm.md) |
| **4 · María** | Revisión, validación y rutas de calidad | `src/review/`, `src/graph/review_routes.py` | [review-quality.md](review-quality.md) |
| **5 · Isabella** | Interfaz, orquestación y aprobación humana | `src/ui/` (vacío), `src/runtime/` (vacío), diseño de Streamlit/LangGraph | [streamlit-approval.md](streamlit-approval.md) · [langgraph-flow.md](langgraph-flow.md) |

## Persona 1 — Juan: investigación, datos y MCP

<a id="persona-1"></a>

**Responsabilidad.** Convertir un `ResearchBrief` en un `ResearchResult` trazable, con evidencias identificables, competidores y fuentes descubiertas. Mantiene también el servidor MCP que publica los indicadores municipales.

**Entregables principales.**

- `src/schemas.py`: contratos compartidos (`ResearchBrief`, `ResearchResult`, `Evidence`, `Competitor`).
- `src/agents/researcher.py`: `run_research(brief, context=None)`, `build_researcher`, `build_research_task`.
- `src/tools/`: búsqueda web, lectura de páginas, búsqueda de competidores, descubrimiento de fuentes y registro oficial.
- `src/mcp/`: servidor y cliente MCP; `get_area_statistics(area_id, indicators=None)`.
- `data/raw/`: scripts de preparación de datos y documentación de fuentes.
- `.github/workflows/ci.yml` y pruebas deterministas del investigador.

**Interfaces que consume.** Un `ResearchBrief` y fuentes municipales o web.

**Interfaces que produce.** `ResearchResult` con `evidences`, `competitors`, `unresolved_questions`, `coverage_percentage` y `search_performed`.

**Estado real.** La investigación web requiere red y puede devolver un resultado parcial si falla un proveedor. El MCP funciona en local por `stdio`. `run_research` no ejecuta un LLM ni un `Crew`; la cobertura permanece en `0.0`.

**Documentación.** [research-module.md](research-module.md), [auditoria-fuentes-datos.md](auditoria-fuentes-datos.md), [data/raw/README.md](../data/raw/README.md). Los documentos [research-implementation.md](research-implementation.md) y [research-changelog.md](research-changelog.md) son históricos.

## Persona 2 — Laura: análisis y escenarios

<a id="persona-2"></a>

**Responsabilidad.** Convertir datos de competidores en indicadores descriptivos y calcular escenarios de punto de equilibrio con supuestos explícitos.

**Entregables principales.**

- `src/analysis/market_analysis.py`: `normalize_playroom_value`, `summarize_competitors`.
- `src/analysis/scenarios.py`: `calculate_break_even_clients`.
- `tests/test_market_analysis.py`, `tests/test_scenarios.py`.

**Interfaces que consume.** Un `DataFrame` con las columnas obligatorias `gym_name`, `monthly_price_eur` y `has_playroom`. El registro versionado puede convertirse con `src.tools.competitor_registry.to_dataframe`.

**Interfaces que produce.** Un diccionario de indicadores (`competitor_count`, precios conocidos, media de precios y estado de ludoteca) y un entero de clientes mínimos para el punto de equilibrio.

**Estado real.** El análisis descriptivo y el punto de equilibrio están implementados. La conexión automática desde un `ResearchResult` a `DataFrame` sigue pendiente; hoy requiere un adaptador explícito o partir del registro versionado.

**Documentación.** [analysis.md](analysis.md).

## Persona 3 — Gema: redacción, informes y exportación

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

**Estado real.** La ruta determinista es la predeterminada. La ruta LLM se activa con `build_report(..., use_llm=True)` y requiere `GROQ_API_KEY`; no se ejecutó con un proveedor real en la revisión documental. La exportación exige un `ApprovalRecord` válido, pero la interfaz que lo crea no existe.

**Documentación.** [report-export.md](report-export.md), [writer-llm.md](writer-llm.md).

## Persona 4 — María: revisión, validación y rutas de calidad

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

**Estado real.** La revisión estructural está implementada. No verifica que una fuente respalde semánticamente una afirmación, no consulta Internet y no ejecuta correcciones. No aprueba ni exporta.

**Documentación.** [review-quality.md](review-quality.md).

## Persona 5 — Isabella: interfaz, orquestación y aprobación

<a id="persona-5"></a>

**Responsabilidad.** Unir el flujo completo en una interfaz y una orquestación con aprobación humana: mostrar investigación, análisis, borrador y revisión; recoger la decisión; y autorizar la exportación.

**Entregables previstos.**

- `src/ui/`: aplicación Streamlit (hoy solo existe `.gitkeep`).
- `src/runtime/`: orquestación y estado compartido (hoy solo existe `.gitkeep`).
- Flujo de aprobación que construye un `ApprovalRecord` válido y llama al exportador de Gema.
- Pruebas de la interfaz y del flujo de aprobación.

**Interfaces que consume.** `ResearchResult`, `ReportDraft`, `ReviewResult` y `ApprovalRecord`.

**Interfaces que produce.** Decisión humana registrada y archivo Markdown/PDF publicado.

**Estado real.** Diseño documentado; implementación pendiente. No hay código de UI, dependencias de Streamlit/LangGraph en `requirements.txt`, ni orquestador global. El controlador que cree `ApprovalRecord` debe garantizar que la decisión humana existió.

**Documentación.** [streamlit-approval.md](streamlit-approval.md), [langgraph-flow.md](langgraph-flow.md).

## Contratos compartidos

| Contrato | Lo produce | Lo consumen |
|---|---|---|
| `ResearchResult` | Investigación | Análisis, redacción y revisión |
| `DataFrame` de competidores | Registro oficial o adaptador explícito | Análisis |
| `ReportDraft` | Redacción | Revisión y controlador |
| `ReviewResult` | Revisión | Controlador/futuro grafo |
| `ApprovalRecord` | Controlador con decisión humana | Exportación |
| Markdown / PDF | Exportación | Persona usuaria |

## Regla de documentación

Cada integrante mantiene el documento de su rol. Si un cambio afecta a un contrato compartido, se actualizan el documento del rol y [arquitectura-modulos.md](arquitectura-modulos.md) en el mismo cambio. Ningún rol se considera “secundario”: la documentación debe reflejar las cinco responsabilidades por igual.
