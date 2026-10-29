# Registro de integración de María

Actualizado el 29 de octubre de 2026. Fuente inspeccionada:
FitFamily_dev_demo_nuevo(1).zip, origin/dev 4b52500
(commit verificado en los metadatos del ZIP).

## Estado conocido

- Rama de trabajo: feature/review-quality, sin cambios sin guardar al crear el ZIP.
- El estado local posterior al último merge no se ha recibido; no asumir que
  los commits locales estén publicados ni que la rama ya incorpore este dev.
- dev ya contiene la corrección de CalculationResult y las pruebas compartidas.
- Markdown y PDF incluyen metric_id, reported_value y reported_unit.
- Gema unifica once apartados y añade el punto de equilibrio dentro de
  Escenarios económicos. Se mantienen los avisos de información pendiente.
- La demo verifica esa estructura con el redactor determinista, sin llamar a Groq.
- La rama local de María no se ha comparado íntegramente con este ZIP:
  el instalador comprueba los archivos afectados y sus dependencias.
- No aplicar los paquetes antiguos de trazabilidad ni el documental previo.

## Contratos y responsables

| Responsable | Archivos / contrato | Estado observado |
|---|---|---|
| Laura | analysis/calculation_models.py, economic_calculations.py, scenarios.py | Cálculos y escenarios disponibles |
| Compartido con Laura | analysis/calculation_adapter.py y contracts.py | Conversión de punto de equilibrio con contexto completo |
| Gema | reporting/calculated_claims.py y report_builder.py | Texto y campos desde la misma métrica; conserva notas |
| Gema | reporting/markdown_renderer.py y pdf_renderer.py | Referencias numéricas visibles |
| María | review/validation.py, numeric_validation.py, calculation_validation.py, quality_checks.py | Revisión estructural, numérica y del contexto |
| María | graph/review_routes.py | Rutas y vigencia de investigación, análisis y borrador |
| Isabella | graph/workflow.py | Existe, pero conexiones compartidas aún pendientes en este ZIP |

## Conexiones pendientes del workflow en 4b52500

- analysis_node construye las métricas manualmente, sin el contexto del adaptador.
- writing_node llama directamente a run_writing y omite build_report con métricas.
- review_node reconstruye ReportDraft, pero no las afirmaciones anidadas ReportClaim.
- La decisión awaiting_approval/failed no utiliza las rutas y el control de contexto.
- No confundir compilación del grafo con ejecución correcta del recorrido completo.
- Estas observaciones describen el ZIP; no adelantan el estado de ramas de Isabella
  todavía no integradas en dev.

## Verificación acumulada

- María confirmó 26 pruebas nuevas del contrato y 218 en el conjunto seleccionado.
- María confirmó después diez pruebas compartidas de integración.
- Los conteos corresponden a ejecuciones diferentes: no sumarlos como si fueran
  una única ejecución actual.
- Tres casos del workflow quedan como aceptación explícita, fuera de la recogida
  habitual de pytest.
- Para el bloque documental y demo se ejecuta únicamente demo_review.py.

## Continuidad

1. Mantener todos los cambios de María en feature/review-quality.
2. Actualizar este registro después de inspeccionar un ZIP o commit nuevo.
3. Antes de modificar archivos compartidos, comprobar su versión y responsable.
4. Mantener supuestos, limitaciones, unidades y referencia al cálculo original.
5. La redacción libre y la fiabilidad de fuentes mantienen revisión humana.
6. Cuando Isabella entregue sus cambios, ejecutar la aceptación de sus nodos.
7. Al cierre, validar la suite amplia y el recorrido real de aprobación y entrega.

## Archivos de este bloque

- docs/review-quality.md: documentación actual del revisor.
- docs/maria-integration-status.md: este registro.
- docs/demo-review.md: guion, ejecución y límites.
- demo_review.py: demostración reproducible con tres casos ficticios.

No cambia producción, workflow, tests, dependencias ni modelos.
