# INE — Metodología de renta neta por sección censal (ADRH, op. 30325)

> Estado: **documentado**, pendiente de descarga oficial validada.
> No se inventan valores de renta. Los intentos reales (`ine_intento_real.json`, `ine_intento_real_02.json`) quedan como histórico.

## Fuente oficial
- INE — Atlas de Distribución de Renta de los Hogares (ADRH)
- Operación: 30325 (`urn:ine:es:OPER:30325`)
- URL referencia: https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177088&menu=ultiDatos&idp=1254735976608
- Catálogo (datos.gob.es): https://datos.gob.es/es/catalogo/ea0042823-atlas-de-distribucion-de-renta-de-los-hogares-adrh
- Formato preferido: CSV / PC-Axis / Excel (lo que la fuente permita en la edición vigente)

## Geografía
- Secciones candidatas de El Cañaveral: 19052, 19053, 19054, 19055, 19056, 19058, 19059, 19060, 19061.
- Debe verificarse correspendencia oficial por edición; no asumirse por código postal ni nombre aproximado.

## Variables
- Prioridad: renta neta media por hogar / por persona / por unidad de consumo (según lo que la fuente publique para la edición consultada).
- Diferenciación clara: renta bruta vs neta; por hogar vs persona; anual vs mensual; media vs mediana.
- No convertir valores anuales a mensuales sin documento de conversión y conservación del original.

## Tratamiento
- Resultado por sección (no agregación por barrio sin ponderaciones oficiales del mismo periodo y universo).
- Si no hay ponderaciones: conservar los nueve resultados individuales; mostrar distribución; no imputar ni estimar la media de barrio.
- Valores nulos o suprimidos: documentados como nulos; no como cero.

## Integración
- `data/raw/ine/` para original descargado.
- `data/processed/ine_renta_secciones.json` para resultado procesado (solo tras verificación completa).
- Contratos de indicadores y evidencias deben mantener fuente, referencia temporal, unidad, limitaciones.
- MCP: indica si el indicador está disponible o no; no marca como `verified` automáticamente por descarga de archivo.

## Limitaciones documentadas
- Descarga aún pendiente de verificación completa (intento real 02 existente pero requiere parámetros específicos de la API INE).
- No se declara PASS para renta INE hasta tener archivo oficial, edición identificada, correspondencia geográfica comprobada y variable correctamente interpretada.
