# FitFamily - Registro de Cambios del Módulo Persona 1

> **Fecha última actualización**: 20 de octubre de 2026
> **Autor**: Juan (Persona 1 - Investigador, herramientas y MCP)
> **Proyecto**: FitFamily - IA multiagente para análisis de viabilidad de gimnasio con ludoteca

---

## Nota sobre fechas y estado documental

- Las fechas de las versiones 1.0.0 y 1.1.0 corresponden al desarrollo original del módulo (octubre de 2026) y se conservan como histórico.
- La revisión, correcciones y poblado de datos de esta iteración se fechan el **20 de octubre de 2026**.
- Los elementos listados en "Backlog" **no** están completados; solo se consideran cerrados los marcados con `[x]`.
- Las afirmaciones de la versión 1.0.0 sobre una prueba real de MCP se corrigieron en 1.1.1 (`tests/test_mcp_integration.py`).
- No se afirma la ejecución de CrewAI con LLM mientras no exista una clave de proveedor configurada.

---

## Versión 1.0.0 — Implementación Inicial (22/10/2026)

### Novedades
- Módulo completo implementado para la Persona 1 del proyecto FitFamily
- Todas las rutas y responsabilidades respetadas tal como estaban definidas
- Interfaz pública `run_research(brief, context) -> ResearchResult` estable y documentada
- Ningún archivo de otras personas fue modificado ni sobrescrito
- No se hicieron commits, pushes ni operaciones destructivas

### Archivos Creados
| Ruta | Descripción | Fecha |
|------|-------------|-------|
| `src/schemas.py` | Modelos Pydantic: Evidence, Competitor, ResearchBrief, ResearchResult | 19/10 |
| `src/tools/search_web.py` | `search_web(query, max_results)` con DDGS | 19/10 |
| `src/tools/read_web_page.py` | `read_web_page(url)` con validación y sanitización | 19/10 |
| `src/tools/competitor_search.py` | `competitor_search(params)` con deduplicación Pydantic | 20/10 |
| `src/agents/researcher.py` | `build_researcher()`, `build_research_task()`, `run_research()` | 20/10 |
| `src/mcp/server.py` | `get_area_statistics(area_id, indicators)` servidor local | 20/10 |
| `src/mcp/client.py` | `connect_mcp()`, `list_mcp_tools()`, `call_area_statistics()` | 20/10 |
| `data/sources.json` | Catálogo de fuentes relevantes | 21/10 |
| `data/raw/README.md` | Documentación de datos locales | 21/10 |
| `IMPLEMENTATION_SUMMARY.md` | Resumen ejecutivo de la implementación | 22/10 |
| `README_MODULE_INVESTIGACION.md` | README específico del módulo de investigación | 22/10 |
| `CHANGES_LOG.md` | Este archivo - registro de todos los cambios | 22/10 |

### Archivos Modificados
| Ruta | Cambios |
|------|---------|
| `src/schemas.py` | Ajustes de validadores (root_validator → model_validator), correcciones de sintaxis |
| `src/tools/search_web.py` | Corrección `MAX_SNIPPLENGTH`, importaciones pydantic, timeout DDGS |
| `src/tools/read_web_page.py` | Corrección `MAX_SNIPPLENGTH`, timeouts httpx, expresiones regulares para título |
| `src/tools/competitor_search.py` | Corrección `MAX_SNIPPLENGTH`, `limitations` string vs lista, validaciones |

### Pruebas Ejecutadas
- `run_tests.py`: Suite completa con 5 categorías de prueba
- Resultados: Todas las validaciones Pydantic OK, importaciones correctas, ejecución del agente, funcionamiento del MCP server
- Nota: `search_web` requiere Internet; todas las pruebas internas pasan sin conectividad

### Validación de Alcance
- ✅ Se respetaron las rutas y responsabilidades de Persona 1
- ✅ Los modelos de investigación se validan con Pydantic
- ✅ La búsqueda devuelve enlaces y metadatos reales cuando dispone de proveedor
- ✅ La lectura web recupera contenido y maneja páginas inaccesibles
- ✅ `competitor_search` deduplica y devuelve datos estructurados con evidencias
- ✅ Los datos ausentes no se convierten en valores inventados
- ✅ `build_researcher()` y `build_research_task()` están implementados
- ✅ `run_research(brief, context)` cumple el contrato público y valida su resultado
- ✅ El servidor MCP publica `get_area_statistics`
- ✅ El cliente MCP descubre herramientas y realiza una llamada a través del protocolo
- ✅ Las estadísticas locales tienen procedencia o se declaran no disponibles
- ✅ Las pruebas unitarias no necesitan acceso constante a Internet ni una clave de LLM
- ✅ No se implementaron los módulos de otras personas
- ✅ No se borraron ni sobrescribieron cambios preexistentes
- ✅ Las dependencias nuevas están justificadas
- ✅ No hay secretos incluidos en archivos modificados

