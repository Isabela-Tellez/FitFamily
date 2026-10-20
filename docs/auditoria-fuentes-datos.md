# Auditoría de fuentes de datos — Módulo de investigación (Persona 1)

## 1. Resumen ejecutivo

| Indicador | Estado | Valor | Fuente |
|---|---|---|---|
| Población total | Verificado | 27.480 (1 oct 2026) | Padrón Municipal, CSV oficial |
| Menores de 20 años | Verificado | 28,29 % (1 oct 2026) | Padrón Municipal, calculado |
| Población a 1 ene 2025 | Verificado | 21.492 | Fichero oficial de hogares |
| **Hogares** | **Verificado** | **8.140 (1 ene 2025)** | Fichero oficial de hogares, suma exacta de las 9 secciones censales del barrio |
| **Tamaño medio del hogar** | **Verificado** | **2,64 (1 ene 2025)** | Derivado de los mismos datos |
| Locales abiertos | Verificado | 234 (20 oct 2026) | Censo de Locales, CSV oficial |
| Familias con hijos | No disponible | `null` | Sin fuente oficial a nivel de barrio |
| Gimnasios | No disponible | `null` | Sin censo a nivel de barrio |

**Hallazgo principal:** el cruce entre el fichero oficial de hogares y la cartografía oficial de secciones censales **no requiere estimación**. Las 9 secciones censales asignadas oficialmente a El Cañaveral **teselan el barrio al 100 %**, por lo que la suma es exacta.

**Estado de implementación:** los valores de hogares están publicados en el MCP (`households_total`, `average_household_size`, `population_total_2025`), con extracción reproducible en `data/raw/extract_households.py` y 9 tests de regresión.

## 2. Fuentes investigadas

### Población (verificada)
- **Fuente:** Padrón Municipal de Habitantes (datos.madrid.es/dataset/200076-0-padron)
- **Recurso:** CSV (32,5 MB), actualizado 6 oct 2026, cobertura hasta 30 sep 2026. Licencia CC BY 4.0.
- **Método:** suma directa de todas las edades del barrio "EL CAÑAVERAL" (distrito 19, Vicálvaro).
- **Resultado:** 27.480 hab. (oct 2026); 28,29 % < 20 años (7.774 de 27.480).
- **Contraste:** el dataset "Población por distrito y barrio a 1 de enero" (datos.madrid.es/300557) da 24.945 hab. a 1 ene 2026 y 21.492 a 1 ene 2025. Ambas son coherentes con el crecimiento del barrio.

### Hogares (verificable — ver §3)
- **Fuente:** datos.madrid.es/dataset/300438-0-hogares-tamano, recurso XLSX 2025.
- **Referencia:** Padrón Municipal revisado a **1 de enero de 2025**. Cobertura temporal del dataset: 1 ene 2009 – 1 ene 2025. Frecuencia anual. Licencia CC BY 4.0.
- **Granularidad:** distrito y sección censal. Hoja "Tamaño del hogar": columnas `Habitantes`, `Total Hogares`, `Tamaño medio del hogar` y distribución por tamaño (1 a 15+ personas). Los códigos de sección son enteros de 5 dígitos (p. ej. `19058`).
- **Limitación de vigencia:** el último dato oficial de hogares es de enero 2025, no de octubre 2026. Es la limitación real de este indicador, no la geografía.

### Cartografía oficial de secciones censales y barrios
- **Fuente:** Geoportal del Ayuntamiento de Madrid, "Límites administrativas actuales" (id `e251898e-4a9c-11eb-9104-dc4a3e8ce33b`).
- **Fecha de datos:** 31/08/2026. SRS: **EPSG:25830** (ETRS89 / UTM 30N). Secciones censales actualizadas en junio de 2022; barrios conforme al acuerdo del Pleno de 29/06/2021 (BOCM 12/07/2021).
- **Recursos descargados:** `Secciones_Censales.zip` (SHP), `Barrios.zip` (SHP) y sus versiones TopoJSON.
- **Atributos clave:** la capa de secciones trae `COD_DIS`, `NOM_DIS`, **`COD_BAR`**, `NOM_BAR`, `COD_SECCIO`, `AREA`. La capa de barrios trae `CODDIS`, `NOMDIS`, `COD_BAR`, `NOMBRE`, `AREA`.
- **Consecuencia decisiva:** existe una **atribución oficial sección→barrio** en la propia cartografía municipal, sin necesidad de inferencia espacial.

