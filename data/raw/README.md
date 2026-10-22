# Datos locales del módulo de investigación FitFamily

## ¿Qué datos utiliza el MCP?

El servidor MCP (`src/mcp/server.py`) publica una herramienta llamada `get_area_statistics` que consulta un almacén de datos local (`_STATISTICS_DATA`). A fecha de la última revisión, los indicadores disponibles son:

| Indicador | Valor | Período | Fuente |
|---|---|---|---|
| `population_total` | 27 480 hab. | 1 oct 2026 | Padrón Municipal (datos.madrid.es, CSV oficial) |
| `population_under_20_share` | 28,29 % | 1 oct 2026 | Padrón Municipal (calculado de datos.madrid.es) |
| `population_total_2025` | 21 492 hab. | 1 ene 2025 | Fichero oficial de hogares (misma referencia que `households_total`) |
| `households_total` | 8 140 hogares | 1 ene 2025 | Fichero oficial de hogares, agregado sobre las 9 secciones censales del barrio |
| `average_household_size` | 2,64 pers./hogar | 1 ene 2025 | Derivado de los mismos datos (21.492 / 8.140) |
| `households_with_minors` | 3 071 hogares | 1 ene 2025 | Hoja de composición del hogar (mínimo verificable) |
| `businesses_open` | 234 locales | descarga 20 oct 2026 | Censo de Locales, fichero de Locales |
| `gyms_registered` | 9 locales | descarga 20 oct 2026 | Censo de Locales, fichero de Actividades, epígrafe 931008 |
| `sports_recreation_venues` | 4 locales | descarga 20 oct 2026 | Censo de Locales, epígrafe 855002 |
| `childrens_play_venues` | 3 locales | descarga 20 oct 2026 | Censo de Locales, epígrafes 932001 y 932002 |
| `community_pools` | 3 locales | descarga 20 oct 2026 | Censo de Locales, epígrafe 931010 |
| `families_with_children` | `null` | — | Ninguna fuente oficial define "familias con hijos" a nivel de barrio |
| `gyms_with_ludoteca` | `null` | — | Ningún epígrafe combina gimnasio y ludoteca; confirmar centro a centro |

⚠️ **Las referencias temporales no son intercambiables.** Los indicadores de hogares y `population_total_2025` son de **1 ene 2025**; `population_total` y `population_under_20_share` son de **oct 2026**. Para calcular ratios coherentes hay que usar `population_total_2025` (o el tamaño medio ya calculado), nunca `population_total`.

## De dónde proceden

Todos los valores publicados proceden de **fuentes primarias oficiales** (Ayuntamiento de Madrid), ninguna de fuentes secundarias:

- **Padrón Municipal de Habitantes** (datos.madrid.es/200076-0-padron): población por edad. Mensual, ficha actualizada el 6 de octubre de 2026.
- **Hogares por tamaño y sección censal** (datos.madrid.es/300438-0-hogares-tamano): hogares, tamaño medio y población a 1 ene 2025.
- **Límites administrativos / secciones censales** (Geoportal del Ayuntamiento): atribución oficial sección→barrio (`COD_BAR`) y verificación geométrica, EPSG:25830, fecha de datos 31/08/2026.
- **Censo de Locales y Actividades** (datos.madrid.es/200085-0-censo-locales): locales abiertos, actualización diaria.
- **Población por distrito y barrio a 1 de enero** (datos.madrid.es/300557): contraste independiente de la población.

El detalle completo por fuente está en `data/sources.json`.

## Cómo preparar los datos sin perder trazabilidad

1. Crear un archivo JSON o CSV con los indicadores numéricos.
2. Para cada valor, registrar:
   - El origen exacto (enlace, fecha de consulta, número de expediente si corresponde).
   - El período al que se refiere los datos.
   - El ámbito geográfico exacto (barrio, distrito, códigos postales).
3. Colocar el archivo en `data/raw/` o cargarlo en la variable `_STATISTICS_DATA` del servidor MCP.
4. Actualizar los `limitations` de cada indicador para reflejar la fuente y el período.

## Limitaciones geográficas y temporales

- Los datos municipales pueden tener lag de actualización de 1-2 años (los hogares oficiales llegan a ene 2025).
- Los datos de búsqueda web son volátiles y cambian con el tiempo.
- El ámbito geográfico "El Cañaveral" puede incluir o excluir desarrollos urbanos nuevos según la fuente.
- Una cifra en `null` es una respuesta válida: significa "no disponible en las fuentes consultadas", no un error del módulo.

## Cómo actualizar los datos

1. Consultar la fuente oficial solicitada.
2. Ejecutar el script de extracción correspondiente (ver más abajo).
3. Actualizar el valor y el campo `limitations` en `_STATISTICS_DATA` (`src/mcp/server.py`).
4. Actualizar `data/sources.json` con la nueva fuente.
5. Documentar el cambio en este archivo y en `docs/research-changelog.md`.

## Integración reproducible del Censo de Locales

Los indicadores del Censo de Locales (`businesses_open`, `gyms_registered`, `sports_recreation_venues`, `childrens_play_venues`, `community_pools`) se actualizan de forma automatizada:

```python
from src.mcp.server import refresh_locales_count, refresh_gyms_count

print(refresh_locales_count("el-cañaveral"))   # 234 locales abiertos
print(refresh_gyms_count("el-cañaveral"))      # equipamientos por epígrafe
```