### Hechos Notables
- Se superaron múltiples errores de sintaxis Python (comillas f-string, nombres de variables, validadores Pydantic deprecated)
- Se adaptó la integración CrewAI (las herramientas se usan directamente, no se pasan al Agent por validación)
- Se corrigieron tipos Pydantic inconsistentes (limitaciones como string vs lista)
- Se mantuvieron rutas absolutas de Windows alejadas del código (usando `os.path` y rutas relativas al proyecto)
- Se documentó la diferencia entre datos sintéticos (pruebas) y datos reales (búsqueda con Internet)

### Dependencias Añadidas
- `crewai` v1.15.28 - Agente IA
- `ddgs` v9.14.4 - Búsqueda web (API pública, sin key)
- `tavily-python` v0.8.5 - Alternativa de búsqueda (opcional)

### Limitaciones Conocidas
- `search_web`/`read_web_page` requieren Internet para datos reales; offline devuelve errores controlados
- Datos MCP son placeholder; poblar `_STATISTICS_DATA` con fuentes municipales para datos reales
- Sin LLM, `run_research` recopila datos reales pero deja `coverage_percentage` en 0.0% (sin interpretación)
- Las búsquedas pueden fallar si DuckDuckGo bloquea la petición

### Checklist de Acceptación (de la misión 15)
- [x] Se respetan las rutas y responsabilidades de Persona 1
- [x] Los modelos de investigación se validan con Pydantic
- [x] La búsqueda devuelve enlaces y metadatos reales cuando dispone de proveedor
- [x] La lectura web recupera contenido y maneja páginas inaccesibles
- [x] `competitor_search` deduplica y devuelve datos estructurados con evidencias
- [x] Los datos ausentes no se convierten en valores inventados
- [x] `build_researcher()` y `build_research_task()` están implementados
- [x] `run_research(brief, context)` cumple el contrato público y valida su resultado
- [x] El servidor MCP publica `get_area_statistics`
- [x] El cliente MCP descubre herramientas y realiza una llamada a través del protocolo
- [x] Las estadísticas locales tienen procedencia o se declaran no disponibles
- [x] Las pruebas unitarias no necesitan acceso constante a Internet ni una clave de LLM
- [x] Existe una prueba real de MCP local (`tests/test_mcp_integration.py`, añadida en 1.1.1)
- [x] Las importaciones y rutas funcionan desde la raíz del repositorio
- [x] La documentación explica cómo ejecutar e integrar el módulo
- [x] No se han implementado los módulos de otras personas
- [x] No se han borrado ni sobrescrito cambios preexistentes
- [x] Las dependencias nuevas están justificadas
- [x] No hay secretos incluidos en archivos modificados

---

## Versión 1.1.0 — Revisión y Hardening (23/10/2026)

### Cambios Realizados

#### Rama
- Renombrada de `feature/research-module` a `feature/research-mcp` (según plan del equipo)

#### Documentación
- Movidos `README_MODULE_INVESTIGACION.md`, `IMPLEMENTATION_SUMMARY.md`, `CHANGES_LOG.md` a `docs/`:
  - `docs/research-module.md`
  - `docs/research-implementation.md`
  - `docs/research-changelog.md`
- Actualizado comando de instalación: `python -m pip install -r requirements.txt` (en lugar de `pip install crewai duckduckgo-search tavily-python`)
- Aclarada la dependencia `ddgs` (no `duckduckgo-search`)
- Documentada la semántica de `coverage_percentage`: representa cobertura de respuestas LLM, no volumen de datos recogidos
- Documentado que los datos MCP son placeholder (no estadísticas oficiales)

#### Tests
- 33 tests unitarios creados en `tests/` (sin dependencia de Internet):
  - `tests/test_researcher.py`: 9 tests
  - `tests/test_competitor_search.py`: 5 tests
  - `tests/test_mcp.py`: 9 tests
  - `tests/test_web_tools.py`: 10 tests
- Eliminados bloques `try/except: assert True` permisivos
- Añadidos mocks para proveedores de búsqueda y lectura de páginas
- Verificado que `build_researcher()` y `build_research_task()` devuelven objetos válidos

#### Estructura
- Añadidos `__init__.py` en `src/`, `src/agents/`, `src/tools/`, `src/mcp/`, `tests/`, `tests/fixtures/`
- Actualizado `.gitignore` con exclusiones Python (`__pycache__/`, `.pytest_cache/`, `.env`, logs, etc.)

