# Auditoría de fuentes de datos — Módulo de investigación (Persona 1)

## 1. Resumen ejecutivo

| Indicador | Estado | Valor | Fuente |
|---|---|---|---|
| Población total | Verificado | 27.480 (1 oct 2026) | Padrón Municipal, CSV oficial |
| Menores de 20 años | Verificado | 28,29 % (1 oct 2026) | Padrón Municipal, calculado |
| Población a 1 ene 2025 | Verificado | 21.492 | Fichero oficial de hogares |
| Hogares | Verificado | 8.140 (1 ene 2025) | Fichero oficial de hogares, suma exacta de las 9 secciones censales del barrio |
| Tamaño medio del hogar | Verificado | 2,64 (1 ene 2025) | Derivado de los mismos datos |
| Hogares con menores | Verificado (mínimo) | 3.071 (1 ene 2025) | Hoja de composición del hogar del mismo fichero |
| Locales abiertos | Verificado | 234 (20 oct 2026) | Censo de Locales, fichero de Locales |
| Gimnasios | Verificado | 9 (20 oct 2026) | Censo de Locales, fichero de Actividades, epígrafe 931008 |
| Deporte y recreación | Verificado | 4 | Censo de Locales, epígrafe 855002 |
| Ocio infantil | Verificado | 3 | Censo de Locales, epígrafes 932001 y 932002 |
| Piscinas comunitarias | Verificado | 3 | Censo de Locales, epígrafe 931010 |
| Familias con hijos | No disponible | `null` | Ninguna fuente oficial define "familias con hijos" a nivel de barrio |
| Gimnasios con ludoteca | No disponible | `null` | Ningún epígrafe combina gimnasio y ludoteca |

**Corrección de la auditoría anterior:** la primera revisión se quedó en el *primer
recurso* de cada dataset (el fichero de Locales y la hoja de Tamaño del hogar) y
concluyó que no había fuente para familias ni gimnasios. Ambos datasets tienen más
recursos, y ahí estaban los datos que faltaban. Ningún valor se había inventado,
pero la conclusión era más fuerte que la evidencia.

**Estado de implementación:** todos los indicadores con valor están publicados en el
MCP con `reference_period`, `source_url`, `consulted_at` y `verification_status`, y
son reproducibles con `data/raw/extract_censo_locales.py`,
`data/raw/extract_households.py` y `data/raw/extract_competitor_registry.py`.

## 2. Causa raíz del fallo del buscador de fuentes

**El buscador no fallaba por las instrucciones: fallaba por código.** Durante la
generación del registro de competidores apareció el error real:

```
Search provider failed: urlencode() got an unexpected keyword argument 'query_fragment'
```

Causa: `_normalize_url()` en `src/tools/search_web.py` llamaba
`urlencode(query, query_fragment=parsed.fragment)`. Ese argumento **no existe** en
`urllib.parse.urlencode`, así que **toda búsqueda web lanzaba `TypeError`**, que
`search_web()` envolvía en `RuntimeError`. Además, la URL se reconstruía sin el
interrogante, por lo que los parámetros se habrían perdido igualmente.

Por eso el agente no encontraba fuentes: **no las buscaba bien, es que no podía
buscar**. Los tests no lo detectaban porque todos mockeaban `search_web`. Corregido
y con tres tests de regresión que usan la función real.

Consecuencia para el diseño: la mejora del buscador no consiste en reescribir el
prompt del agente, sino en (a) reparar la herramienta y (b) añadir
`src/tools/source_discovery.py`, que convierte una variable pendiente en varias
consultas (literal, "datos abiertos", "estadística" y una por organismo con `site:`),
clasifica cada resultado como `discovered`, `accessible`, `extracted`, `validated` o
`rejected` con motivo explícito, distingue páginas informativas de datasets
descargables y **no marca nada como validado sin haber leído el contenido**.

## 3. Fuentes evaluadas para las variables que faltan

