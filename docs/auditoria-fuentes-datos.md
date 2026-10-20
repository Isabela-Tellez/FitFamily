# Auditoría de fuentes de datos — Módulo de investigación (Persona 1)

## 1. Resumen ejecutivo

El módulo ya cuenta con datos verificados para población (27.480 hab.) y locales abiertos (234, Censo de Locales). Los indicadores de hogares y tamaño medio del hogar **no pueden verificarse** con las fuentes disponibles a nivel de barrio y se mantienen en `null`. Los gimnasios no tienen censo oficial a nivel de barrio.

## 2. Fuentes investigadas

### Población (verificada)
- **Fuente:** Padrón Municipal de Habitantes (datos.madrid.es/dataset/200076-0-padron)
- **Recurso:** CSV (32.5 MB), actualizado 6 oct 2026, cobertura hasta 30 sep 2026
- **Licencia:** CC BY 4.0
- **Método:** suma directa de todas las edades del barrio "EL CAÑAVERAL" (distrito 19, Vicálvaro) en el CSV oficial
- **Resultado:** 27.480 habitantes (oct 2026). Pirámide: 28,29 % < 20 años (7.774 de 27.480)
- **Reproducible:** sí, mediante el script de filtrado por barrio

### Hogares (no verificable a nivel de barrio)
- **Fuente oficial:** datos.madrid.es/dataset/300438-0-hogares-tamano
- **Cobertura temporal:** 1 de enero de 2009 a 1 de enero de 2025 (último disponible: 2025)
- **Frecuencia:** anual
- **Granularidad:** distrito y sección censal, **no por barrio**
- **Variables:** Total Hogares, Tamaño medio del hogar, distribución por tamaño (1-15+ personas)
- **Problema:** El Cañaveral es un barrio dentro del distrito de Vicálvaro. El dataset no incluye una columna de barrio. Las secciones censales que intersectan con El Cañaveral no están documentadas en el dataset.
- **Cartografía oficial:** Geoportal de Madrid (geoportal.madrid.es) ofrece secciones censales en SHP/TopoJSON. Sin embargo, no existe un mapeo oficial de secciones censales a barrios de Madrid.
- **Conclusión:** no se puede calcular hogares de El Cañaveral sin una agregación espacial (intersección de polígonos de secciones censales con los límites del barrio). Esta agregación requeriría GeoPandas y verificación manual. Hasta entonces, `households_total` y `average_household_size` permanecen en `null`.
- **Alternativa razonable:** usar los datos del distrito de Vicálvaro (35.256 hogares, 2,70 pers./hogar en 2025) como referencia contextual, pero documentando que es el distrito, no el barrio.

### Negocios (verificado)
- **Fuente:** Censo de Locales y Actividades (datos.madrid.es/dataset/200085-0-censo-locales)
- **Recurso:** CSV (85.2 MB), actualizado diariamente
- **Licencia:** CC BY 4.0
- **Método:** filtrar `desc_barrio_local == "El Cañaveral"` y `desc_situacion_local == "Abierto"`, contar `id_local` únicos
- **Resultado:** 234 locales abiertos (verificado en esta auditoría)
- **Limitación:** "locales" (premises) ≠ "negocios" (establishments). Un local puede albergar varias actividades. No distingue entre comercio, oficinas, hostelería, etc.

### Gimnasios e instalaciones deportivas (no verificado)
- **Censo de Instalaciones Deportivas (CSD):** cubre instalaciones deportivas a nivel municipal, no a nivel de barrio. No se encontró dataset descargable para Madrid.
- **INE - Directorio Central de Empresas:** empresas por municipio y CNAE, no por barrio.
- **Censo de Locales:** podría filtrar por actividad deportiva (epígrafe), pero la clasificación por actividad no es precisa para "gimnasio con ludoteca".
- **Conclusión:** no existe un censo de gimnasios a nivel de barrio. Los 8 centros localizados manualmente (9F, Énergie, One More, Nine Fitness, Winfit, Sano, Brooklyn Fitboxing, Silva) no constituyen un censo verificado.

