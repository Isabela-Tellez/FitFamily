# FitFamily

FitFamily analiza la viabilidad de abrir un gimnasio con ludoteca en El Cañaveral (Madrid). El repositorio contiene el módulo de investigación, los datos municipales con su estado de verificación y las interfaces de análisis y redacción. Todavía no existe un ejecutable único que recorra todo el producto de extremo a extremo; el estado detallado está en [docs/arquitectura-modulos.md](docs/arquitectura-modulos.md).

## Estado actual

Implementado:

- Investigación con `run_research(brief)`: búsqueda web y búsqueda de competidores; esta última lee las páginas encontradas.
- Servidor MCP local con la herramienta `get_area_statistics` y cliente de comprobación.
- Esquemas compartidos: `ResearchBrief`, `ResearchResult`, `Evidence` y `Competitor`.
- Análisis descriptivo de competidores con `summarize_competitors`.
- Borrador de informe en memoria con `WriterAgent`.
- Extracción offline de hogares con `data/raw/extract_households.py`.

Pendiente:

- CLI u orquestador que encadene investigación → análisis → informe.
- Exportación de informes y interfaz de usuario.
- Orquestación LLM con CrewAI: hoy se construyen `Agent`/`Task`, pero `run_research` ejecuta las herramientas directamente.
- Módulos `automation`, `graph`, `multimodal`, `review`, `runtime`, `security` y `ui`.

## Requisitos

- Python 3.13 (versión usada en la verificación local y configurada en el workflow de CI).
- Git.
- Acceso a internet para las búsquedas y la lectura de páginas web.
- Opcional: `TAVILY_API_KEY` para usar Tavily en lugar de DuckDuckGo.

## Instalación

```bash
git clone https://github.com/Isabela-Tellez/FitFamily.git
cd FitFamily
python -m venv .venv
```

Activa el entorno virtual.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Instala las dependencias:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuración

La aplicación lee las variables del entorno del proceso. `.env.example` documenta los nombres; exporta las variables en tu shell o en el entorno de ejecución.

`TAVILY_API_KEY` es opcional.

Windows PowerShell:

```powershell
$env:TAVILY_API_KEY = "..."
```

macOS/Linux:

```bash
export TAVILY_API_KEY="..."
```

Si la variable no está definida, `search_web` usa DuckDuckGo mediante `ddgs`. No guardes claves reales en el repositorio.

## Ejecución

Ejecuta los comandos y ejemplos desde la raíz del repositorio.

### Comprobar el servidor MCP

```bash
python -m src.mcp.client
```

Arranca el servidor local por `stdio`, descubre sus herramientas y llama a `get_area_statistics`.

### Arrancar el servidor MCP

```bash
python -m src.mcp.server
```

El servidor se queda escuchando por `stdio`; está pensado para que lo lance un cliente MCP, no para funcionar como servidor HTTP.

### Ejecutar una investigación desde Python

Todavía no hay una CLI de investigación. La interfaz actual es:

```python
from src.schemas import ResearchBrief
from src.agents.researcher import run_research

brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location="Madrid",
    study_area="El Cañaveral",
    questions=["precios", "servicios", "horarios"],
)
result = run_research(brief)
print(result.model_dump_json(indent=2))
```

La búsqueda y la lectura de páginas requieren red. Si una fuente falla, el resultado conserva las evidencias disponibles y describe el problema en `search_performed` o `notes`.

### Análisis y borrador

`summarize_competitors(data)` espera un `pandas.DataFrame` con las columnas `gym_name`, `monthly_price_eur` y `has_playroom`. `WriterAgent().create_draft(brief, result)` genera un `ReportDraft` en memoria; no exporta archivos. No existe todavía un adaptador automático de `ResearchResult` al DataFrame.

## Pruebas y calidad

```bash
python -m pytest -q
python -m compileall -q src tests data/raw
```

Para ejecutar solo las pruebas del investigador:

```bash
python -m pytest tests/test_researcher.py -q
```

Las pruebas del investigador sustituyen las herramientas web por respuestas controladas; el test de integración MCP arranca un subproceso local y no necesita internet. El workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) ejecuta `compileall` y `pytest` con Python 3.13 en `push` a `dev`/`main` y en pull requests contra esas ramas.

No hay linter ni comprobador de tipos configurado en el repositorio; por tanto, no se ejecutan en CI.

## Datos

- `data/sources.json`: catálogo de fuentes, períodos y limitaciones.
- `data/raw/README.md`: indicadores publicados, procedencia y actualización.
- `data/raw/extract_households.py`: extracción offline reproducible de hogares. La verificación geométrica (`--verify-geometry`) requiere `pyogrio`, que no forma parte de las dependencias de runtime.
- Las descargas grandes y la caché (`data/raw/cache/`) están ignoradas por Git.

## Documentación

- [Mapa de módulos e interfaces](docs/arquitectura-modulos.md)
- [Módulo de investigación](docs/research-module.md)
- [Implementación](docs/research-implementation.md)
- [Auditoría de fuentes](docs/auditoria-fuentes-datos.md)
- [Changelog de investigación](docs/research-changelog.md)

## Limitaciones

Este repositorio no es todavía un producto completo: no hay interfaz de usuario, orquestador único, exportación de informes ni ejecución LLM de extremo a extremo. Los datos publicados por el MCP son locales y deben citarse con su período y fuente; un valor `null` significa "no disponible", no cero.
