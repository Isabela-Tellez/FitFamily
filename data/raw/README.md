# Datos locales del módulo de investigación FitFamily

## ¿Qué datos utiliza el MCP?

El servidor MCP (`src/mcp/server.py`) publica una herramienta llamada `get_area_statistics` que consulta un almacén de datos local. Actualmente, los indicadores disponibles son:

- `population_total`: Población total del área. *Valor: no disponible - dato pendiente de consultar fuentes municipales.*
- `families_with_children`: Número de familias con niños. *Valor: no disponible - dato pendiente de consultar fuentes municipales.*
- `gyms_registered`: Centros deportivos registrados en el área. *Valor: no disponible - dato pendiente de consultar fuentes municipales.*
- `gyms_with_ludoteca`: Centros deportivos con ludoteca. *Valor: no disponible - dato pendiente de consultar fuentes municipales.*

## De dónde proceden

Los datos están pensados para poblarse con fuentes oficiales como:
- Ayuntamiento de Madrid
- Comunidad de Madrid
- INE (Instituto Nacional de Estadística)
- Cámaras de comercio locales

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
- Los datos de búsqueda web son volatiles y cambian con el tiempo.
- El ámbito geográfico "El Cañaveral" puede incluir o excluir desarrollos urbanos nuevos según la fuente.

## Cómo actualizar los datos

1. Consultar la fuente oficial solicitada.
2. Añadir el nuevo valor al diccionario `_STATISTICS_DATA` en `src/mcp/server.py`.
3. Actualizar el campo `limitations` con la fuente y fecha de consulta.
4. Documentar el cambio en este archivo.