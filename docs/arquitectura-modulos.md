# Mapa de módulos e interfaces

> Revisión documental: **26 de octubre de 2026**. Este documento describe lo que existe en el código, no un flujo ideal. FitFamily es hoy una colección de módulos con contratos comunes; **no hay un `main.py` ni una aplicación que ejecute todo el recorrido de una sola vez**.

## 1. Vista general

```text
Entrada
  ResearchBrief
      │
      ▼
Investigación (Juan)
  run_research(brief, context=None)
      ├── search_web()
      ├── read_web_page()
      ├── competitor_search()
      ├── discover_sources()
      └── registro de competidores sobre datos oficiales
      │
      ▼
  ResearchResult
      ├── Evidence[]
      ├── Competitor[]
      ├── coverage_percentage = 0.0
      └── unresolved_questions[]
      │
      ├──────────────────────────────┐
      ▼                              ▼
Análisis (Laura)                Redacción (Gema)
  ResearchResult                  WriterAgent.create_draft()
      │ adaptador pendiente            o run_writing()
      ▼                              │
  DataFrame ──► summarize_competitors│
                 calculate_break_even│
                                     ▼
                                ReportDraft
                                     │
                                     ▼
                              Revisión (María)
                                run_basic_review()
                                choose_review_route()
                                     │
                                     ▼
                              Decisión humana
                              ApprovalRecord
                                     │
                                     ▼
                              Exportación (Gema)
                              export_markdown()
                              export_pdf()
```

La interfaz Streamlit y el grafo LangGraph de Isabella están **diseñados en documentación, no implementados**. Por eso no aparecen como una caja ejecutable en la vista anterior.

## 2. Componentes implementados

| Componente | Ruta | Entrada pública | Salida | Estado real |
|---|---|---|---|---|
| Contratos compartidos | `src/schemas.py` | `ResearchBrief`, `Evidence`, `Competitor`, `ResearchResult` | Modelos Pydantic | Implementado |
| Investigación | `src/agents/researcher.py` | `run_research(brief, context=None)` | `ResearchResult` | Implementado con herramientas directas; no ejecuta un `Crew` |
| Búsqueda web | `src/tools/search_web.py` | `search_web(query, max_results)` | Resultados estructurados | Requiere red; Tavily o DuckDuckGo |
| Lectura web | `src/tools/read_web_page.py` | `read_web_page(url)` | Texto y metadatos | Implementado con protecciones SSRF |
| Búsqueda de competidores | `src/tools/competitor_search.py` | `competitor_search(params)` | Competidores y evidencias | Implementado; puede requerir red |
| Descubrimiento de fuentes | `src/tools/source_discovery.py` | `discover_sources(variable, area, ...)` | Candidatos con estado | Implementado |
| Registro oficial | `src/tools/competitor_registry.py` | `build_competitor_registry(...)`, `to_dataframe(...)` | Competidores oficiales y `DataFrame` | Implementado; artefacto versionado |
| Datos municipales/MCP | `src/mcp/server.py`, `src/mcp/client.py` | `get_area_statistics(area_id, indicators=None)` | 13 indicadores documentados | Servidor local por `stdio`; 11 verificados y 2 no disponibles |
| Análisis descriptivo | `src/analysis/market_analysis.py` | `summarize_competitors(data)` | Diccionario de indicadores | Implementado; no consume `ResearchResult` automáticamente |
| Escenarios | `src/analysis/scenarios.py` | `calculate_break_even_clients(...)` | Clientes mínimos | Implementado con supuestos del usuario |
| Redactor determinista | `src/agents/writer_agent.py` | `WriterAgent().create_draft(brief, result)` | `ReportDraft` | Implementado; no calcula viabilidad financiera |
| Redactor LLM | `src/agents/strategic_writer.py` | `run_writing(brief, result)` | `ReportDraft` | Implementado; requiere Groq y no se ejecutó con un proveedor real en esta revisión |
| Constructor de informes | `src/reporting/report_builder.py` | `build_report(...)`, `build_report_markdown(...)` | `ReportDraft`/Markdown | Implementado; valida referencias existentes |
| Renderizadores | `src/reporting/markdown_renderer.py`, `pdf_renderer.py` | `render_report_markdown(draft)`, `render_report_pdf(draft)` | Texto/bytes en memoria | Implementado; no validan aprobación |
| Revisión | `src/review/` | `run_basic_review(draft, result)` | `ReviewResult` | Implementado; solo comprobaciones estructurales |
| Rutas de revisión | `src/graph/review_routes.py` | `choose_review_route(review, count, max_revisions=2)` | Ruta de corrección | Implementado; no ejecuta agentes |
| Aprobación y exportación | `src/automation/` | `ApprovalRecord`, `export_markdown`, `export_pdf` | Archivos publicados | Implementado a nivel de API; el controlador humano no existe |

