# Contrato compartido: primer caso, punto de equilibrio

Base revisada: dev b5dca87. Esta corrección reemplaza el último commit de trazabilidad, todavía sin PR
a dev; no debe integrarse aquel paquete de veinte archivos.
No se cambian los modelos de Laura ni las funciones de Gema.

## Conversión sin fórmulas duplicadas

El adaptador inicial está en src/analysis/calculation_adapter.py para que Laura
pueda adoptarlo como única conversión. No llama al LLM ni calcula el resultado:
conserva el resultado original y una copia completa de su contexto.

```python
from src.analysis.calculation_adapter import metric_from_break_even, metric_context_notes

metric = metric_from_break_even(
    scenario,
    calculation_result,  # calculation_type == "break_even"
    # Solo para entradas marcadas como evidence; los supuestos no lo necesitan.
    input_evidence_ids={},
)
calculated_metrics = [metric]
```

El identificador de negocio es scenario_id + ".break_even_clients".
El campo calculation conserva calculation_id, independiente de metric_id.
context contiene EconomicScenario, CalculationResult y el vínculo por entrada
observada. Conserva operation, inputs/input_type, assumptions y limitations.

El modelo anterior CalculatedMetric sigue siendo válido con context=None.
Esas métricas antiguas solo tienen comparación numérica; NO se consideran
comprobaciones completas de procedencia. Para ids scenario_* o calc_* el revisor
exige contexto. Otros tipos económicos con contexto se rechazan hasta implementar
su comprobación específica.

## Redacción de Gema

Gema debe generar reported_value, reported_unit y texto desde el mismo metric.
No se impone una plantilla de texto ni se sustituye el redactor en esta corrección.

- value=None representa un resultado no disponible: no se crea una cifra ni cero.
- Si hay entradas assumption, la afirmación no debe marcarse como fact.
- Las evidencias de la afirmación deben conservar metric.evidence_ids.
- Añadir metric_context_notes(metric) a draft.limitations, sin duplicados.
  Incluye las entradas supuestas con sus valores, supuestos narrativos del
  escenario y limitaciones originales. El revisor comprueba su presencia.
- Conservar el valor sin redondeos arbitrarios; si se adapta a float, comprobar
  que Decimal(str(valor)) coincide antes de utilizarlo.
- La coherencia del texto libre con los campos sigue siendo responsabilidad
  de la generación de Gema y de una prueba compartida; este PR no afirma
  verificar semánticamente cualquier cifra del texto.

## Revisión e integración de Isabella

```python
review = run_basic_review(draft, research_result, calculated_metrics=calculated_metrics)
route = choose_review_route_for_context(
    review, draft, research_result, revision_count=revision_count,
    calculated_metrics=calculated_metrics,
)
```

Se repite el control de contexto antes de solicitar aprobación. Después de cambios
en los originales hay que reconstruir calculated_metrics con el adaptador;
una copia antigua no puede descubrir cambios en un objeto externo. No regenerar
el cálculo solo para convertirlo: su calculation_id UUID identifica la ejecución.

La huella cubre todos los campos del contexto. Cambiar entradas, supuestos,
limitaciones, operación, escenario o referencias invalida la revisión.

El revisor comprueba las entradas y unidades originales y llama a
src.analysis.economic_calculations.calculate_break_even_clients; no mantiene una
segunda fórmula ni interpreta operation como código ejecutable.

Para entradas evidence exige vínculo explícito por variable, evidencia existente,
fuente, valor y unidad coincidentes. No deduce automáticamente conversiones:
EUR/client/month no equivale a EUR/month. Los supuestos no requieren evidencias.
Una URL registrada no prueba la veracidad de su contenido.

## Alcance de la corrección respecto al paquete anterior

Se aplica en feature/review-quality después de revertir el commit 7db18ae
e integrar dev. git revert conserva el historial del trabajo anterior. No se incorporan los módulos provenance.py,
metric_binding.py, numeric_text.py ni report_pipeline.py del paquete anterior,
ni sus cambios en escritores o renderizadores. Así no se solapan las tareas
que Gema está realizando. El commit anterior debe estar revertido antes de aplicar este paquete.

El primer caso acordado es un escenario de punto de equilibrio; ampliar a ingresos
y costes requiere contratos y pruebas específicos. Un mismo scenario_id debe
identificar un único escenario dentro de la ejecución.
