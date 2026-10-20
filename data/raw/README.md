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
| `businesses_open` | 234 locales | descarga 20 oct 2026 | Censo de Locales (datos.madrid.es, actualización diaria) |
| `families_with_children` | `null` | — | Sin censo directo; referencia indirecta: 28,29 % de la población es menor de 20 años |
| `gyms_registered` | `null` | — | Sin censo municipal publicado; conteo manual no verificado |
| `gyms_with_ludoteca` | `null` | — | Sin censo municipal; ningún centro localizado publica ludoteca de forma verificable |

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

El indicador `businesses_open` se puede actualizar de forma automatizada:

```python
from src.mcp.server import refresh_locales_count

resultado = refresh_locales_count("el-cañaveral")
print(resultado["status"], resultado.get("count"), resultado.get("consulted_at"))
```

- **Función pura (testeable sin red):** `parse_locales_csv(csv_text, barrio_name)`.
- **Descarga explícita o bajo demanda:** la descarga ocurre solo al llamar a `refresh_locales_count()`, nunca en cada consulta MCP.
- **Método de cálculo:** filtrar `desc_barrio_local == "El Cañaveral"` y `desc_situacion_local == "Abierto"`, y contar `id_local` únicos.
- **Recurso:** https://datos.madrid.es/dataset/200085-0-censo-locales/resource/200085-1-censo-locales/download/200085-1-censo-locales.csv (85.2 MB, actualizado diariamente, CC BY 4.0).
- **Caché local:** el CSV descargado se guarda en `data/raw/censo_locales.csv` (ignorado por git).
- **Errores:** descarga fallida, CSV vacío, columnas cambiadas o barrio no encontrado devuelven `status: "error"` y **no** modifican el valor almacenado. Un fallo nunca se convierte en cero.
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
- **Caché:** las descargas se guardan en `data/raw/cache/` (ignorado por git).
- **Dependencias:** `openpyxl` y `pyogrio` (ya instaladas). **No** son dependencias del servidor MCP: solo de esta herramienta offline.
- **En el servidor MCP:** `refresh_households("el-cañaveral")` regenera los indicadores y `parse_households_rows(rows, section_codes)` es la función pura testeable sin red.

## Trazabilidad

Cada indicador expone `value`, `unit`, `reference_period`, `source_url`, `consulted_at`, `verification_status` (`verified` / `unverified` / `unavailable`) y `limitations`. Los valores no disponibles se devuelven como `null` y nunca como cero.
