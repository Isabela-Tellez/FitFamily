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
- `search_limits.max_results` del encargo se respeta (por defecto 5, máximo 20, el límite que aceptan las herramientas)
- La orquestación completa con CrewAI + LLM queda como fase posterior (ver Limitaciones)

### 4. Protocolo MCP (Model Context Protocol)
- `get_area_statistics(area_id, indicators)`: Herramienta publicada localmente
- Cliente MCP que descubre e invoca herramientas del servidor
- Comunicación a través de `stdio` (proceso local solo)
- Sin Cloudflare ni servidores externos por defecto
- Datos reales poblados con procedencia por indicador (ver `data/sources.json`)
- `refresh_locales_count(area_id)`: actualización reproducible del Censo de Locales (descarga bajo demanda, sin red en las consultas MCP)

### 5. Modelos Pydantic Compartidos
- `Evidence`: registra afirmaciones con fuente, valor, unidad, fragmento y limitaciones
- `Competitor`: identifica competidores con nombre, ubicación, servicios, tarifas
- `ResearchBrief`: encargo de investigación con tipo, ubicación, área y preguntas
- `ResearchResult`: resultado estructurado con evidencias, competidores y cobertura

### 6. Descubrimiento de fuentes
- `src/tools/source_discovery.py` convierte una variable pendiente en varias consultas
  (literal, "datos abiertos", "estadística" y una por organismo con `site:`), clasifica
  cada resultado como `discovered`, `accessible`, `extracted`, `validated` o `rejected` con
  motivo explícito, y distingue páginas informativas de datasets descargables.
- `ResearchBrief.missing_variables` (opcional) dispara esa pasada en `run_research()`: las
  candidatas vuelven como `Evidence` con URL, organismo, consulta y estado.
- Una fuente nunca se presenta como verificada sin haber leído su contenido.
- Fase documentada y pendiente: renta por sección censal (INE ADRH, operación 30325) en
  `docs/pendiente-renta-ine.md`.
### 7. Registro de competidores (oficial)
- `src/tools/competitor_registry.py` une los tres recursos del Censo de Locales del
  Ayuntamiento (locales, actividades y licencias) en registros de `Competitor` con el
  identificador oficial del local.
- Cada campo oficial lleva su propia `Evidence` (URL, fecha de consulta, limitaciones),
  de modo que los datos municipales se distinguen de los comerciales.
- Coordenadas `0,0` o fuera del entorno UTM 30N de Madrid se tratan como **no
  disponibles** y no se usan para distancias ni clustering.
- Una licencia ausente significa "no hay información", nunca "denegada".
- La web del establecimiento solo se vincula si coinciden la calle **y el número**
  oficial. Un rango publicado que incluya el número (`42-46` para el 44) se acepta; si
  el censo no publica número, solo se puede comprobar la calle.
- `has_playroom` es `True`/`False` solo con evidencia fiable; si no, queda `None`
  (desconocido). Una mención negada ("no dispone de ludoteca", "sin sala infantil",
  "ludoteca no disponible") no cuenta como oferta y **no** se registra como `True`.
- `to_dataframe()` produce el DataFrame que consume el módulo de análisis de mercado
  (`gym_name`, `monthly_price_eur`, `has_playroom` y contexto adicional).
- Script reproducible: `python data/raw/extract_competitor_registry.py`.

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
│   └── researcher.py       # Agente CrewAI, run_research() y descubrimiento de fuentes
├── tools/
│   ├── search_web.py       # search_web(query, max_results)
│   ├── read_web_page.py    # read_web_page(url)
│   ├── competitor_search.py # competitor_search(params)
│   ├── competitor_registry.py # Registro de competidores sobre el Censo de Locales
│   └── source_discovery.py # Descubrimiento de fuentes por variable pendiente
├── mcp/
│   ├── server.py           # get_area_statistics(area_id, indicators)
│   └── client.py           # connect_mcp() (context manager), list_mcp_tools(), call_area_statistics()

data/
├── sources.json           # Catálogo de fuentes
├── processed/             # Artefactos generados (registro de competidores)
└── raw/
    ├── README.md          # Documentación de datos locales
    ├── extract_censo_locales.py
    ├── extract_households.py
    └── extract_competitor_registry.py

docs/
├── research-module.md
├── research-implementation.md
├── research-changelog.md
├── auditoria-fuentes-datos.md   # Investigación de fuentes por indicador
└── pendiente-renta-ine.md       # Fase de renta (INE ADRH) documentada, no implementada
```

---

## 👥 Consumo por Otros Módulos

> **Nota para los consumidores:** `ResearchResult.evidences` ya incluye las evidencias
> que lleva cada `Competitor`. Si concatenáis `competitor.evidences` a esa lista,
> las cuentas salen duplicadas. Usad la lista global para contar y la de cada competidor
> solo para agrupar por fuente.

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
- Todos los valores publicados proceden de **fuentes primarias oficiales** del Ayuntamiento de Madrid
- Población (27.480) y pirámide de edad (28,29 %): Padrón Municipal, referencia oct 2026
- Hogares (8.140) y tamaño medio (2,64): fichero oficial de hogares, referencia 1 ene 2025, agregados **exactamente** sobre las 9 secciones censales que la cartografía oficial asigna al barrio
- Hogares con menores (3.071, **mínimo verificable**): hoja de composición del hogar del mismo fichero oficial
- `population_total_2025` (21.492) se publica para que los households de 2025 no se combinen con la población de 2026
- Locales abiertos (234) y equipamientos (gimnasios 9, deporte y recreación 4, ocio infantil 3, piscinas 3): Censo de Locales, descarga del 20 oct 2026
- Cada indicador lleva `verification_status`: `verified`, `unverified` o `unavailable`
- Solicitar un área distinta de El Cañaveral devuelve `null` con limitación
- Actualización reproducible: `refresh_locales_count()`, `refresh_gyms_count()`, `refresh_households()` y `refresh_households_with_minors()`; scripts offline en `data/raw/`

### Transporte MCP
- El servidor y el cliente usan el SDK oficial (`mcp`) y se comunican por `stdio` con un subproceso local
- La sesión debe usarse dentro de `async with connect_mcp() as session:`
- La prueba `tests/test_mcp_integration.py` arranca el servidor real y verifica la llamada

### Seguridad web (SSRF)
- Validación de esquema, host, puerto y credenciales antes de la petición
- Resolución DNS validada inmediatamente antes de conectar
- Redirecciones gestionadas manualmente, validando cada destino
- Clasificación de destinos con el módulo estándar `ipaddress`: se rechazan loopback, privadas, link-local, multicast, no especificadas, reservadas, CGNAT y direcciones IPv4 mapeadas en IPv6 (`::ffff:127.0.0.1`)
- **Transporte HTTP personalizado (`_ValidatingTransport`)**: conecta exclusivamente a IP validadas, resolviendo el TOCTOU/DNS rebinding. TLS/SNI y validación de certificados se preservan (httpcore pasa `server_hostname` por separado)

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
**Versión**: 1.1.5 — Endurecimiento SSRF y pruebas de seguridad