### Negocios (verificado)
- **Fuente:** Censo de Locales y Actividades (datos.madrid.es/dataset/200085-0-censo-locales), CSV 85,2 MB, actualización diaria, CC BY 4.0.
- **Método:** filtrar `desc_barrio_local == "El Cañaveral"` y `desc_situacion_local == "Abierto"`, contar `id_local` únicos.
- **Resultado:** 234 locales abiertos (298 filas totales del barrio; situaciones: Abierto, Cerrado, Baja Reunificación).
- **Limitación:** "locales" (premises) ≠ "negocios" (establecimientos); un local puede albergar varias actividades.

### Gimnasios e instalaciones deportivas (no verificado)
- **Censo de Instalaciones Deportivas (CSD):** a nivel municipal, no de barrio; sin dataset descargable localizado para Madrid.
- **INE — Directorio Central de Empresas:** empresas por municipio y CNAE, no por barrio.
- **Censo de Locales:** el fichero de "Actividades" (119,3 MB) incluye el epígrafe de actividad por local, pero no permite certificar "gimnasio con ludoteca" (actividad no desagregada de forma pública).
- **Conclusión:** no existe censo de gimnasios a nivel de barrio.

### Familias (no disponible)
- El Padrón Municipal no incluye la variable "familias con hijos".
- Referencia indirecta verificada: 28,29 % de la población < 20 años.

## 3. Estudio espacial: ¿se pueden calcular los hogares de El Cañaveral?

**Sí, y de forma exacta (no estimada).**

### Fuentes combinadas
1. `Secciones_Censales.zip` → 2.462 secciones, EPSG:25830.
2. `Barrios.zip` → 131 barrios, EPSG:25830.
3. `hogares_2025.xlsx` (dataset 300438) → datos por sección.

### Paso 1 — Atribución oficial
El shapefile de barrios identifica El Cañaveral como `COD_BAR = 194`, distrito 19 (Vicálvaro), superficie 10.567.690,6 m².

Las secciones con `COD_BAR = 194` son **9**:

| Sección | Área (m²) | Habitantes | Hogares | Tamaño medio |
|---|---|---|---|---|
| 19052 | 1.456.995,1 | 2.091 | 808 | 2,588 |
| 19053 | 317.290,6 | 2.414 | 874 | 2,759 |
| 19054 | 579.103,2 | 2.394 | 874 | 2,739 |
| 19055 | 1.073.354,2 | 2.766 | 1.130 | 2,448 |
| 19056 | 272.765,3 | 3.007 | 1.143 | 2,631 |
| 19058 | 244.945,8 | 1.793 | 806 | 2,225 |
| 19059 | 5.976.011,6 | 2.613 | 797 | 3,279 |
| 19060 | 457.172,3 | 2.470 | 942 | 2,622 |
| 19061 | 190.052,6 | 1.944 | 765 | 2,541 |
| **TOTAL** | **10.567.690,6** | **21.492** | **8.140** | **2,640** |

### Paso 2 — Verificación geométrica (no hay secciones que crucen el límite)
- Área del polígono de El Cañaveral: 10.567.690,6 m².
- Área de la unión de sus 9 secciones oficiales: 10.567.690,6 m².
- Intersección: 10.567.690,6 m² → **cobertura 100,0000 %**.
- Área de las secciones fuera del barrio: **0,0 m²**.
- Área del barrio no cubierta por esas secciones: **0,0 m²**.
- Ratio de intersección por sección: **1,0 en las 9** (todas completamente dentro).

**No hay ninguna sección que cruce el límite de El Cañaveral**, por lo que **no hace falta repartir hogares por superficie**. La suma es exacta y no introduce supuestos.

### Paso 3 — Contraste cruzado con una fuente independiente
- Suma de habitantes de las 9 secciones (21.492) **coincide exactamente** con la población oficial de El Cañaveral a 1 de enero de 2025 del dataset "Población por distrito y barrio a 1 de enero" (21.492; hombres 10.793 / mujeres 10.699).
- Contraste con el distrito: Vicálvaro tiene 95.233 hab. y 35.256 hogares (2,701 de media). El Cañaveral representa el 22,6 % de los habitantes y el 23,1 % de los hogares del distrito, coherente con su peso territorial (10,57 de 45,04 km² ≈ 23 %).

### Resultado
- `households_total` = **8.140 hogares** (referencia 1 de enero de 2025).
- `average_household_size` = **2,64** (21.492 hab. / 8.140 hogares; media de las 9 secciones ponderada por hogares = 2,641).