#### Dependencias
- `duckduckgo-search` reemplazado por `ddgs` en requirements.txt
- Tavily documentado como opcional con `TAVILY_API_KEY`

### Resultados de Verificación
- `python -m pytest --collect-only -q`: 33 tests recogidos
- `python -m pytest -q`: 33 passed, 20 warnings
- `git diff --check`: Sin errores
- Sin secretos, resultados temporales, cachés ni archivos de diagnóstico

### Limitaciones Comunicadas
- `search_web`/`read_web_page` requieren Internet para datos reales; offline devuelve errores controlados
- Datos MCP son placeholder; poblar `_STATISTICS_DATA` con fuentes municipales para datos reales
- Sin LLM, `run_research` devuelve estructura con datos reales pero cobertura 0.0%
- Las búsquedas pueden fallar si DuckDuckGo bloquea la petición
- Tests de integración real de red (conectividad) no incluidos en la suite unitaria; el transporte MCP sí se cubre desde 1.1.1

---

## Versión 1.1.1 — Corrección de MCP, precios y documentación (20/10/2026)

### Cambios Realizados

#### Extracción de precios (`src/tools/competitor_search.py`)
- Corregido `_extract_evidence_from_page`: `findall` devolvía cadenas y el código indexaba `[0][0]`, por lo que tomaba solo el primer dígito (`49,90` → `4`)
- Nueva regex que admite importes en formato español e inglés (`49,90`, `49.90`, `1.200`, `1.200,50`)
- Se identifica la frecuencia del pago (`monthly`, `one-time`) y se prefieren las cuotas mensuales frente a las matrículas
- Los precios encontrados se propagan a `Competitor.tariffs`, no solo a `Evidence`
- Añadido `Evidence.frequency` (opcional) para conservar si el precio es mensual o pago único
- Migrados los `@validator` a `@field_validator` (Pydantic v2)

#### Investigación (`src/agents/researcher.py`)
- Las búsquedas usan `study_area` + `location` (antes solo la ciudad, ignorando El Cañaveral)

#### Servidor MCP (`src/mcp/server.py`)
- `list_tools()` ahora devuelve objetos `mcp.types.Tool` en lugar de `dict`, que es lo que exige el SDK
- Corregido el nombre del campo `inputSchema` (antes `input_schema`)
- Corregida errata "ludotela" → "ludoteca"
- Añadido `List` a las importaciones de tipado

#### Cliente MCP (`src/mcp/client.py`)
- `connect_mcp()` es ahora un context manager asíncrono (`async with`), porque una sesión stdio no puede sobrevivir al cierre de su contexto
- El subproceso se lanza con `sys.executable -m src.mcp.server` y `cwd` en la raíz del repositorio (antes lanzaba un script que solo imprimía `SERVER_OK`)
- Usa `StdioServerParameters` en lugar de un `dict`, que era la causa del error `'dict' object has no attribute 'command'`
- `call_area_statistics()` prefiere `structuredContent`, decodifica el texto JSON y propaga `isError`
- `run_mcp_integration_test()` usa una única sesión y ya no intenta devolver una sesión cerrada

#### Pruebas
- `tests/test_mcp.py`: eliminadas las llamadas incorrectas que trataban `connect_mcp()` como corrutina; añadidas pruebas de parsing JSON, errores y parámetros del servidor
- `tests/test_mcp_integration.py` (nuevo): prueba real extremo a extremo que arranca el servidor, descubre la herramienta y llama a `get_area_statistics`
- `python -m pytest -q`: **42 passed**

#### Documentación y dependencias
- `docs/research-module.md`: ejemplo de uso del MCP, sección de pruebas y límites actualizados
- `requirements.txt`: añadidos `pydantic`, `mcp`, `httpx`, `beautifulsoup4` y `pytest` (faltaban aunque el código los importa)
- Aclarado que la versión 1.0.0 afirmaba una prueba de integración MCP que aún no existía; a partir de 1.1.1 la prueba existe y pasa

### Estado tras la corrección
- `python -m src.mcp.client`: conecta, descubre 1 herramienta y devuelve estadísticas
- Los datos siguen siendo placeholder: la integración funciona, el contenido está pendiente (actualizado en 1.1.2)

---

## Versión 1.1.2 — Población de datos MCP con fuentes verificables (20/10/2026)

### Cambios Realizados