### Familias (no disponible)
- No existe una fuente oficial que proporcione "familias con hijos" a nivel de barrio.
- El Padrón Municipal no incluye esta variable.
- Referencia indirecta verificada: 28,29 % de la población es menor de 20 años (Padrón, oct 2026).

## 3. Matriz indicador-fuente

| Indicador | Fuente recomendada | Cobertura real | Nivel de confianza |
|---|---|---|---|
| `population_total` | Padrón Municipal (datos.madrid.es/200076-0-padron) | Barrio (El Cañaveral) | Verificado (primario) |
| `population_under_20_share` | Padrón Municipal (calculado) | Barrio | Verificado (primario) |
| `households_total` | Hogares por tamaño (datos.madrid.es/300438-0-hogares-tamano) | Distrito/sección censal | No verificable a nivel de barrio |
| `average_household_size` | Mismo que hogares | Distrito/sección censal | No verificable a nivel de barrio |
| `businesses_open` | Censo de Locales (datos.madrid.es/200085-0-censo-locales) | Barrio (premises) | Verificado (primario) |
| `families_with_children` | Sin fuente directa | — | No disponible |
| `gyms_registered` | Sin censo a nivel de barrio | — | No disponible |
| `gyms_with_ludoteca` | Sin censo a nivel de barrio | — | No disponible |

## 4. Recomendación técnica

### Integración reproducible del Censo de Locales (implementada)
- Función `refresh_locales_count(area_id, csv_text, url, timeout, store)` en `src/mcp/server.py`.
- Función pura `parse_locales_csv(csv_text, barrio_name)` testeable sin red.
- Descarga explícita o bajo demanda (no en cada consulta MCP).
- Almacena resultado en `_STATISTICS_DATA` con procedencia.
- Tests unitarios con CSV pequeño (sin red).
- Caché local en `data/raw/censo_locales.csv` (gitignored).

### Para hogares (futuro)
1. Descargar XLSX 2025 de hogares.
2. Obtener cartografía de secciones censales (Geoportal Madrid).
3. Identificar secciones que intersectan con El Cañaveral.
4. Agregar hogares de esas secciones, documentando la metodología.
5. Si la intersección es parcial, estimar proporcionalmente y documentar el supuesto.

### Para gimnasios (futuro)
1. Consultar el Censo de Locales filtrando por epígrafe de actividad deportiva.
2. Verificar si la clasificación permite distinguir "gimnasio con ludoteca".
3. Si no, mantener como `null` con conteo manual documentado.

## 5. Brechas pendientes

| Indicador | Brecha | Alternativa razonable |
|---|---|---|
| `households_total` | Sin fuente a nivel de barrio | Usar datos del distrito de Vicálvaro (35.256 hogares, 2.70 pers./hogar) como referencia contextual, documentando que es el distrito |
| `average_household_size` | Mismo | Mismo |
| `families_with_children` | Sin censo directo | Mantener referencia indirecta (28,29 % < 20 años) |
| `gyms_registered` | Sin censo a nivel de barrio | Conteo manual documentado (8 centros) o filtrar Censo de Locales por epígrafe deportivo |
| `gyms_with_ludoteca` | Sin censo | Confirmar por contacto directo con los centros |

## 6. Próximos pasos priorizados

1. **Investigación:** descargar XLSX de hogares 2025 y cartografía de secciones censales para evaluar la viabilidad del cruce geográfico.
2. **Implementación:** si el cruce es viable, añadir un loader de hogares con la misma estructura que el de locales.
3. **Validación:** añadir tests con datos sintéticos controlados para la agregación geográfica.
4. **Documentación:** actualizar `data/raw/README.md` y `docs/auditoria-fuentes-datos.md` con los hallazgos.

## Restricciones cumplidas

- No se modificó código durante la fase de investigación inicial.
- No se instalaron dependencias nuevas.
- No se cambió de rama, ni se hizo merge ni deploy.
- No se inventaron datos, fuentes ni resultados.
- No se convirtió `null` en cero.
- No se marcaron indicadores como verificados sin evidencia trazable.
- El informe se guardó en `docs/auditoria-fuentes-datos.md` sin alterar otros archivos.