### Limitaciones y supuestos (a documentar en el indicador)
1. **Desfase temporal:** el dato de hogares es de 1 ene 2025, mientras que la población actual del módulo es de oct 2026. Son magnitudes de referencia distintas y **no deben combinarse** (p. ej. dividir la población de 2026 por los hogares de 2025).
2. **Unidad de medida:** "hogares" del Padrón (personas que comparten vivienda), no "familias" ni "viviendas". El tamaño medio se deriva de la relación habitantes/hogares de las mismas secciones, por lo que es coherente internamente.
3. **Cobertura de la sección 19059:** con 5,98 km² (el 56,6 % del barrio) y solo 797 hogares, es la sección mayor. Concentra zonas verdes, suelo no edificado y dotaciones. Si parte del suelo de esa sección no es residencial, la cifra de hogares del barrio es correcta (los hogares existen) pero la densidad residencial del barrio no se deduce de ella.
4. **Sin cobertura de alquiler:** el indicador de hogares del Padrón no distingue régimen de tenencia.

## 4. ¿Hace falta GeoPandas?

**Sí, pero solo para la verificación geométrica, no para el dato.**

- Para **obtener** el dato basta con la columna `COD_BAR` de la capa de secciones (atribución oficial) y el XLSX de hogares. Ninguna geometría es necesaria.
- Para **validar** que la agregación es exacta (que ninguna sección cruza el límite del barrio) sí hace falta geometría: `geopandas` + `shapely` calculan la intersección y el área.
- Entorno de trabajo: `geopandas` 1.1.3, `shapely` 2.1.2, `pyproj` 3.7.2, `pyogrio` 0.12.1 (ya instalados, sin añadir dependencias).
- `fiona` no está disponible; la lectura de SHP se hace con `pyogrio` (incluido en geopandas). No hace falta instalarlo.
- Coste operativo: la verificación geométrica es un script de un solo uso (no debe ejecutarse en cada petición MCP).

## 5. Recomendación técnica

1. **Publicados en el MCP** (`src/mcp/server.py`): `households_total` = 8.140, `average_household_size` = 2,64 y `population_total_2025` = 21.492, todos con `reference_period` "1 de enero de 2025", `source_url` del dataset oficial y `verification_status: verified`.
2. **Coherencia de referencias garantizada:** `population_total_2025` existe para que ningún consumidor combine hogares de 2025 con población de 2026. Hay un test de contrato que lo verifica.
3. **Automatización lista:** `refresh_households()` regenera los indicadores; `data/raw/extract_households.py` es el script offline reproducible que descarga, agrega y verifica la geometría.
4. **GeoPandas no se ha añadido a `requirements.txt`:** la extracción de datos no lo necesita (basta el atributo `COD_BAR`) y la verificación geométrica es una tarea de una sola vez, ejecutada por el script offline. Si en el futuro se quiere automatizar la verificación en CI, `pyogrio`/`geopandas` pasarían a ser dependencia de desarrollo, no del servidor.
5. **Siguiente paso opcional:** extender el mismo mecanismo a otros barrios de Madrid (el dataset de población por barrio ya lo permite; el de hogares requiere su código `COD_BAR`).

## 6. Brechas pendientes

| Indicador | Brecha | Alternativa razonable |
|---|---|---|
| Hogares a fecha actual | El dataset oficial solo llega a ene 2025 | Publicado con su referencia explícita; no se actualiza con estimaciones |
| Familias con hijos | Sin fuente oficial | Mantener `unavailable`; usar el 28,29 % < 20 años como referencia indirecta |
| Gimnasios | Sin censo a nivel de barrio | Mantener `unavailable`; el censo de locales no permite certificar "gimnasio con ludoteca" |
| Densidad residential | Las secciones cubren suelo no residencial | No derivar densidad de viviendas por km² sin matizar |
| Equipamientos deportivos | Censo del CSD a nivel municipal | Localizar el dataset municipal de instalaciones deportivas |

## 7. Próximos pasos priorizados

1. **Ampliar el módulo a otros barrios** de Madrid reutilizando `refresh_locales_count()` y `refresh_households()` (solo hay que ampliar los mapas de códigos).
2. **Buscar el censo municipal de instalaciones deportivas** para `gyms_registered`.
3. **Valorar el fichero de "Actividades" del Censo de Locales** (119 MB) para clasificar los locales por epígrafe económico.
4. **Automatizar la verificación geométrica** en CI si el equipo lo considera útil.

## 8. Restricciones cumplidas

- La fase de investigación se hizo **sin modificar código de producción**; los cambios posteriores (publicación de los indicadores de hogares, script offline y tests) se aplicaron ya con la metodología validada y documentada.
- No se instalaron paquetes ni se tocó `requirements.txt`: `openpyxl` y `pyogrio` ya estaban instalados y solo los usa la herramienta offline.
- No se cambió de rama, ni se hizo merge ni deploy.
- No se inventaron datos, fuentes ni resultados.
- No se convirtió `null` en cero.
- Los indicadores de hogares se marcan como verificados solo con la evidencia trazable de §3 (atribución oficial + verificación geométrica + contraste de población).
- Los indicadores verificados de población (27.480 y 28,29 %) no se han modificado.