| Fuente | Veredicto | Cobertura real | Estado |
|---|---|---|---|
| **INE — Atlas de Distribución de Renta de los Hogares (operación 30325)** | **La más valiosa** | Sección censal, toda España | Documentada en `docs/pendiente-renta-ine.md`; **no descargada** |
| **Censo de Locales histórico (datos.madrid.es/209548)** | **Muy útil** | Snapshots mensuales de marzo 2014 a septiembre 2026 | Verificado en la ficha; pendiente de uso para validar el censo actual y medir la evolución de la oferta |
| **CRTM (datos.crtm.es)** | Utile, coste alto | Red de transporte completa (GTFS) | Pendiente: el GTFS es pesado; para accesibilidad por distancia puede bastar la capa de estaciones del Geoportal |
| **Empleo de la Comunidad de Madrid** | Contexto, no local | Por verificar si llega a barrio o sección censal | Pendiente de verificar la granularidad |
| **Directorio de centros educativos del Ayuntamiento** | Relevante (demanda de conciliación) | Centro a centro, con coordenadas | Pendiente de descarga; **no se ha verificado su cobertura en El Cañaveral** |
| **Madrid Crece / EMVS (viviendas futuras)** | **No es un dataset** | Noticias municipales | Solo sirve como contexto en el informe, no como dato automatizable |
| **Encuesta de Presupuestos Familiares (Comunidad / Ayuntamiento)** | Regional, no local | Comunidad / municipio | **No atribuir a sección censal**; solo contexto |

### Lo que ya se puede calcular sin fuentes nuevas

Con lo descargado (padrón por edad exacta, libro de hogares, censo de locales con
coordenadas y geometría de secciones censales) se puede obtener:

- Cohorts 0-4, 5-9, 10-14, 15-24, 25-44, 45-64, 65+ por sección censal.
- Ratio de dependencia, % mayores de 65 y % mujeres.
- Evolución 2018-2026 y población nueva.
- Densidad de locales por sección censal y por km².
- Número de equipamientos (gimnasios, ocio infantil, piscinas) a 250/500/1.000 m
  de cada local, gracias a las coordenadas oficiales.
- Cobertura espacial de la oferta mediante H3 o clustering.
- Brecha entre población infantil y oferta de servicios.

## 4. Fuentes investigadas

### Población (verificada)
- **Fuente:** Padrón Municipal de Habitantes (datos.madrid.es/dataset/200076-0-padron)
- **Recurso:** CSV (32,5 MB), actualizado 6 oct 2026, cobertura hasta 30 sep 2026. Licencia CC BY 4.0.
- **Método:** suma directa de todas las edades del barrio "EL CAÑAVERAL" (distrito 19, Vicálvaro).
- **Resultado:** 27.480 hab. (oct 2026); 28,29 % < 20 años (7.774 de 27.480).
- **Contraste:** el dataset "Población por distrito y barrio a 1 de enero" (datos.madrid.es/300557) da 24.945 hab. a 1 ene 2026 y 21.492 a 1 ene 2025. Ambas son coherentes con el crecimiento del barrio.

### Hogares (verificado)
- **Fuente:** datos.madrid.es/dataset/300438-0-hogares-tamano, recurso XLSX 2025.
- **Referencia:** Padrón Municipal revisado a **1 de enero de 2025**. Cobertura temporal del dataset: 1 ene 2009 – 1 ene 2025. Frecuencia anual. Licencia CC BY 4.0.
- **Granularidad:** distrito y sección censal. Hoja "Tamaño del hogar": columnas `Habitantes`, `Total Hogares`, `Tamaño medio del hogar` y distribución por tamaño (1 a 15+ personas). Hoja "Composición del hogar": 20 categorías de tipo de hogar.
- **Resultado:** 8.140 hogares, 2,6403 de media, 21.492 habitantes, 3.071 hogares con menores (mínimo).
- **Limitación de vigencia:** el último dato oficial de hogares es de enero 2025, no de octubre 2026. Es la limitación real de este indicador, no la geografía.

### Cartografía oficial de secciones censales y barrios
- **Fuente:** Geoportal del Ayuntamiento de Madrid, "Límites administrativos actuales" (id `e251898e-4a9c-11eb-9104-dc4a3e8ce33b`).
- **Fecha de datos:** 31/08/2026. SRS: **EPSG:25830** (ETRS89 / UTM 30N). Secciones censales actualizadas en junio de 2022; barrios conforme al acuerdo del Pleno de 29/06/2021 (BOCM 12/07/2021).
- **Recursos descargados:** `Secciones_Censales.zip` (SHP), `Barrios.zip` (SHP) y sus versiones TopoJSON.
- **Atributos clave:** la capa de secciones trae `COD_DIS`, `NOM_DIS`, **`COD_BAR`**, `NOM_BAR`, `COD_SECCIO`, `AREA`. La capa de barrios trae `CODDIS`, `NOMDIS`, `COD_BAR`, `NOMBRE`, `AREA`.
- **Consecuencia decisiva:** existe una **atribución oficial sección→barrio** en la propia cartografía municipal, sin necesidad de inferencia espacial.