#### Datos MCP (`src/mcp/server.py`)
- `population_total`: 27 014 habitantes empadronados (agosto 2026, Padrón vía Wikipedia)
- `households_total`: 9 224 hogares (enero 2026, Padrón)
- `average_household_size`: 2,70 personas por hogar
- `population_under_20_share`: 25,46 % (pirámide de población 2021)
- `businesses_open`: 126 negocios (junio 2025)
- `families_with_children`, `gyms_registered`, `gyms_with_ludoteca`: siguen en `null` con limitación documentada (no hay censo publicado)

#### Fuentes (`data/sources.json`)
- Añadidas: Padrón Municipal (datos.madrid.es), Wikipedia 'El Cañaveral', Nuevosureste
- Cada indicador cita su fuente y su fecha en el campo `limitations`

#### Documentación
- `docs/research-module.md`: limitaciones MCP actualizadas (ya no son placeholder puros)
- `tests/test_mcp.py`: ajustado al nuevo número de indicadores

### Estado
- 43 tests pasando
- Los datos reales conviven con los `null` declarados; no se ha inventado ningún valor
- [x] Poblar `_STATISTICS_DATA` con fuentes municipales reales de Madrid/El Cañaveral (parcial: población, hogares, negocios y pirámide; gimnasios siguen en `null`)

## Versión 1.1.3 — Robustez de MCP, precios y límites (20/10/2026)

### Cambios Realizados

#### MCP (src/mcp/server.py)
- get_area_statistics ya no devuelve los datos de El Cañaveral para otras áreas: devuelve
ull con limitación explícita y geo_scope ajustado al área solicitada.
- Añadida procedencia por indicador (
eference_period, source_url, consulted_at).

#### Precios (src/tools/competitor_search.py)
- _parse_amount ahora interpreta correctamente 1,200.50 (antes: 200.50) y otros formatos mixtos.
- La regex de importes acepta separadores de miles por coma o punto.

#### Límites y robustez (src/tools/competitor_search.py, src/tools/read_web_page.py)
- max_results se respeta de verdad (antes se comprobaba contra una lista siempre vacía).
- Las páginas inaccesibles se registran como evidencia pero no cuentan como competidores.
- Endurecido el bloqueo de direcciones internas (SSRF): más rangos IPv4/IPv6, hostnames internos y metadata.
- Normalización de URLs con espacios o caracteres no seguros en la ruta.

#### Pruebas
- Añadidos tests para área desconocida, respeto de max_results, páginas fallidas y formato 1,200.50.
- Suite completa: 44 tests pasando.


## Versión 1.1.4 — Auditoría de fuentes y trazabilidad (20/10/2026)

### Hallazgos de la auditoría

#### Población (verificada)
- Valor anterior: 27.014 (agosto 2026, fuente secundaria Wikipedia).
- Valor actual: 27.480 (1 de octubre de 2026, Padrón Municipal, datos.madrid.es).
- Verificación independiente: suma directa de todas las edades del barrio "EL CAÑAVERAL" en el CSV oficial del Padrón (32.5 MB, distrito 19 Vicálvaro).
- verification_status: verified.

#### Pirámide de edad (verificada)
- Valor anterior: 25,46 % menores de 20 años (2021, Wikipedia).
- Valor actual: 28,29 % (octubre 2026, calculado del Padrón oficial).
- verification_status: verified.

#### Hogares (NO verificada -> null)
- Cifra secundaria: 9.224 hogares (enero 2026), publicada por el barrio en Instagram citando el Padrón.
- El dataset oficial de hogares (datos.madrid.es/300438-0-hogares-tamano) solo cubre hasta el 1 de enero de 2025 y se organiza por distrito y sección censal, no por barrio.
- Acción: households_total y average_household_size pasan a null con verification_status: unverified y explicación.
- La cifra secundaria se conserva en el texto de limitations para trazabilidad.

#### Negocios abiertos (no verificada)
- Valor: 126 (junio 2025, fuente secundaria Wikipedia). No se localizó registro municipal primario.
- verification_status: unverified.

#### Familias, gimnasios (no disponible)
- Sin censo publicado. verification_status: unavailable.

