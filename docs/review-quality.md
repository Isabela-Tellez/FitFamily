# Revisión, validación y calidad

Responsable: María (Persona 4). Referencia: dev 4b52500, inspeccionado el 29 de octubre de 2026, con la corrección
del contrato de cálculos y las pruebas compartidas ya integradas.
Este documento no acredita cambios posteriores de GitHub.

## Responsabilidad

El revisor detecta incidencias, conserva la identidad del contenido revisado
y permite decidir a qué etapa devolverlo. No concede aprobación humana,
no ejecuta agentes, no cambia los datos y no exporta informes.

## Archivos e interfaces

| Archivo | Responsabilidad |
|---|---|
| src/review/validation.py | Referencias, calidad de evidencias y estructura de afirmaciones |
| src/review/numeric_validation.py | Comparación de valor/unidad y validación de campos numéricos mutables |
| src/review/calculation_validation.py | Procedencia del punto de equilibrio y comprobación con la función de Laura |
| src/review/quality_checks.py | Revisión agregada y huellas de investigación y análisis |
| src/review/models.py | ReviewIssue y ReviewResult |
| src/graph/review_routes.py | Rutas, límite de correcciones y control del contexto vigente |
| src/analysis/calculation_adapter.py | Conversión inicial del contrato original y notas para el informe |
| src/analysis/contracts.py | CalculatedMetric y CalculationContext |

## Entrada y salida

```python
review = run_basic_review(
    draft,
    research_result,
    calculated_metrics=calculated_metrics,
)
route = choose_review_route_for_context(
    review,
    draft,
    research_result,
    revision_count=revision_count,
    max_revisions=2,
    calculated_metrics=calculated_metrics,
)
```

calculated_metrics es opcional para conservar llamadas sin cifras.
Si el borrador declara cifras pero no se proporciona el análisis, se devuelve
missing_analysis_context. Una lista vacía no equivale a no proporcionar análisis.

ReviewResult incluye draft_id, draft_version, draft_fingerprint,
research_fingerprint, analysis_fingerprint, issues y checks_performed.
Su estado es needs_revision si hay errores; en caso contrario pending_review.
No existe un estado de aprobación automática.

## Comprobaciones

- Referencias inexistentes, hechos sin evidencia e identificadores duplicados.
- Referencias vacías, fuentes ausentes, accesos fallidos y fuentes descartadas.
- Identificador, texto y clasificación de cada afirmación.
- Campos numéricos completos y válidos, incluso tras modificar la dataclass.
- Indicadores inexistentes, ambiguos o no disponibles; diferencias de valor/unidad.
- Para cálculos con contexto: escenario, cálculo original, entradas, unidades,
  operación, referencias y resultado de la función económica de Laura.
- Correspondencia de referencias entre la afirmación y el cálculo.
- Conservación de metric_context_notes(metric) en draft.limitations.
- Un resultado con entradas supuestas no debe presentarse como fact.

Los nombres de checks_performed reflejan las comprobaciones activadas.
No son una puntuación de exactitud ni una garantía de calidad de las fuentes.

## Contrato económico

El primer caso admitido es break_even. metric_id distingue escenario e indicador;
calculation conserva el calculation_id original. context mantiene una copia de
EconomicScenario, CalculationResult y el mapa de evidencias por entrada observada.

Se utiliza src.analysis.economic_calculations.calculate_break_even_clients.
No se duplica la fórmula ni se ejecuta el texto de operation como código.

Las entradas assumption no necesitan evidencias inventadas. Las entradas evidence
sí requieren un vínculo explícito y coincidencia de valor y unidad.
EUR/client/month no se convierte implícitamente en EUR/month.

Las métricas antiguas con context=None conservan la comparación básica; no
acreditan procedencia completa. Los identificadores scenario_* o calc_* requieren
contexto. Otros tipos económicos con contexto todavía no están admitidos.

Detalles y ejemplo de conversión: [calculation-review-contract.md](calculation-review-contract.md).

## Rutas y vigencia

| Ruta | Condición |
|---|---|
| pending_review | Sin errores; pendiente de decisión humana |
| revise_research | Hay errores de investigación |
| revise_analysis | Hay errores de análisis y ninguno de investigación |
| revise_writing | Quedan errores de redacción |
| blocked | Hay errores y se agotaron las rondas permitidas |

El orden de prioridad es investigación, análisis y redacción.
Los contadores deben ser enteros no negativos; no se incrementan ni reinician
dentro del revisor. Una revisión obsoleta provoca ValueError: hay que repetirla,
no tratarla como si ya fuera una corrección revisada.

choose_review_route_for_context comprueba investigación, análisis y borrador.
El controlador debe repetir ese control con el estado actual antes de presentar
la aprobación. Si cambian los originales, debe reconstruir las métricas mediante
el adaptador: una copia antigua no detecta modificaciones en objetos externos.

## Límites

La revisión no interpreta semánticamente todas las cifras del texto libre, no
consulta URLs ni demuestra que las fuentes sean verdaderas o representativas.
Gema ya genera el punto de equilibrio mediante build_break_even_claim y
build_report; Markdown y PDF muestran los campos registrados. Esto no comprueba
semánticamente todo el resto del texto libre. Isabella conserva el contexto y registra la aprobación humana.
Laura mantiene los cálculos y la conversión compartida acordada.

## Verificación y política de trabajo

Resultado confirmado por María: 26 pruebas nuevas y 218 en el conjunto de
integración seleccionado. No equivale a ejecutar toda la suite del repositorio.

Durante cambios funcionales se ejecutan únicamente las pruebas relacionadas.
Los cambios documentales se revisan contra el código, sin repetir pytest.
Antes de cerrar la integración del equipo se ejecutarán las regresiones amplias
y el recorrido completo con el redactor y el controlador actuales.

## Demostración y continuidad

Ver [demo-review.md](demo-review.md) para la demostración de tres casos y
[maria-integration-status.md](maria-integration-status.md) para la versión revisada,
los archivos compartidos y los pendientes del workflow.