### Locales (verificado)
- **Fuente:** Censo de Locales y Actividades (datos.madrid.es/dataset/200085-0-censo-locales).
- **Recursos:** Locales (id, dirección, CP, coordenadas), Actividades (epígrafes) y Locales con información de licencia (ref., tipo, situación y fecha).
- **Licencia:** CC BY 4.0. Actualización diaria.
- **Resultados:** 234 locales abiertos en el barrio; 18 con actividad vinculada al estudio (gimnasios, deporte y recreación, ocio infantil y piscinas); 16 de esos con información de licencia.
- **Limitaciones del propio dataset:** la información procede de un registro administrativo sin tratamiento estadístico, por lo que puede contener inconsistencias; hay duplicidad declarada en los ficheros de octubre 2021 a enero 2022.

### Gimnasios e instalaciones deportivas
- **Censo de Instalaciones Deportivas (CSD):** a nivel municipal, no de barrio; sin dataset descargable localizado para Madrid.
- **INE — Directorio Central de Empresas:** empresas por municipio y CNAE, no por barrio.
- **Censo de Locales:** el fichero de Actividades permite clasificar por epígrafe (931008 → 9 gimnasios). No permite certificar "gimnasio con ludoteca".
- **Conclusión:** no existe un censo de gimnasios a nivel de barrio más allá del recuento por epígrafe.

### Familias
- El Padrón Municipal no incluye la variable "familias con hijos".
- Referencia indirecta verificada: 28,29 % de la población es menor de 20 años (Padrón, octubre 2026) y 3.071 hogares con menores (mínimo, 1 ene 2025).

## 5. Estudio espacial: ¿se pueden calcular los hogares de El Cañaveral?

**Sí, y de forma exacta (no estimada).**

### Fuentes combinadas
1. `Secciones_Censales.zip` → 2.462 secciones, EPSG:25830.
2. `Barrios.zip` → 131 barrios, EPSG:25830.
3. `hogares_2025.xlsx` (dataset 300438) → datos por sección.

### Paso 1 — Atribución oficial
El shapefile de barrios identifica El Cañaveral como `COD_BAR = 194`, distrito 19 (Vicálvaro), superficie 10.567.690,6 m².

Las secciones con `COD_BAR = 194` son **9**: 19052, 19053, 19054, 19055, 19056, 19058, 19059, 19060, 19061.

### Paso 2 — Verificación geométrica (no hay secciones que crucen el límite)
- Área del polígono de El Cañaveral: 10.567.690,6 m².
- Área de la unión de sus 9 secciones oficiales: 10.567.690,6 m².
- Intersección: 10.567.690,6 m² → **cobertura 100,0000 %**.
- Área de las secciones fuera del barrio: **0,0 m²**.
- Área del barrio no cubierta: **0,0 m²**.
- Ratio de intersección por sección: **1,0 en las 9**.

**No hay ninguna sección que cruce el límite de El Cañaveral**, por lo que **no hace falta repartir hogares por superficie**. La suma es exacta y no introduce supuestos.

### Paso 3 — Contraste cruzado con una fuente independiente
- Suma de habitantes de las 9 secciones (21.492) **coincide exactamente** con la población oficial de El Cañaveral a 1 de enero de 2025 del dataset "Población por distrito y barrio a 1 de enero".
- Contraste con el distrito: Vicálvaro tiene 95.233 hab. y 35.256 hogares (2,701 de media). El Cañaveral representa el 22,6 % de los habitantes y el 23,1 % de los hogares del distrito, coherente con su peso territorial (10,57 de 45,04 km² ≈ 23 %).

### Resultado
- `households_total` = **8.140 hogares** (referencia 1 de enero de 2025).
- `average_household_size` = **2,64** (21.492 hab. / 8.140 hogares).
- `households_with_minors` = **3.071** (mínimo verificable).

