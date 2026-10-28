# Calidad, pruebas y CI

Este documento describe qué se prueba hoy en FitFamily, cómo reproducirlo y qué queda fuera de la cobertura. Los resultados corresponden a la revisión documental del **26 de octubre de 2026**; no son una promesa de resultados futuros.

## Qué ejecuta la CI

El workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) se activa con `push` y `pull_request` sobre `dev` y `main`, además de forma manual. El job:

1. Usa Ubuntu y Python 3.13.
2. Instala las dependencias fijadas en `requirements.txt`.
3. Compila `src`, `tests` y `data/raw` con `python -m compileall -q`.
4. Ejecuta `python -m pytest -q`.

No hay pasos de lint, comprobación de tipos, cobertura mínima, validación de enlaces ni pruebas con proveedores reales.

## Resultado de la revisión

Entorno local de la revisión: Windows, Python 3.13.12.

| Comprobación | Resultado |
|---|---|
| `python -m pytest -q` | **273 passed**, 36 warnings, exit code 0 |
| `python -m compileall -q src tests data/raw` | exit code 0 |
| `python -m src.mcp.client` | conexión local por `stdio`, 1 herramienta, 2 indicadores consultados, exit code 0 |
| Demo determinista registro → análisis → borrador → revisión → exportación | Markdown y PDF generados en un directorio temporal, exit code 0 |

Las 36 advertencias son avisos de deprecación emitidos por CrewAI (`function_calling_llm`, `allow_code_execution` y `reasoning`). No hubo fallos ni errores de colección.

## Mapa de pruebas

La suite contiene **28 archivos** y **273 casos**. La agrupación siguiente es orientativa:

| Área | Archivos | Casos |
|---|---:|---:|
| Datos municipales y MCP | 5 | 49 |
| Investigación, web, fuentes y registro | 9 | 130 |
| Análisis de mercado y escenarios | 2 | 12 |
| Redacción, informes, exportación y flujo entre módulos | 8 | 50 |
| Revisión y rutas de corrección | 4 | 32 |
| **Total** | **28** | **273** |

Archivos incluidos:

- Datos y MCP: `test_area_indicators.py`, `test_mcp.py`, `test_mcp_integration.py`, `test_locales.py`, `test_households.py`.
- Investigación: `test_researcher.py`, `test_competitor_search.py`, `test_competitor_registry.py`, `test_source_discovery.py`, `test_web_tools.py`, `test_evidence_ids.py`, `test_extract_registry_cache.py`, `test_search_limits.py`, `test_registry_artifact.py`.
- Análisis: `test_market_analysis.py`, `test_scenarios.py`.
- Informes: `test_report_draft.py`, `test_report_builder.py`, `test_markdown_renderer.py`, `test_exporter.py`, `test_pdf_exporter.py`, `test_writer_agent.py`, `test_strategic_writer.py`, `test_cross_module_integration.py`.
- Revisión: `test_evidence_quality.py`, `test_quality_checks.py`, `test_review_routes.py`, `test_review_validation.py`.

## Qué cubre la suite

- Validación de los contratos Pydantic y de los modelos de informe.
- Investigación con respuestas web simuladas: búsqueda, lectura, competidores, descubrimiento de fuentes, límites y errores controlados.
- Protecciones SSRF de `read_web_page`, incluidos redirecciones, direcciones privadas y IPv4 mapeado en IPv6.
- Parseo y actualización de los indicadores municipales, incluyendo errores que no deben sobrescribir el almacén.
- MCP real por `stdio` en un subproceso local.
- Análisis descriptivo, normalización de ludoteca y punto de equilibrio.
- Redactor determinista y redactor LLM con respuestas simuladas.
- Construcción de borradores, referencias, renderizado Markdown, PDF y exportación con aprobación.
- Revisión estructural, huella del borrador y rutas de corrección.
- Integración registro versionado → `DataFrame` → análisis → redactor.

## Qué no cubre

- Una búsqueda o lectura real de Internet: las pruebas de herramientas usan respuestas controladas.
- Una llamada real a Groq/CrewAI: la ruta LLM se prueba con mocks.
- Una interfaz Streamlit, el grafo LangGraph o un orquestador global: el workflow (`workflows.py`) y la persistencia (`persistence.py`) están implementados (PR #30); falta el controlador global y la aplicación web.
- La verificación semántica de que una fuente respalde realmente una afirmación.
- El cálculo real de `coverage_percentage`: el campo permanece en `0.0`.
- Rendimiento, concurrencia, autenticación, autorización, despliegue o recuperación ante fallos.
- Una revisión visual automatizada del PDF: se comprueban estructura y bytes, no tipografía o composición.
- Validación de enlaces y de diagramas Mermaid dentro de la CI.

## Cómo reproducir

Desde la raíz del repositorio:

```bash
python -m pip install -r requirements.txt
python -m compileall -q src tests data/raw
python -m pytest -q
```

Pruebas de una parte concreta:

```bash
python -m pytest tests/test_mcp_integration.py -q
python -m pytest tests/test_exporter.py tests/test_pdf_exporter.py -q
python -m pytest tests/test_review_validation.py tests/test_review_routes.py -q
```

El archivo `pyproject.toml` declara `testpaths = ["tests"]` y `pythonpath = ["."]`; por eso los comandos funcionan desde la raíz sin instalar el proyecto como paquete.

## Límites de la propia CI

La CI actual es una red de seguridad útil, no una garantía de producto terminado:

- Solo ejecuta una combinación de sistema operativo y versión de Python (Ubuntu + 3.13).
- No exige un umbral de cobertura ni publica un informe de cobertura.
- No comprueba tipos, estilo ni enlaces.
- No ejecuta la interfaz ni el flujo completo con aprobación humana.
- No detecta cambios en proveedores externos porque no los llama de verdad.

Cualquier afirmación sobre “flujo completo” debe entenderse como composición de APIs probadas por separado, no como una aplicación integrada de extremo a extremo.