## 3. Flujo real, paso a paso

No hay una función única que enlace todos los pasos. Una persona o un futuro controlador debe llamar a los módulos en este orden:

1. Construir un `ResearchBrief`.
2. Llamar a `run_research(brief)` si se quiere investigación web, o cargar el artefacto `data/processed/competitor_registry.json` si se parte del registro oficial.
3. Si se usa el registro, convertirlo con `to_dataframe(competitors)` y llamar a `summarize_competitors(frame)`; esta unión no es automática desde `ResearchResult`.
4. Construir el borrador con `build_report(brief, research_result)` o `build_report(..., use_llm=True)`.
5. Revisar con `run_basic_review(draft, research_result)` y decidir la ruta con `choose_review_route(...)`.
6. Mostrar el borrador a una persona y crear un `ApprovalRecord` solo después de su decisión.
7. Exportar con `export_markdown(...)` o `export_pdf(...)`.

La aprobación es un objeto de datos, no una prueba criptográfica de que una persona haya pulsado un botón. El controlador que lo cree debe garantizar que la decisión existió de verdad.

## 4. Contratos compartidos

| Contrato | Campos principales | Lo produce | Lo consumen |
|---|---|---|---|
| `ResearchBrief` | `business_type`, `location`, `study_area`, `questions`, `search_limits`, `missing_variables`, `assumed`, `assumed_params` | Persona usuaria o futuro controlador | Investigación |
| `Evidence` | `evidence_id`, `claim`, `value`, `unit`, `frequency`, `source_url`, `snippet`, `date_observed`, `geo_scope`, `limitations` | Herramientas de investigación | Redacción y revisión |
| `Competitor` | `identifier`, `name`, `location`, `services`, `tariffs`, `evidences`, coordenadas, sección censal, licencia, `has_playroom` | Registro o búsqueda de competidores | Análisis y redacción |
| `ResearchResult` | `evidences`, `competitors`, `coverage_percentage`, `unresolved_questions`, `search_performed`, `notes` | `run_research` | Análisis, redacción y revisión |
| `ReportDraft` | `title`, `study_area`, `sections`, `sources`, `limitations`, `draft_id`, `version`, `claims` | Redactor | Revisión, renderizado y exportación |
| `ReviewResult` | `draft_id`, `draft_version`, `draft_fingerprint`, `issues`, `checks_performed` | Revisión | Controlador/futuro grafo |
| `ApprovalRecord` | `run_id`, `draft_id`, `draft_version`, `draft_fingerprint`, `approved`, `actions`, `decided_at` | Controlador con decisión humana | Exportador |

### Invariantes

- `null` o una lista vacía significan **no disponible**, nunca cero ni una invención.
- `Evidence.claim` no puede estar vacío.
- `ResearchResult.evidences` ya debe incluir las evidencias de cada competidor; quien itere ambas listas debe deduplicar.
- `coverage_percentage` existe en el contrato, pero `run_research` lo deja en `0.0`; no hay cálculo de cobertura.
- `ReportDraft` recibe un `draft_id` nuevo y `version=1`; el incremento de versión es responsabilidad del proceso que modifica el contenido.
- `ReviewResult` no concede aprobación. `pending_review` solo significa que no hay errores estructurales.
- `ApprovalRecord.decided_at` debe ser una fecha con zona horaria.

## 5. Roles humanos frente a componentes