### Limitaciones y supuestos (documentados en el indicador)
1. **Desfase temporal:** el dato de hogares es de 1 ene 2025, mientras que la población actual del módulo es de oct 2026. Son magnitudes de referencia distintas y **no deben combinarse** (p. ej. dividir la población de 2026 entre los hogares de 2025).
2. **Unidad de medida:** "hogares" del Padrón (personas que comparten vivienda), no "familias" ni "viviendas".
3. **Categorías ambiguas:** las categorías "con o sin menores" (662 hogares) no permiten atribuir la presencia de menores; las "sin menores" (2.484) se descartan. Por eso 3.071 es un mínimo.
4. **Cobertura de la sección 19059:** con 5,98 km² (el 56,6 % del barrio) y solo 797 hogares, es la sección mayor. La cifra de hogares es correcta, pero la densidad residencial no se deduce de ella.

## 6. ¿Hace falta GeoPandas?

**Para el dato, no. Para validar la exactitud, sí.**

- Para *obtener* el valor basta `COD_BAR` + el XLSX. Cero geometría.
- Para *demostrar* que la agregación es exacta (que ninguna sección cruza el límite) hace falta geometría: `geopandas` + `shapely` calculan la intersección y el área.
- `geopandas` 1.1.3, `shapely` 2.1.2, `pyproj` 3.7.2 y `pyogrio` 0.12.1 ya están instalados; `fiona` no está y no hace falta (lee el SHP con `pyogrio`).
- Coste: la verificación geométrica es un script de un solo uso, no debe ejecutarse en cada petición MCP.
- La conversión de UTM 30N a WGS84 (para `latitude`/`longitude`) usa `pyproj` de forma **opcional**: si no está, las coordenadas UTM se conservan en la evidencia y `latitude`/`longitude` quedan como `None`.

## 7. Recomendación técnica

### Publicado
- `households_total` = 8.140, `average_household_size` = 2,64 y `population_total_2025` = 21.492, con referencia 1 ene 2025.
- `households_with_minors` = 3.071 (mínimo verificable).
- `gyms_registered` = 9, `sports_recreation_venues` = 4, `childrens_play_venues` = 3, `community_pools` = 3.
- `businesses_open` = 234.

### Siguiente fase
- **Renta (INE ADRH)**: ver `docs/pendiente-renta-ine.md`. Verificar el último año realmente disponible, los identificadores geográficos y las limitaciones de la estadística experimental.
- **Evolución de la oferta**: usar el Censo de Locales histórico para medir la apertura y cierre de equipamientos por mes.
- **Demanda infantil**: cruzar los cohorts 0-4 y 5-9 con la oferta, usando la distancia real a los equipamientos.

## 8. Brechas pendientes

| Indicador | Brecha | Alternativa razonable |
|---|---|---|
| Hogares a fecha actual | El dataset oficial solo llega a ene 2025 | Publicar con su referencia explícita; no estimar |
| Familias con hijos | Sin fuente oficial | Mantener `unavailable`; usar 28,29 % < 20 años y 3.071 hogares con menores como referencia indirecta |
| Gimnasios con ludoteca | Ningún epígrafe lo recoge | Confirmar centro a centro con la evidencia de la web de cada uno |
| Renta por sección | Pendiente de integración | INE ADRH, fase documentada |
| Alquiler comercial | Sin fuente pública fiable | Estimación a partir del €/m² de alquiler de vivienda, marcada como estimación |
| Densidad residencial | Las secciones cubren suelo no residencial | No derivar densidad de viviendas por km² sin matizar |

## 9. Próximos pasos priorizados

1. **Integrar la renta** (INE ADRH) con la metodología de la fase documentada.
2. **Medir la evolución de la oferta** con el Censo de Locales histórico.
3. **Cruzar población infantil con la oferta** y la distancia real a los equipamientos.
4. **Ampliar el registro a otros barrios** de Madrid: solo hay que ampliar los mapas de códigos.
5. **Buscar el censo municipal de instalaciones deportivas** para `gyms_registered` más allá del epígrafe.

## 10. Restricciones cumplidas

- La fase de investigación se hizo **sin modificar código de producción**; los cambios posteriores (publicación de los indicadores de hogares, registro de competidores y buscador de fuentes) se aplicaron ya con la metodología validada y documentada.
- No se instalaron paquetes ni se tocó `requirements.txt`: `openpyxl` y `pyogrio` solo los usan las herramientas offline, con importaciones perezosas en el servidor.
- No se cambió de rama, ni se hizo merge ni deploy.
- No se inventaron datos, fuentes ni resultados.
- No se convirtió `null` en cero.
- Los indicadores de hogares se marcan como verificados solo con la evidencia trazable de §5 (atribución oficial + verificación geométrica + contraste de población).
