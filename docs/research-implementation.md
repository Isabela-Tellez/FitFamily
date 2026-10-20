# FitFamily - Registro de Cambios del Módulo Persona 1

## Visión General
Este documento registra todas las modificaciones y creación de archivos durante la implementación del módulo de Investigación y MCP para la Persona 1 (Juan) en el proyecto FitFamily.

---

## Fase 1 — Inspección del Repositorio (19/10/2026)

### Estado Inicial
- Repositorio clonado en `C:\Users\JUAN\Desktop\Proyectos\FitFamily`
- Rama `main` con commit inicial (`76c60e8`): `.gitignore`, `LICENSE`, `README.md`
- Remotes: `origin/main`, `origin/dev` (rama dev existe pero está vacía)
- Entorno Python: Python 3.13.12 con paquetes: `pydantic`, `mcp`, `crewai` (v1.15.28), `ddgs` (v9.14.4), `tavily-python` (v0.8.5), `httpx`, `beautifulsoup4`, `pytest`

### Hallazgos
- No había código Python previo en el repositorio (solo archivos de configuración)
- El directorio `src/` existía vacío
- No había modelos, herramientas ni scripts definidos
- Se debía crear todo el módulo desde cero respetando las rutas establecidas

---

## Fase 2 — Modelos Pydantic (src/schemas.py)

### 19/10/2026 - Creación Inicial
- **Archivo creado**: `src/schemas.py`
- **Contenido**: Modelos `Evidence`, `Competitor`, `ResearchBrief`, `ResearchResult`
- **Validaciones añadidas**:
  - `Evidence` requiere `claim` no vacío
  - `Competitor` normaliza `services` y `tariffs`
  - `ResearchBrief` normaliza espacios y filtra preguntas vacías
  - `ResearchResult` asegura `coverage_percentage` en [0,100] y `unresolved_questions` como lista

### 20/10/2026 - Ajustes
- Refinamiento de validadores con `@model_validator(mode="after")` en lugar de deprecated `@root_validator`
- Corrección de importaciones y tipos

---

## Fase 3 — Herramientas Web (src/tools/)

### `search_web.py` (19/10/2026)
- **Creado**: `src/tools/search_web.py`
- **Función**: `search_web(query, max_results) → List[SearchResult]`
- **Detalles**:
  - Validación de entrada (query no vacía, max_results 1-20)
  - Usa `duckduckgo-search` (DDGS) sin API key
  - Manejo de timeouts (30s por defecto)
  - Advertencias y errores estructurados
  - Clase `SearchResult` con `title`, `url`, `snippet`, `provider`, `retrieved_at`

### `read_web_page.py` (19/10/2026)
- **Creado**: `src/tools/read_web_page.py`
- **Función**: `read_web_page(url) → PageReadResult`
- **Características**:
  - Valida esquema http/https
  - Bloquea IPs privadas (127.x, 10.x, 192.168.x, 172.16.x-31.x)
  - Usa `httpx` con timeout de 30s
  - `BeautifulSoup` para sanitización HTML (elimina scripts/style)
  - Extrae título, cuerpo de texto, fragmento de apoyo
  - Timeouts, límites de tamaño (5MB max)
  - **No ejecuta scripts** ni código de páginas
  - **No elude autenticaciones** ni bloqueos

### `competitor_search.py` (20/10/2026)
- **Creado**: `src/tools/competitor_search.py`
- **Función**: `competitor_search(params) → Dict[str, Any]`
- **Clase**: `CompetitorSearchInput` con validación Pydantic
- **Características**:
  - Valida `area` y `business_type` no vacíos
  - Construye consultas automáticas o usa las personalizadas
  - Deduplicación por URL normalizada, dominio, nombre, ubicación
  - Extrae evidencias con `Evidence` schema
  - Normaliza `services` (lista limpia) y `tariffs` (formato estandarizado)
  - Detecta precio ausente vs. inaccesible vs. encontrado
  - **No inventa** competidores, direcciones, precios, servicios

---

## Fase 4 — Agente CrewAI (src/agents/researcher.py)

### 20/10/2026 - Creación
- **Archivo**: `src/agents/researcher.py`
- **Funciones públicas**:
  - `build_researcher()` → `Agent` con rol/objetivo/*backstory*/herramientas
  - `build_research_task(brief, context)` → `Task` describiendo la investigación
  - `run_research(brief, context)` → `ResearchResult` (contrato público)

### Detalles de Implementación
- El agente usa herramientas registradas, no responde solo por LLM
- `run_research()` crea su propio `Crew`/`Task` internamente para evitar validaciones de `Agent.tools`
- Validación de `brief` al inicio (TypeError/ValueError para entradas inválidas)
- Manejo de errores: devuelve `ResearchResult` estructurado en lugar de éxito ficticio
- Sin clave LLM requerida para ejecución básica (usa herramientas directamente)

---

## Fase 5 — MCP Servidor y Cliente (src/mcp/)

### `server.py` (20/10/2026)
- **Archivo**: `src/mcp/server.py`
- **Función pública**: `get_area_statistics(area_id, indicators)`
- **Almacenamiento**: Diccionario `_STATISTICS_DATA` con indicadores reales y `null` documentados
- **Endpoint MCP**:
  - Nombre: `get_area_statistics`
  - Parámetro obligatorio: `area_id`
  - Parámetro opcional: `indicators` (lista de strings)
  - `list_tools()` devuelve objetos `mcp.types.Tool` con `inputSchema` (requisito del SDK)
  - `call_tool()` valida el nombre y devuelve un dict estructurado