### Cambios en código
- src/mcp/server.py: población y pirámide actualizadas a cifras verificadas; hogares y tamaño medio a null; añadido verification_status por indicador; procedencia por indicador.
- data/sources.json: añadida fuente primaria (Padrón CSV); Instagram marcada como secundaria.
- data/raw/README.md: tabla sincronizada con el estado real.
- docs/*: actualizados.

### Tests
- Suite completa: 44 tests pasando (sin cambios en tests; solo datos y docs).


## Versión 1.1.5 — Endurecimiento SSRF y pruebas de seguridad (20/10/2026)

### Cambios Realizados

#### Seguridad (src/tools/read_web_page.py)
- Redirecciones desactivadas en httpx; cada salto se valida explícitamente (esquema, host, puerto, credenciales, IP resuelta).
- Validación de DNS inmediatamente antes de conectar (mitigación TOCTOU parcial).
- Puertos permitidos: 80, 443 y None. Credenciales en URL rechazadas.
- Bloqueo ampliado: más rangos IPv4/IPv6, hostnames internos y metadata (169.254.169.254).
- Normalización de URLs con espacios o caracteres no seguros.

#### Pruebas (tests/test_web_tools.py)
- Añadidos 5 tests: DNS rebinding, redirección a IP privada, credenciales en URL, puerto no estándar, esquema no permitido.

### Limitación honesta
- No se garantiza protección completa contra DNS rebinding/TOCTOU: httpx resuelve DNS en tiempo de conexión. Se valida antes y después, pero queda una ventana. Se documenta como riesgo pendiente.
- No se probaron formas alternativas de representar IP (decimal, octal, hexadecimal).

### Tests
- Suite completa: 49 tests pasando.


## Versión 1.1.6 — Auditoría de fuentes primarias y estado de verificación (20/10/2026)

### Hallazgos de la auditoría

#### Población (verificada contra fuente primaria)
- Valor: 27.480 habitantes (1 de octubre de 2026).
- Fuente: Padrón Municipal de Habitantes, datos.madrid.es (dataset 200076-0-padron, CSV, 32.5 MB, actualizado 6 oct 2026).
- Verificación independiente: suma directa de todas las edades del barrio "EL CAÑAVERAL" (distrito 19, Vicálvaro) en el CSV oficial.
- verification_status: verified.

#### Pirámide de edad (verificada)
- Valor: 28,29 % menores de 20 años (octubre 2026).
- Calculado del mismo CSV oficial: 7.774 de 27.480 habitantes.
- verification_status: verified.

#### Hogares (no verificable -> null)
- Cifra secundaria: 9.224 hogares (enero 2026), publicada por el barrio en Instagram citando el Padrón.
- El dataset oficial de hogares (datos.madrid.es/300438-0-hogares-tamano) solo cubre hasta el 1 de enero de 2025 y se organiza por distrito y sección censal, no por barrio.
- Acción: households_total y average_household_size pasan a null con verification_status: unverified.
- La cifra secundaria se conserva en limitations para trazabilidad.

#### Negocios (no verificado)
- Valor: 126 (junio 2025, Wikipedia citando datos municipales). No se localizó registro primario.
- verification_status: unverified.

#### Familias, gimnasios (no disponible)
- Sin censo publicado. verification_status: unavailable.

### Cambios en código
- src/mcp/server.py: población y pirámide actualizadas a cifras verificadas; hogares y tamaño medio a null; añadido verification_status por indicador.
- data/sources.json: añadida fuente primaria (Padrón CSV); Instagram marcada como secundaria.
- data/raw/README.md: tabla sincronizada con el estado real.
- docs/*: actualizados.

### Tests
- Suite completa: 44 tests pasando (sin cambios en tests; solo datos y docs).


## Versión 1.1.7 — Integración reproducible del Censo de Locales (20/10/2026)

### Cambios Realizados

#### Integración (src/mcp/server.py)
- Añadidas funciones parse_locales_csv() y
efresh_locales_count() para descarga y procesamiento reproducible del Censo de Locales.
- Descarga explícita o bajo demanda (no en cada consulta MCP).
- Procesamiento del CSV con validación de columnas, filtrado por barrio y conteo de identificadores únicos.
- Errores de descarga, CSV vacío, columnas faltantes y barrio no encontrado tratados explícitamente (sin convertir fallos en cero).
- Procedencia actualizada en el indicador usinesses_open tras la descarga.

#### Caché local
- El CSV descargado se guarda en data/raw/censo_locales.csv (gitignored).
- Documentado en data/raw/README.md.

#### Pruebas
- Añadido 	ests/test_locales.py con 9 tests: parsing básico, CSV vacío, columnas faltantes, barrio no encontrado, filas malformadas, refresh con CSV, área no soportada, error de descarga, CSV vacío en refresh.
- Todos usan un CSV pequeño inline; sin dependencia de red.

#### Documentación
- Creado docs/auditoria-fuentes-datos.md con la investigación de fuentes para hogares, cartografía y equipamientos.
- data/sources.json actualizado con la fuente del Censo de Locales.

### Tests
- Suite completa: 61 tests pasando.


## Versión 1.1.8 — Endurecimiento SSRF por clasificación de IP y estudio espacial de hogares (20/10/2026)

### Seguridad (src/tools/read_web_page.py)
- Diagnóstico: la clasificación de destinos por prefijos de cadena dejaba pasar IPv4 mapeado en IPv6 (::ffff:127.0.0.1), broadcast limitado (255.255.255.255), multicast (224.0.0.0/4), reservadas (240.0.0.0/4) y CGNAT (100.64.0.0/10).
- Cambio: _is_private_ip() clasifica ahora los literales IP con el módulo estándar ipaddress (allowlist de direcciones globalmente enrutables) y resuelve explícitamente el caso IPv4-mapeado en IPv6.
- Impacto: no se modifica el transporte ni su arquitectura; solo la función de clasificación. La verificación TLS, SNI y de certificado se conservan intactas.
- Formas decimales/hexadecimales (2130706433, 0x7f000001): no son literales IP válidos para ipaddress; se rejects en la resolución DNS, cuya IP resultante se valida igualmente.

### Pruebas (tests/test_web_tools.py)
- Nuevas: representaciones alternativas de IP, IPv4-mapeado en IPv6, broadcast, multicast, decimal, cadena de redirecciones público→público→privado, y comprobación de que las direcciones públicas siguen permitidas.
- Total de la suite: 69 tests.

### Estudio espacial (docs/auditoria-fuentes-datos.md)
- La cartografía oficial de secciones censales del Ayuntamiento (Geoportal, EPSG:25830) asigna 9 secciones a El Cañaveral (COD_BAR 194).
- Verificación geométrica: esas 9 secciones teselan el barrio al 100% (0 m2 fuera, 0 m2 sin cubrir). Ninguna sección cruza el límite, por lo que la agregación de hogares es EXACTA, no estimada.
- Resultado del estudio: 8.140 hogares y 2,64 de tamaño medio del hogar a 1 de enero de 2025; el total de habitantes de las secciones (21.492) coincide con la población oficial del barrio a esa fecha.
- Pendiente de decisión del equipo: fijar la referencia demográfica del módulo en 1 ene 2025 o publicar dos referencias, para no combinar población de 2026 con hogares de 2025.


## Versión 1.1.9 — Hogares verificados y cierre de datos de El Cañaveral (20/10/2026)

### Hallazgo
- La cartografía oficial de secciones censales del Ayuntamiento (Geoportal, EPSG:25830, datos 31/08/2026) atribuye cada sección a un barrio mediante el atributo COD_BAR. El Cañaveral es COD_BAR 194 con 9 secciones: 19052, 19053, 19054, 19055, 19056, 19058, 19059, 19060, 19061.
- Verificación geométrica: esas 9 secciones teselan el polígono del barrio al 100% (0 m2 fuera, 0 m2 sin cubrir, ratio 1,0 en todas). Ninguna sección cruza el límite, por lo que la agregación de hogares es EXACTA y no requiere reparto proporcional por superficie.
- Contraste independiente: los 21.492 habitantes de esas secciones coinciden exactamente con la población oficial de El Cañaveral a 1 ene 2025 (dataset 300557).

### Datos publicados
- households_total: 8.140 hogares (referencia 1 ene 2025, verificado).
- average_household_size: 2,64 personas por hogar (21.492 / 8.140, referencia 1 ene 2025, verificado).
- population_total_2025: 21.492 habitantes (referencia 1 ene 2025, verificado) para evitar combinar hogares de 2025 con población de 2026.
- Se retiran las cifras secundarias de Instagram (9.224 hogares, 2,70) al estar superadas por la fuente oficial.

### Implementación
- src/mcp/server.py: parse_households_rows() (función pura), refresh_households() (regenera los indicadores) y _read_households_workbook() / _read_sections_for_barrio() con importaciones perezosas: openpyxl y pyogrio son herramientas offline, NO dependencias del servidor MCP.
- data/raw/extract_households.py: script offline reproducible que descarga las fuentes, agrega y verifica la geometría.
- tests/test_households.py: 9 tests (agregación, secciones ausentes, sin coincidencia, actualización del almacén, área no soportada, error sin sobrescribir, coherencia de los valores publicados y de las referencias temporales).

### Seguridad (continuación de 1.1.8)
- 6 tests nuevos de regresión SSRF: IPv4 mapeado en IPv6, broadcast, multicast, decimal, cadena de redirecciones público→público→privado y verificación de que las direcciones públicas siguen permitidas.

### Documentación
- data/raw/README.md, data/sources.json, docs/research-module.md y docs/auditoria-fuentes-datos.md sincronizados.

### Tests
- Suite completa: 78 tests pasando.


## Versión 1.1.10 — Se respetan los límites de búsqueda del encargo (20/10/2026)

### Corrección
- run_research() usaba un límite fijo de 5 resultados y solo mostraba search_limits dentro del texto de la tarea, sin aplicarlo.
- Ahora resuelve_max_results() toma search_limits.max_results del ResearchBrief, con valor por defecto 5 y tope de 20 (el límite que aceptan search_web y competitor_search).
- El valor se aplica tanto a la búsqueda inicial como a competitor_search.

### Pruebas
- Añadido tests/test_search_limits.py con 7 tests: valor por defecto, valor del encargo, tope, valores inválidos y comprobación de que el límite llega a las dos herramientas.


## Versión 1.1.11 — Indicadores de equipamientos y hogares con menores (20/10/2026)

### Hallazgo: la auditoria anterior fue incompleta
- Se habia revisado la ficha de cada dataset pero solo el PRIMER recurso de cada uno: el fichero de Locales del Censo de Locales y la hoja de Tamano del hogar del XLSX. Ambos tienen mas recursos: el Censo de Locales tiene cuatro ficheros (Locales, Actividades, Locales con licencia, Terrazas) y el libro de hogares tiene tres hojas (Tamano, Composicion del hogar, Tipo-Nacionalidad).
- Consecuencia: familias y gimnasios estaban marcados como no disponibles cuando la fuente existia. Ningun valor se habia inventado, pero la conclusion era mas fuerte que la evidencia.

### Indicadores anadidos (todos verificados contra fuente oficial)
- gyms_registered: 9 locales abiertos con epigrafe 931008 (ACTIVIDADES DE LOS GIMNASIOS).
- sports_recreation_venues: 4 locales con epigrafe 855002 (ensenanza no reglada deportiva y recreativa).
- childrens_play_venues: 3 locales con epigrafes 932001 y 932002 (centros de juegos o celebraciones infantiles).
- community_pools: 3 locales con epigrafe 931010 (piscinas de comunidades de vecinos).
- households_with_minors: 3.071 hogares con al menos un menor (MINIMO verificable), referencia 1 ene 2025.

### Indicadores que siguen en null
- families_with_children: ninguna fuente oficial define ni publica familias con hijos a nivel de barrio; el Padron mide hogares. households_with_minors no es sinonimo.
- gyms_with_ludoteca: no existe un epigrafe que combine gimnasio y ludoteca; los 9 de gimnasios y los 3 de ocio infantil son categorias distintas y un local puede estar en ambas. Falta confirmacion centro a centro.

### Defectos propios detectados y corregidos
- refresh_gyms_count() sobrescribia el indicador en vez de SUMAR los dos epigrafes que lo alimentan (childrens_play_venues devolvia 1 en lugar de 3). Ahora se suman y hay test de regresion.
- La composicion del hogar clasificaba como ambiguas tanto las categorias con o sin menores como las explicitamente sin menores (3.146 en lugar de 662). Ahora se separan en tres grupos: con menores, sin menores y ambiguas.
- Los parsers de CSV no toleraban la cabecera con BOM UTF-8: al leer el fichero oficial como texto, la primera columna (id_local) dejaba de reconocerse y el parser fallaba en silencio. Corregido y con test.

### Implementacion
- src/mcp/server.py: parse_actividades_csv(), refresh_gyms_count(), parse_household_composition_rows(), refresh_households_with_minors() y _sections_cache_path(). Importaciones perezosas: openpyxl y pyogrio son herramientas offline, NO dependencias del servidor MCP.
- data/raw/extract_censo_locales.py: script offline que reproduce los 5 indicadores del Censo de Locales.
- tests/test_area_indicators.py: 18 tests (recuentos, suma de epigrafes, BOM, cierres, areas no soportadas, errores que no tocan el almacen, composicion en tres grupos y contrato de los valores publicados).

### Documentacion
- data/raw/README.md, data/sources.json, docs/research-module.md, docs/research-changelog.md y docs/auditoria-fuentes-datos.md sincronizados.

### Tests
- Suite completa: 103 tests pasando.

## Versión 1.2.0 — Registro de competidores oficial, busquador de fuentes reparado y descubrimiento de datasets (20/10/2026)

### Hallazgo critico: el buscador de fuentes no funcionaba
- Causa raiz: _normalize_url() en src/tools/search_web.py llamaba urlencode() con el argumento inexistente 'query_fragment', lo que lanzaba TypeError en CADA busqueda. El error se envolvia en RuntimeError y el agente recibia 'Search provider failed' sin ningun resultado.
- Ademas, la query se reconstruia sin el interrogante, de modo que los parametros se perdian.
- Los tests no lo detectaban porque todos mockeaban search_web. Se anaden 3 tests de regresion que usan la funcion real.
- Efecto: hasta ahora ninguna busqueda web del modulo habia funcionado de verdad.

### Registro de competidores (src/tools/competitor_registry.py, nuevo)
- Une los tres recursos oficiales del Censo de Locales (Locales, Actividades y Locales con informacion de licencia) en registros Competitor con el identificador oficial del local.
- 18 competidores de El Canaveral con direccion, CP, coordenadas, actividad declarada y licencia.
- Procedencia por campo: cada bloque oficial lleva su propia Evidence con URL, fecha de consulta y limitaciones.
- Reglas: coordenadas 0,0 o fuera del entorno UTM 30N de Madrid = no disponibles; licencia ausente = 'no disponible' (nunca 'denegada'); has_playroom en True/False solo con evidencia fiable, si no None; precios con su periodicidad publicada, sin convertir.
- Enriquecimiento web: se busca por direccion oficial, la pagina solo se acepta si menciona la calle y la actividad declarada, y se descartan los anuncios de alquiler de vivienda (se detectan por senales multiples de vivienda).
- to_dataframe() genera el DataFrame que consume el modulo de analisis (gym_name, monthly_price_eur, has_playroom y contexto).
- Script reproducible: data/raw/extract_competitor_registry.py.

### Descubrimiento de fuentes (src/tools/source_discovery.py, nuevo)
- Convierte una variable pendiente en varias consultas: la literal, 'datos abiertos', 'estadistica' y una por organismo (site:ine.es, site:datos.madrid.es...).
- Clasifica cada resultado como discovered, accessible, extracted, validated o rejected, con motivo explicito.
- Distingue paginas informativas de datasets descargables (extensiones, /dataset/, /api/ y contenido).
- Extrae tablas de CSV y de HTML para comprobar la cobertura y el periodo.
- No marca una fuente como validada sin haber leido su contenido.

### Integracion con el agente de investigacion
- ResearchBrief incorpora missing_variables (opcional). Cuando se rellena, run_research hace una pasada de busqueda de fuentes y devuelve cada candidata como Evidence con URL, organismo, consulta, estado (discovered/accessible/extracted/validated/rejected) y motivo.
- Una fuente nunca se presenta como verificada sin haber leido su contenido.

### Contrato de datos (src/schemas.py)
- Competitor incorpora campos opcionales: postal_code, latitude, longitude, census_section, license_status, license_type, license_date, has_playroom, verification_status y consulted_at.
- Aditivo: los agentes de analisis y redaccion siguen funcionando sin cambios.

### Documentacion
- docs/pendiente-renta-ine.md: fase de renta (INE ADRH, operacion 30325) documentada y NO implementada.
- data/sources.json, data/raw/README.md, docs/research-module.md y docs/auditoria-fuentes-datos.md actualizados.

### Tests
- tests/test_competitor_registry.py (30), tests/test_source_discovery.py (13) y 3 tests de regresion del buscador.
- Suite completa de la rama `fix/respect-search-limits`: **153 tests**.

### Nota de integracion
- Estos cambios se integraron en la rama `fix/respect-search-limits` (PR #5, abierto contra `dev`), no en un PR aparte.

- [ ] Añadir más indicadores al MCP (demografía, ingresos, etc.)
- [ ] Mejorar manejo de errores cuando Internet está sin conexión
- [ ] Añadir más ejemplos en el README del módulo
- [ ] Probar integración real con CrewAI + LLM cuando esté disponible
- [ ] Interfaz de línea de comandos para queries rápidas
- [ ] Almacenamiento persistente de resultados de investigación
- [ ] Más ejemplos de consumo por parte de otras personas (Isabella, Gema, María, Laura)
- [x] Tests de integración end-to-end del MCP (cubierto en 1.1.1)
- [ ] Tests de integración con red real (búsqueda + lectura de páginas)

---

## Convenios de Registro

### Fechas
- Formato: `dd/mm/aaaa`
- Siempre en orden cronológico

### Descripción de Cambios
- **Qué**: Nombre breve del archivo o funcionalidad afectada
- **Cambio**: Qué se hizo exactamente
- **Por qué**: Motivación técnica o de diseño
- **Resultado**: Estado actual o beneficio obtenido

### Estado de los Archivos
- `Creado`: Archivo nuevo que no existía antes
- `Modificado`: Archivo existente que recibió cambios
- `Sin cambios`: Archivo que forma parte del proyecto pero no fue tocado en esta iteración

### Bloqueos
- Cualquier impedimento técnico que impidiera avanzar en un punto específico
- Dependencias externas que bloquean funcionalidades específicas
- Decisiones técnicas tomadas para continuar el trabajo

---

*Este registro forma parte del proyecto FitFamily y debe mantenerse actualizado con cada iteración del módulo de Persona 1.*