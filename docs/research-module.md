# Módulo de Investigación y MCP - FitFamily

> **Persona 1: Juan** — Investigador, búsqueda web, herramientas y MCP  
> **Propósito**: Localizar competidores, recuperar información verificable, registrar evidencias y proporcionar interfaz estable para el resto del equipo.

---

## 📝 Descripción General

El **Módulo de Investigación y MCP** es el responsable de Persona 1 en el proyecto FitFamily. Su misión es:

- Investigar el mercado de gimnasios con ludoteca en El Cañaveral, Madrid
- Localizar competidores y recopilar datos verificables
- Normalizar resultados y proporcionar modelos estructurados
- Exposer herramientas mediante el protocolo Model Context Protocol (MCP) para uso interno

**Este módulo vive únicamente en local**. No requiere claves de API, servicios en la nube ni conectividad constante a Internet para funcionar. Todas las búsquedas y Lecturas web pueden fallar gracefuly si no hay red, pero la estructura, validación y lógica interna funcionan completamente offline.

---

## ✨ Características Principales

### 1. Búsqueda y Lectura Web
- `search_web(query, max_results)`: Busca en la web usando DuckDuckGo (sin API key)
- `read_web_page(url)`: Lee páginas HTML y extrae contenido limpio
- Validación de URLs (solo http/https)
- Bloqueo de IPs privadas y redes internas
- Manejo de timeouts y errores controlados
- **No ejecuta código** ni sigue instrucciones de páginas web

### 2. Búsqueda de Competidores
- `competitor_search(params)`: Identifica competidores por área y tipo de negocio
- Deduplicación por URL, dominio, nombre y ubicación
- Extrae datos con validación Pydantic
- Distingue entre: ausencia de datos, inaccesibilidad y datos encontrados
- **No inventa** competidores, direcciones, precios o estadísticas

### 3. Agente CrewAI
- `run_research(brief, context) → ResearchResult`: Función pública del contrato
- `build_researcher()` define el rol, objetivo y *backstory* del agente
- `build_research_task(brief, context)` genera la tarea con las reglas de la investigación
- **La ejecución real es determinista**: `run_research()` usa las herramientas Python directamente, sin LLM ni clave OpenAI
- La orquestación completa con CrewAI + LLM queda como fase posterior (ver Limitaciones)

### 4. Protocolo MCP (Model Context Protocol)
- `get_area_statistics(area_id, indicators)`: Herramienta publicada localmente
- Cliente MCP que descubre e invoca herramientas del servidor
- Comunicación a través de `stdio` (proceso local solo)
- Sin Cloudflare ni servidores externos por defecto
- Datos reales poblados con procedencia por indicador (ver `data/sources.json`)

### 5. Modelos Pydantic Compartidos
- `Evidence`: registra afirmaciones con fuente, valor, unidad, fragmento y limitaciones
- `Competitor`: identifica competidores con nombre, ubicación, servicios, tarifas
- `ResearchBrief`: encargo de investigación con tipo, ubicación, área y preguntas
- `ResearchResult`: resultado estructurado con evidencias, competidores y cobertura

---

## 🛠️ Instalación

```bash
# Desde la raíz del repositorio FitFamily
python -m pip install -r requirements.txt
```
**Nota sobre dependencias:**
- El código utiliza `ddgs` (no `duckduckgo-search`, que es el nombre anterior del paquete).
- `tavily-python` es opcional: solo se necesita si se configura `TAVILY_API_KEY` en el entorno.
- `mcp` es el SDK oficial del protocolo, necesario para el servidor y el cliente locales.
- `pytest` solo es necesario para ejecutar la suite de pruebas.



**No se requieren** credenciales, claves API ni servicios externos para el funcionamiento básico.

---

## 🚀 Uso Básico

```python
from src.schemas import ResearchBrief
from src.agents.researcher import run_research

# Definir el encargo de investigación
brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location="Madrid",
    study_area="El Cañaveral",
    questions=[
        "¿Cuáles son las tarifas mensuales?",
        "¿Qué servicios incluyen?",
    ],
    search_limits={"max_results": 10},
)

# Ejecutar investigación (funciona offline, usa herramientas locales)
result = run_research(brief, context=None)

# Consumir resultados
print(f"Competidores: {len(result.competitors)}")
print(f"Evidencias: {len(result.evidences)}")
print(f"Cobertura: {result.coverage_percentage}%")
```

**Sin conexión a Internet**: El módulo funciona completamente offline. Las búsquedas web devolverán errores controlados, pero la estructura, validación y lógica interna son totalmente funcionales.

**Con conexión a Internet**: `search_web` y `read_web_page` realizarán búsquedas y lecturas reales.

---

## 🔌 Uso del MCP

El cliente abre una sesión contra el servidor local y la mantiene abierta dentro de un
contexto asíncrono. La sesión **no puede devolverse fuera del `async with`**: al salir
del contexto se cierra el subproceso del servidor.

```python
import asyncio
from src.mcp.client import connect_mcp, list_mcp_tools, call_area_statistics

async def main():
    async with connect_mcp() as session:          # arranca el servidor por stdio
        tools = await list_mcp_tools(session)     # descubre get_area_statistics
        print([t.name for t in tools])

        stats = await call_area_statistics(
            session,
            area_id="el-cañaveral",
            indicators=["gyms_with_ludoteca", "population_total"],
        )
        print(stats["results"])

asyncio.run(main())
```

Prueba de integración real (arranca el servidor y verifica la llamada):

```bash
python -m src.mcp.client
```

---

## 🧪 Pruebas

```bash
python -m pytest -q
```

- `tests/test_mcp.py`: pruebas unitarias de la función y del cliente (sin subproceso).
- `tests/test_mcp_integration.py`: prueba real extremo a extremo por `stdio`.
- El resto de archivos cubren schemas, herramientas web y el agente.

