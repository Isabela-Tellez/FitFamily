# Mapa de módulos e interfaces

Estado descrito: base remota `origin/dev` (`6dbe80e`), 21/10/2026. Este documento no incluye el trabajo del PR #5, que sigue abierto y no fusionado.

## Flujo actual

```text
ResearchBrief
   │
   ▼
run_research() ──────────────► ResearchResult ──────► WriterAgent.create_draft() ──► ReportDraft
   │                              │
   ├── search_web()               └── [falta adaptador] ──► summarize_competitors(DataFrame)
   ├── read_web_page()
   └── competitor_search()

MCP (proceso local)
   python -m src.mcp.server ──► get_area_statistics() ──► _STATISTICS_DATA
   python -m src.mcp.client ──► connect_mcp() / list_mcp_tools() / call_area_statistics()
```

El borrador puede consumir directamente un `ResearchResult`, pero no hay un orquestador que encadene investigación, análisis y salida. El análisis de mercado y la exportación del informe todavía no forman parte de un flujo automático.

## Módulos implementados

| Área | Archivo | Interfaz principal | Estado |
|---|---|---|---|
| Contratos | `src/schemas.py` | `ResearchBrief`, `ResearchResult`, `Evidence`, `Competitor` | Implementado |
| Investigación | `src/agents/researcher.py` | `build_researcher()`, `build_research_task(brief, context=None)`, `run_research(brief, context=None)` | Implementado; sin LLM en ejecución |
| Búsqueda web | `src/tools/search_web.py` | `search_web(query, max_results=10) -> list[SearchResult]` | Implementado; requiere red |
| Lectura web | `src/tools/read_web_page.py` | `read_web_page(url) -> PageReadResult` | Implementado; requiere red |
| Competidores | `src/tools/competitor_search.py` | `competitor_search(params) -> dict` | Implementado; requiere red |
| Servidor MCP | `src/mcp/server.py` | `get_area_statistics(area_id, indicators=None)`, `run_mcp_server()` | Implementado; datos locales |
| Cliente MCP | `src/mcp/client.py` | `connect_mcp()`, `list_mcp_tools(session)`, `call_area_statistics(session, area_id, indicators=None)` | Implementado |
| Análisis | `src/analysis/market_analysis.py` | `summarize_competitors(data: pandas.DataFrame) -> dict` | Implementado; requiere DataFrame |
| Redacción | `src/agents/writer_agent.py` | `WriterAgent.create_draft(brief, research_result) -> ReportDraft` | Implementado; plantilla sin LLM |
| Modelo de informe | `src/reporting/models.py` | `ReportDraft(title, study_area, sections, sources, limitations)` | Implementado; sin exportación |
| Datos offline | `data/raw/extract_households.py` | `python data/raw/extract_households.py [--verify-geometry] [--json PATH]` | Implementado; no es runtime |
| Fuentes | `data/sources.json` | Catálogo de fuentes, períodos y limitaciones | Implementado |
| CI | `.github/workflows/ci.yml` | `compileall` + `pytest` | Añadido en esta rama |

## Contratos e interfaces

### `ResearchBrief` → `ResearchResult`

`run_research(brief, context=None)` valida el brief, ejecuta `search_web` y `competitor_search` y devuelve un `ResearchResult` con:

- `evidences`: evidencias recuperadas.
- `competitors`: competidores identificados.
- `coverage_percentage`: cobertura declarada; en esta base vale `0.0` porque no hay análisis LLM.
- `unresolved_questions`: preguntas pendientes.
- `search_performed` y `notes`: resumen y limitaciones de la ejecución.

En esta base `run_research` usa `max_results=5` de forma fija. El PR #5 propone tomar el valor de `brief.search_limits.max_results`.

### Herramientas web

- `search_web` usa Tavily si existe `TAVILY_API_KEY`; si no, usa DuckDuckGo con `ddgs`. El máximo efectivo es 20 resultados.
- `read_web_page` acepta solo HTTP/HTTPS, valida redirecciones, bloquea destinos privados/locales y limita tamaño y tiempo de respuesta.
- `competitor_search` devuelve un diccionario con `competitors`, `evidences`, `search_summary` y `unresolved_questions`.

### MCP

El servidor publica una única herramienta, `get_area_statistics(area_id, indicators=None)`. En la base `origin/dev` publica 9 indicadores: 6 con valor verificado y 3 con `null` (`families_with_children`, `gyms_registered`, `gyms_with_ludoteca`).

El cliente se usa para comprobar el protocolo:

```bash
python -m src.mcp.client
```

### Análisis y redacción

`summarize_competitors` requiere un `pandas.DataFrame` con estas columnas:

- `gym_name`
- `monthly_price_eur`
- `has_playroom`

Devuelve conteos de competidores, precios conocidos, precio medio mensual y respuestas de ludoteca (`sí`, `no`, desconocidas).

`WriterAgent.create_draft` consume directamente un `ResearchResult` y produce un `ReportDraft` en memoria. No calcula viabilidad financiera, no usa LLM y no escribe archivos.

## Piezas que faltan para el flujo de extremo a extremo

1. **Orquestador/CLI**: no existe `src/main.py` ni un comando que encadene brief → investigación → análisis → borrador → salida.
2. **Adaptador `ResearchResult` → DataFrame**: `summarize_competitors` no puede consumir directamente `ResearchResult.competitors`. Hay que definir cómo obtener `monthly_price_eur` desde `Competitor.tariffs` y `has_playroom` desde evidencias o servicios explícitos, sin inferir datos ausentes.
3. **Exportación del informe**: `ReportDraft` no tiene serializador ni escritura en `reports/`.
4. **Orquestación LLM**: `build_researcher` y `build_research_task` crean objetos CrewAI, pero no hay una `Crew` que ejecute el ciclo completo.
5. **Interfaz de usuario y capas de producto**: `automation`, `graph`, `multimodal`, `review`, `runtime`, `security` y `ui` están vacías.
6. **Persistencia y actualización**: los indicadores del MCP viven en `_STATISTICS_DATA`; no hay base de datos ni programación de actualizaciones.
7. **Pruebas deterministas**: los tests del investigador sustituyen las herramientas web por respuestas controladas en esta rama; el PR #5 añade pruebas de extremo a extremo para el registro de competidores y la búsqueda de fuentes.

## Limitaciones conocidas de la base

- Los IDs de evidencia de `competitor_search` usan `hash(url)` y no son estables entre procesos. El PR #5 propone IDs deterministas con SHA-256.
- `run_research` fija `max_results=5` y no lee `brief.search_limits.max_results`.
- No hay integración automática entre los datos del MCP y `run_research`; son dos rutas separadas.
- No hay CI en `origin/dev`; este documento acompaña al workflow añadido en esta rama.
