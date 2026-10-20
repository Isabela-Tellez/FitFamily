# Datos locales del módulo de investigación FitFamily

## ¿Qué datos utiliza el MCP?

El servidor MCP (`src/mcp/server.py`) publica una herramienta llamada `get_area_statistics` que consulta un almacén de datos local (`_STATISTICS_DATA`). A fecha de la última revisión, los indicadores disponibles son:

| Indicador | Valor | Período | Fuente |
|---|---|---|---|
| `population_total` | 27 014 hab. | agosto 2026 | Padrón Municipal (Ayuntamiento de Madrid), vía Wikipedia "El Cañaveral" (ed. 6 sep 2026) |
| `households_total` | 9 224 hogares | enero 2026 | Padrón Municipal, publicado por el barrio en Instagram |
| `average_household_size` | 2,70 pers./hogar | enero 2026 | Padrón Municipal, publicado por el barrio en Instagram |
| `population_under_20_share` | 25,46 % | 2021 | Pirámide de población (Wikipedia, citando INE) |
| `businesses_open` | 126 negocios | junio 2025 | Wikipedia "El Cañaveral" (citando datos municipales) |
| `families_with_children` | `null` | — | Sin censo directo; referencia indirecta: 25,46 % de la población es menor de 20 años |
| `gyms_registered` | `null` | — | Sin censo municipal publicado; conteo manual no verificado |
| `gyms_with_ludoteca` | `null` | — | Sin censo municipal; ningún centro localizado publica ludoteca de forma verificable |

## De dónde proceden

Los datos combinan fuentes oficiales y fuentes secundarias documentadas:

- **Ayuntamiento de Madrid - Padrón Municipal de Habitantes** (datos.madrid.es): población y hogares. Se actualiza mensualmente y cubre distritos, barrios y secciones censales. La ficha consultada se actualizó el 6 de octubre de 2026.
- **Wikipedia "El Cañaveral"** (ed. 6 sep 2026): cita INE/Padrón y datos municipales para población, negocios y pirámide de edad.
- **Nuevo Sureste** (publicación local): hogares y evolución demográfica del barrio.

Estas fuentes secundarias respaldan las cifras comunicadas, pero no sustituyen la verificación directa del registro municipal original.

## Cómo preparar los datos sin perder trazabilidad

1. Crear un archivo JSON o CSV con los indicadores numéricos.
2. Para cada valor, registrar:
   - El origen exacto (enlace, fecha de consulta, número de expediente si corresponde).
   - El período al que se refiere los datos.
   - El ámbito geográfico exacto (barrio, distrito, códigos postales).
3. Colocar el archivo en `data/raw/` o cargarlo en la variable `_STATISTICS_DATA` del servidor MCP.
4. Actualizar los `limitations` de cada indicador para reflejar la fuente y el período.

## Limitaciones geográficas y temporales

- Los datos municipales pueden tener lag de actualización de 1-2 años.
- Los datos de búsqueda web son volátiles y cambian con el tiempo.
- El ámbito geográfico "El Cañaveral" puede incluir o excluir desarrollos urbanos nuevos según la fuente.
- Una cifra en `null` es una respuesta válida: significa "no disponible en las fuentes consultadas", no un error del módulo.

## Cómo actualizar los datos

1. Consultar la fuente oficial solicitada.
2. Añadir el nuevo valor al diccionario `_STATISTICS_DATA` en `src/mcp/server.py`.
3. Actualizar el campo `limitations` con la fuente, el período y la fecha de consulta.
4. Actualizar `data/sources.json` con la nueva fuente.
5. Documentar el cambio en este archivo y en `docs/research-changelog.md`.