---

## Semántica de coverage_percentage

El campo `coverage_percentage` en `ResearchResult` representa la **cobertura de respuestas generadas mediante análisis LLM**, NO el volumen de datos recogidos.

- `0.0%`: Sin análisis LLM. El módulo funciona con herramientas deterministas (sin clave OpenAI).
- Los datos reales (competidores, evidencias, URLs, fragmentos) SÍ se recogen de la web.
- Las preguntas del encargo se marcan como no resueltas si no hay LLM para analizarlas.
- Distinción importante:
  - **Recopilación de datos**: Competidores y evidencias reales de la web (SÍ se realiza).
  - **Análisis LLM**: Interpretación y respuesta a preguntas (NO se realiza sin clave OpenAI).
  - **Preguntas respondidas**: Aquellas respaldadas por evidencia suficiente.
  - **Preguntas pendientes**: Las que requieren análisis LLM o datos adicionales.
  - **Errores**: Fallos de búsqueda o lectura se registran pero no detienen la ejecución.

El módulo NO afirma haber ejecutado un flujo de CrewAI cuando realiza la recopilación directamente mediante herramientas Python.

---

## 📁 Estructura de Archivos

```
src/
├── schemas.py              # Modelos Pydantic compartidos
├── agents/
│   └── researcher.py       # Agente CrewAI y run_research()
├── tools/
│   ├── search_web.py       # search_web(query, max_results)
│   ├── read_web_page.py    # read_web_page(url)
│   └── competitor_search.py # competitor_search(params)
└── mcp/
    ├── server.py           # get_area_statistics(area_id, indicators)
    └── client.py           # connect_mcp() (context manager), list_mcp_tools(), call_area_statistics()

data/
├── sources.json           # Catálogo de fuentes
└── raw/
    └── README.md          # Documentación de datos locales
```

---

## 👥 Consumo por Otros Módulos

### Para Isabella (Persona 5 - Streamlit/LangGraph):
```python
from fitfamily.src.agents.researcher import run_research
from fitfamily.src.schemas import ResearchBrief

brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location=city,
    study_area=district,
    questions=questions_list
)

result = run_research(brief, context=some_context)
# Usar result.competitors, result.evidences, etc.
```

### Para Gema (Persona 3 - Redacción de Informes):
```python
from fitfamily.src.schemas import Evidence, Competitor, ResearchResult
# Los modelos son estándar y pueden ser serializados a JSON/CSV
```

### Para María (Persona 4 - Revisor Crítico):
```python
from fitfamily.src.schemas import ResearchResult
# Validar resultados y rutas de revisión
```

### Para Laura (Persona 2 - Análisis Financiero):
```python
from fitfamily.src.schemas import Competitor, ResearchResult
# Acceder a tarifas, servicios, estructuras de datos
```

**Importante**: Ningún módulo necesita importar `src.tools.*` o `src.agents.*` directamente. El punto de entrada único y estable es `run_research(brief, context)`.

---

## ⚠️ Limitaciones y Consideraciones

### Bloqueadas por el Entorno
- `search_web` y `read_web_page` requieren Internet para datos reales; offline fallan de forma controlada
- El proveedor DuckDuckGo puede bloquear búsquedas en ciertos regímenes

### Datos MCP
- Mezcla de datos oficiales (Padrón Municipal) y documentados (Wikipedia, medios locales)
- Cada indicador lleva su propia limitación; los no disponibles siguen en `null`
- Solicitar un área distinta de El Cañaveral devuelve `null` con limitación, en lugar de los datos de El Cañaveral
- Para añadir o corregir datos: editar `_STATISTICS_DATA` en `src/mcp/server.py` y `data/sources.json`

### Transporte MCP
- El servidor y el cliente usan el SDK oficial (`mcp`) y se comunican por `stdio` con un subproceso local
- La sesión debe usarse dentro de `async with connect_mcp() as session:`
- La prueba `tests/test_mcp_integration.py` arranca el servidor real y verifica la llamada

### Sin LLM Requerido
- `run_research()` funciona sin clave OpenAI usando herramientas reales y deterministas
- Con LLM disponible, el agente utilizaría las herramientas para recopilar datos reales

### CrewAI: estado y decisión de diseño
- `build_researcher()` y `build_research_task()` están implementados y devuelven objetos CrewAI válidos
- `run_research()` **no ejecuta un `Crew`**: recopila datos con las herramientas deterministas para no depender de una clave LLM y para que el resultado sea reproducible
- Conectar las herramientas al agente requiere envolverlas como `BaseTool` y disponer de un proveedor LLM configurado
- Esa conexión es una fase posterior, no un bug: el valor actual está en los datos verificables, no en el texto generado
- Si se activa un LLM, las preguntas del brief podrían analizarse y `coverage_percentage` dejaría de ser 0.0

---

## 📞 Contacto y Soporte

- **Propietario**: Juan (Persona 1)
- **Proyecto**: FitFamily - Viabilidad gimnasio con ludoteca en El Cañaveral, Madrid
- **Ramas relacionadas**: 
  - `src/` → responsabilidad exclusiva de Persona 1
  - No modificar archivos fuera de `src/mcp/`, `src/agents/`, `src/tools/`, `src/schemas/`
- **¿Dudas?**: Revisar `docs/research-changelog.md` para el historial completo de cambios

---

## 📜 Licencia

Este módulo forma parte del proyecto FitFamily. Consulte el archivo `LICENSE` en la raíz del repositorio para términos y condiciones.

---

**Última actualización**: 20 de octubre de 2026
**Versión**: 1.1.3 — Robustez de MCP, precios y límites