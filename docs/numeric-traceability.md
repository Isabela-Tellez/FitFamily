# Cifras trazables: integración y límites

El formato único sigue siendo ReportClaim. Los textos numéricos usan
`Resultado documentado: {{value}} {{unit}}.`; las secciones los citan con
`{{claim:identificador}}`. Markdown y PDF comparten la sustitución.

## Entrada del controlador

```python
from src.graph.report_pipeline import prepare_reviewed_report, export_reviewed_report

result = prepare_reviewed_report(
    brief, research_result,
    price_evidence_ids=["precio_a", "precio_b"],  # selección explícita y justificada
    use_llm=False,
    revision_count=revision_count,
)

# Mostrar las incidencias si result.route no es "pending_review".
# Tras obtener la aprobación humana real, conservar el mismo contexto.
delivery = export_reviewed_report(
    result, research_result, approval, run_id, output_dir,
    csv_path=csv_path, revision_count=revision_count,
)
```

El controlador debe usar esta entrada en lugar de encadenar llamadas sin pasar
el análisis. No se crea una aprobación automáticamente. La entrega vuelve a
comprobar borrador, investigación y análisis actuales. Los exportadores de bajo
nivel no reciben investigación: requieren que el controlador use esta puerta.

## Procedencia y operaciones admitidas

- Valores observados: una evidencia numérica, con URL y unidad.
- Media de precios de una muestra explícita: usa summarize_competitors sobre
  las evidencias mensuales seleccionadas. No se elige automáticamente la muestra.
- Punto de equilibrio: usa calculate_break_even_clients; requiere referencias
  diferenciadas para fixed_costs, monthly_fee y variable_cost_per_client.
  Son importes mensuales. No se inventan costes ni se introducen supuestos sin
  registrar su procedencia.
- Los cálculos desconocidos, las referencias inexistentes o duplicadas, los
  datos ambiguos y los valores no finitos se rechazan.
- Un id repetido con contenido idéntico entre la lista general y competidores
  se deduplica. El mismo id con contenido diferente se rechaza.
- La revisión repite el cálculo y comprueba valor, unidad y evidencias citadas.
  La huella incluye el mapa de entradas financieras.
- Unidades admitidas: EUR con periodicidad monthly/annual/one-time,
  EUR/month, EUR/year, clients, count, %, m2. Otras requieren implementar
  expresamente su interpretación.

## Redacción

El redactor LLM recibe los indicadores y devuelve metric_id, reported_value y
reported_unit. No calcula ni copia números en las secciones; utiliza marcadores.
Su respuesta se revisa después, incluso si cumple el esquema Pydantic.

El modo determinista con análisis construye una sección de resultados con
referencias a las afirmaciones, evitando copias independientes de tarifas.
Conserva fuentes y limitaciones; este modo no reproduce todo el detalle del
antiguo listado de competidores.

Los números literales en secciones, título, zona, limitaciones o afirmaciones sin
indicador provocan una incidencia. Es un control conservador: también puede
señalar fechas, direcciones o numeraciones legítimas. No las corrige silenciosamente.
Detecta dígitos y un vocabulario español limitado de números escritos; no es
una interpretación semántica universal de cualquier frase o idioma. La revisión
humana sigue siendo necesaria para metáforas, comparaciones, selección de la
muestra, significado de las unidades y respaldo real de las fuentes.
URLs e identificadores técnicos no se interpretan como cifras del estudio.

## Compatibilidad y comprobación

No cambian las dependencias de producción. Las pruebas de PDF utilizan
pdfplumber, ya incluido por CrewAI. Los casos LLM usan respuestas simuladas
y no consumen API. Hay regresiones para los cinco problemas detectados y
para la entrega con contexto modificado.

La nueva política cambia la huella: los borradores anteriores requieren nueva
revisión y aprobación. Los borradores con importes literales deberán reconstruirse
mediante el flujo nuevo. No se migran automáticamente archivos de datos históricos.

La procedencia comprobada es interna: existencia, datos registrados, operación
y resultado. No se visita la URL ni se demuestra que el dato publicado sea cierto,
actual o representativo. Eso corresponde a la investigación y a la revisión humana.