Las cinco personas son **roles de desarrollo**, no agentes que se ejecuten en runtime:

| Persona | Responsabilidad | Documento |
|---|---|---|
| Juan | Investigación, herramientas, datos y MCP | [research-module.md](research-module.md) |
| Laura | Análisis descriptivo y escenarios | [analysis.md](analysis.md) |
| Gema | Redacción, informes y exportación | [report-export.md](report-export.md), [writer-llm.md](writer-llm.md) |
| María | Revisión y rutas de calidad | [review-quality.md](review-quality.md) |
| Isabella | Interfaz, orquestación y aprobación | [streamlit-approval.md](streamlit-approval.md), [langgraph-flow.md](langgraph-flow.md) |

El componente `src/agents/researcher.py` es código, no la persona Juan. Del mismo modo, `WriterAgent` es un componente y no Gema. La única ruta que ejecuta un `Crew` de CrewAI es el redactor LLM; el investigador construye objetos `Agent`/`Task` pero usa las herramientas directamente.

## 6. Fronteras y piezas pendientes

### Implementado y conectado por API

- Investigación → `ResearchResult`.
- Registro oficial → `DataFrame` → análisis descriptivo.
- `ResearchResult` → redactor → `ReportDraft`.
- `ReportDraft` → revisión estructural.
- `ReportDraft` + `ApprovalRecord` → exportación Markdown/PDF.

### Implementado, pero sin integración automática

- `ResearchResult` → análisis: falta un adaptador explícito a `DataFrame`.
- MCP → investigación: la consulta de indicadores es una herramienta local separada; no alimenta `run_research`.
- Análisis → redactor: el análisis no forma parte del `ReportDraft` actual.
- Revisión → corrección: `choose_review_route` devuelve una ruta, pero no ejecuta la corrección.
- `coverage_percentage`: campo reservado, siempre `0.0`.

### Diseñado, no implementado

- `src/ui/`: solo `.gitkeep`; no hay Streamlit.
- `src/runtime/`: solo `.gitkeep`; no hay grafo ni controlador.
- `src/security/`, `src/multimodal/`: carpetas reservadas, sin módulos.
- No hay `main.py`, CLI ni servidor de aplicación.
- `update_tracking_csv` está reconocida como acción permitida, pero no existe una función que la implemente.
- No hay actualización programada de datos, base de datos, autenticación, autorización ni trazas de auditoría.

### Datos

- El almacén MCP es un snapshot documentado en `src/mcp/server.py`; las funciones `refresh_*` descargan y actualizan bajo demanda.
- El registro versionado de competidores es una foto de `data/processed/`; no se refresca en cada ejecución.
- La variable de renta está documentada en [pendiente-renta-ine.md](pendiente-renta-ine.md) y no se ha imputado.

## 7. Dónde ampliar sin romper contratos

- Para añadir una fuente, extender las herramientas y `Evidence`; no rellenar `null` con estimaciones.
- Para conectar análisis, crear un adaptador explícito `ResearchResult → DataFrame`; no duplicar la lógica de `summarize_competitors`.
- Para añadir UI, construir el `ApprovalRecord` después de la decisión y reutilizar `export_markdown`/`export_pdf`.
- Para añadir orquestación, conservar el `ReportDraft` aprobado; no regenerarlo después de la aprobación.
- Para cambiar un contrato compartido, actualizar este documento y los tests en el mismo cambio.

## 8. Documentación relacionada

- [README](../README.md) · [English README](../README.en.md)
- [Equipo y responsabilidades](equipo.md)
- [Módulo de investigación](research-module.md)
- [Análisis](analysis.md)
- [Exportación de informes](report-export.md)
- [Redactor con LLM](writer-llm.md)
- [Revisión y calidad](review-quality.md)
- [Calidad, pruebas y CI](calidad-pruebas.md)
- [Streamlit y aprobación](streamlit-approval.md)
- [Flujo LangGraph](langgraph-flow.md)
- [Auditoría de fuentes](auditoria-fuentes-datos.md)
- [Renta pendiente](pendiente-renta-ine.md)
- [Datos locales](../data/raw/README.md)