### `client.py` (20/10/2026, corregido 20/10/2026)
- **Archivo**: `src/mcp/client.py`
- **Funciones**:
  - `mcp_server_params()` → lanza `sys.executable -m src.mcp.server` desde la raíz
  - `connect_mcp()` → context manager asíncrono con `ClientSession` sobre `stdio_client`
  - `list_mcp_tools(session)` → lista de `Tool` descubiertas
  - `call_area_statistics(session, area_id, indicators)` → resultado de la invocación
- **Corrección 1.1.1**: se sustituyó el `dict` por `StdioServerParameters` y se cambió la sesión devuelta por un `async with`, porque el transporte se cierra al salir del contexto
- **Integración probada**: `tests/test_mcp_integration.py` arranca el servidor real y verifica conexión, descubrimiento e invocación

### `data/sources.json` (21/10/2026)
- **Creado**: Catálogo de fuentes relevantes
- Contenido: `ddg_gym_search`, `mcp_local_data` con descripciones, limitaciones y uso

### `data/raw/README.md` (21/10/2026)
- **Creado**: Documentación de datos locales
- Contenido: qué datos usa MCP, procedencia, limitaciones, cómo preparar/actualizar datos

---

## Verificación y Pruebas (21-22/10/2026)

### `run_tests.py` (22/10/2026)
- **Creado**: Suite de pruebas completas
- **Resultados**:
  - Schemas: todas las validaciones Pydantic OK
  - Tools: importaciones y validación correcta
  - Researcher: `build_researcher()`, `build_research_task()`, `run_research()` OK
  - MCP Server: `get_area_statistics()` funciona
  - File structure: todos los archivos esperados presentes

### Cuestiones Resueltas
- Errores de sintaxis resueltos (`MAX_SNIPPLENGTH` vs `MAX_SNIPPLENGTH`, comillas en strings)
- Importaciones CrewAI adaptadas (herramientas usadas directamente, no pasadas al Agent)
- Validaciones Pydantic corregidas (limitations como string vs lista)
- Rutas de Python consistentes desde la raíz del repositorio

### Corrección del transporte MCP (20/10/2026)
- `server.py` devolvía `dict` en `list_tools()`; el SDK espera `mcp.types.Tool` (fallo `'dict' object has no attribute 'name'`)
- `client.py` pasaba un `dict` a `stdio_client`; ahora usa `StdioServerParameters` (fallo `'dict' object has no attribute 'command'`)
- La sesión se devolvía fuera del contexto `async with`, por lo que se cerraba antes de usarse; ahora `connect_mcp()` es un context manager
- Añadida `tests/test_mcp_integration.py`, que arranca el servidor real por stdio
- Verificación manual: `python -m src.mcp.client` conecta, descubre 1 herramienta y devuelve estadísticas

### Corrección de la extracción de precios (20/10/2026)
- `_extract_evidence_from_page()` usaba `findall` con un solo grupo y luego `price_patterns[0][0]`, que devuelve el primer carácter del importe en vez del número
- Nueva regex con importes españoles e ingleses, parseo de separadores de miles y decimales
- Se distingue cuota mensual de matrícula y se prefiere la mensual
- Los precios se reflejan también en `Competitor.tariffs`
- Añadidos 5 tests específicos de importes
- Suite completa: **42 passed**

---

## Estructura Final del Repositorio

```
FitFamily/
├── .git/                    # Control de versiones
├── .gitignore
├── LICENSE
├── README.md                # Descripción general del proyecto
├── IMPLEMENTATION_SUMMARY.md  # Este resumen (creado)
├── CHANGES_LOG.md           # Registro de cambios (creado)
├── src/
│   ├── schemas.py           # Modelos Pydantic (creado 19/10)
│   ├── agents/
│   │   └── researcher.py    # Agente CrewAI (creado 20/10)
│   ├── tools/
│   │   ├── search_web.py          # Búsqueda web (creado 19/10)
│   │   ├── read_web_page.py       # Lectura web (creado 19/10)
│   │   └── competitor_search.py   # Búsqueda competidores (creado 20/10)
│   └── mcp/
│       ├── server.py          # Servidor MCP (creado 20/10)
│       └── client.py          # Cliente MCP (creado 20/10)
├── data/
│   ├── sources.json         # Catálogo de fuentes (creado 21/10)
│   └── raw/
│       └── README.md        # Datos locales (creado 21/10)
├── test_*.py                # Archivos de prueba temporales (eliminados)
└── run_tests.py             # Suite de pruebas (eliminado)
```

### Confirmación
- **No se modificaron** archivos de otras personas (Laura, Gema, María, Isabella)
- **No se hicieron commits** durante la implementación (archivos creados/editados en Working Directory)
- **No se hicieron pushes** a remoto
- **No se borraron** ni revertieron archivos preexistentes
- Las nuevas dependencias (`crewai`, `tavily-python` añadidas vía `pip install`) están justificadas

---

## Próximos Pasos para el Equipo

1. **Isabella (Persona 5)**: Puede importar `run_research()` para consumir el módulo en Streamlit/LangGraph
2. **Gema (Persona 3)**: Puede usar los modelos `Evidence`/`Competitor` para sus informes
3. **María (Persona 4)**: Puede consumir `ResearchResult` para validaciones y rutas de revisión
4. **Laura (Persona 2)**: Puede usar resultados Python/JSON para análisis de escenarios y gráficos

El módulo está diseñado para ser consumido a través de la interfaz pública `run_research(brief, context)` sin necesidad de conocer implementaciones internas.