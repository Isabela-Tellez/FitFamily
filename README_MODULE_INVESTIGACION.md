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
- Agente con rol, objetivo y *backstory* definidos
- Usa las herramientas registradas, no responde solo por LLM
- Valida entradas y gestiona errores estructurados
- Sin clave OpenAI requerida para operación básica

### 4. Protocolo MCP (Model Context Protocol)
- `get_area_statistics(area_id, indicators)`: Herramienta publicada localmente
- Cliente MCP que descubre e invoca herramientas del servidor
- Comunicación través de `stdio` (proceso local solo)
- Sin Cloudflare ni servidores externos por defecto
- Datos placeholder preparados para poblarse con fuentes reales

### 5. Modelos Pydantic Compartidos
- `Evidence`: registra afirmaciones con fuente, valor, unidad, fragmento y limitaciones
- `Competitor`: identifica competidores con nombre, ubicación, servicios, tarifas
- `ResearchBrief`: encargo de investigación con tipo, ubicación, área y preguntas
- `ResearchResult`: resultado estructurado con evidencias, competidores y cobertura

---

## 🛠️ Instalación

```bash
# Desde la raíz del repositorio FitFamily
pip install crewai duckduckgo-search tavily-python
```

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
    └── client.py           # connect_mcp(), list_mcp_tools(), call_area_statistics()

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
# Los modelos son estándard y pueden ser serializados a JSON/CSV
```

### Para María (Persona 4 - Revisor Crítico):
```python
from fitfamily.src.schemas import ResearchResult
# Validar resultados, checker rutas de revisión
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
- `search_web` y `read_web_page` requieren Internet para datos reales; fallan gracefuly offline
- El proveedor DuckDuckGo puede bloquear búsquedas en ciertos regímenes

### Datos MCP
- Los indicadores actuales son *placeholder* (valores `null` con limitaciones documentadas)
- Para datos reales: poblar `_STATISTICS_DATA` en `src/mcp/server.py` con fuentes municipales de Madrid/El Cañaveral

### Sin LLM Requerido
- `run_research()` funciona sin clave OpenAI usando herramientas sintéticas/deterministas
- Con LLM disponible, el agente utilizaría las herramientas para recopilar datos reales

---

## 📞 Contacto y Soporte

- **Propietario**: Juan (Persona 1)
- **Proyecto**: FitFamily - Viabilidad gimnasio con ludoteca en El Cañaveral, Madrid
- **Ramas relacionadas**: 
  - `src/` → responsabilidad exclusiva de Persona 1
  - No modificar archivos fuera de `src/mcp/`, `src/agents/`, `src/tools/`, `src/schemas/`
- **¿Dudas?**: Revisar `IMPLEMENTATION_SUMMARY.md` para el historial completo de cambios

---

## 📜 Licencia

Este módulo forma parte del proyecto FitFamily. Consulte el archivo `LICENSE` en la raíz del repositorio para términos y condiciones.

---

**Ú actualización**: 22 de octubre de 2026  
**Versión**: 1.0.0 — Implementación inicial completa