- **Funciones puras (testeables sin red):** `parse_locales_csv(csv_text, barrio_name)` y `parse_actividades_csv(csv_text, barrio_name)`.
- **Descarga explícita o bajo demanda:** la descarga ocurre solo al llamar a las funciones, nunca en cada consulta MCP.
- **Método de cálculo:** filtrar `desc_barrio_local == "El Cañaveral"` y `desc_situacion_local == "Abierto"`, y contar `id_local` únicos.
- **Ficheros oficiales:**
  - Locales (85-89 MB): https://datos.madrid.es/dataset/200085-0-censo-locales/resource/200085-1-censo-locales/download/200085-1-censo-locales.csv
  - Actividades (119-125 MB): https://datos.madrid.es/dataset/200085-0-censo-locales/resource/200085-5-censo-locales/download/200085-5-censo-locales.csv
- **Epígrafes usados:** 931008 (gimnasios), 855002 (enseñanza no reglada deportiva y recreativa), 932001 y 932002 (juegos o celebraciones infantiles), 931010 (piscinas de comunidades de vecinos).
- **Cobertura:** el fichero de Actividades recoge 229 de los 234 locales abiertos del fichero de Locales; 5 no tienen actividad económica declarada.
- **Script offline reproducible:** `python data/raw/extract_censo_locales.py` (reproduce los cinco indicadores).
- **Caché local:** las descargas se guardan en `data/raw/cache/` y en `data/raw/censo_locales.csv` (ambos ignorados por git).
- **Errores:** descarga fallida, CSV vacío, columnas cambiadas o barrio no encontrado devuelven `status: "error"` y **no** modifican el valor almacenado. Un fallo nunca se convierte en cero.
- **Cabecera con BOM:** los parsers toleran la cabecera con BOM UTF-8 (el fichero oficial la incluye).
- **Áreas soportadas:** actualmente solo El Cañaveral. La estructura admite ampliar el mapa `_SUPPORTED_LOCALES_AREAS` a otros barrios de Madrid.

## Extracción reproducible de los hogares

Script offline: **`data/raw/extract_households.py`**. No forma parte del arranque del servidor MCP; es una herramienta de preparación de datos.

```bash
python data/raw/extract_households.py --verify-geometry
```

- **Fuentes:** XLSX 2025 de hogares (datos.madrid.es/300438) + cartografía de secciones censales (Geoportal).
- **Método:** la cartografía oficial atribuye cada sección censal a un barrio (`COD_BAR`); se suman los hogares de las 9 secciones de El Cañaveral (19052, 19053, 19054, 19055, 19056, 19058, 19059, 19060, 19061).
- **La agregación es exacta, no estimada:** las 9 secciones teselan el polígono del barrio al 100 % (0 m² fuera, 0 m² sin cubrir, ratio de intersección 1,0 en todas). Ninguna sección cruza el límite, por lo que **no se reparte por superficie**.
- **Contraste independiente:** los 21.492 habitantes de esas secciones coinciden exactamente con la población oficial del barrio a 1 ene 2025 del dataset "Población por distrito y barrio a 1 de enero".
- **Resultado:** 8.140 hogares, 2,6403 personas por hogar, 21.492 habitantes.
- **Hogares con menores (mínimo verificable):** 3.071, de la hoja "Composición del hogar" del mismo fichero. Se cuentan solo las categorías donde la presencia de menores es explícita; las "con o sin menores" (662 hogares) no se pueden atribuir y las "sin menores" (2.484) se descartan.
- **Caché:** las descargas se guardan en `data/raw/cache/` (ignorado por git).
- **Dependencias:** `openpyxl` y `pyogrio` (ya instaladas). **No** son dependencias del servidor MCP: solo de esta herramienta offline.
- **En el servidor MCP:** `refresh_households("el-cañaveral")` regenera los indicadores y `parse_households_rows(rows, section_codes)` es la función pura testeable sin red.

## Registro de competidores respaldado por el Censo de Locales

Script offline: **`data/raw/extract_competitor_registry.py`**. Une los tres recursos
oficiales del Censo de Locales y, opcionalmente, enriquece cada competidor con los
datos publicados en su propia web (precio y evidencia de ludoteca).

```bash
python data/raw/extract_competitor_registry.py            # con enriquecimiento web
python data/raw/extract_competitor_registry.py --no-web   # solo datos oficiales
```

- **Módulo:** `src/tools/competitor_registry.py`.
- **Fuentes:** Locales (identificador, dirección, CP, coordenadas), Actividades
  (epígrafes) y Locales con información de licencia (referencia, tipo, situación y fecha).
- **Salidas:** `data/processed/competitor_registry.json` (con evidencias) y
  `data/processed/competitor_registry.csv` (DataFrame para el módulo de análisis).
- **Reglas aplicadas:** identificador oficial conservado; coordenadas `0,0` o fuera del
  entorno UTM 30N de Madrid marcadas como no disponibles; licencia ausente = "no
  disponible" (nunca "denegada"); `has_playroom` en `True`/`False` solo con evidencia
  fiable y `None` (desconocido) si la web no lo menciona; los precios conservan la
  periodicidad publicada sin convertirla.
- **Ficheros brutos:** se guardan en `data/raw/cache/` (ignorado por git) y no se
  versionan.

## Trazabilidad

Cada indicador expone `value`, `unit`, `reference_period`, `source_url`, `consulted_at`, `verification_status` (`verified` / `unverified` / `unavailable`) y `limitations`. Los valores no disponibles se devuelven como `null` y nunca como cero.
