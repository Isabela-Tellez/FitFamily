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

Agrega las dos validaciones y asigna la etapa de corrección:

| Incidencia | Etapa |
|---|---|
| `evidence_without_source` | `research` |
| Resto de errores | `writing` |

Devuelve un `ReviewResult` con:

- `draft_id` y `draft_version` del borrador revisado.
- `draft_fingerprint` del contenido actual.
- `issues` como tupla de `ReviewIssue` con `severity="error"`.
- `checks_performed=("claim_references", "evidence_quality")`.

No modifica el borrador, no llama a un LLM y no exporta archivos.

## `choose_review_route`

```python
def choose_review_route(
    review: ReviewResult,
    revision_count: int,
    max_revisions: int = 2,
) -> ReviewRoute:
    ...
```

Rutas posibles:

| Ruta | Cuándo |
|---|---|
| `pending_review` | No hay errores; el borrador pasa a revisión humana |
| `blocked` | Hay errores y ya se agotaron las rondas (`revision_count >= max_revisions`) |
| `revise_research` | Hay errores en la etapa de investigación |
| `revise_analysis` | Hay errores en la etapa de análisis |
| `revise_writing` | Solo quedan errores de redacción |

Reglas:

- Las advertencias no provocan corrección por sí solas.
- Se prioriza la etapa más temprana: `research` → `analysis` → `writing`.
- `revision_count` y `max_revisions` deben ser enteros mayores o iguales que cero.
- La revisión inicial empieza con `revision_count=0`; por defecto se permiten 2 rondas.
- La función solo decide la ruta: no ejecuta agentes ni modifica el contador.

## Funciones de vigencia

### `choose_review_route_for_draft`

Comprueba que la revisión corresponda al borrador actual antes de llamar a `choose_review_route`. Lanza `ValueError` si cambió el borrador.

### `choose_review_route_for_context`

Punto de entrada recomendado para el grafo. Comprueba primero la investigación y después el borrador. Lanza `ValueError` si alguno cambió; en ese caso hay que repetir `run_basic_review(draft, research_result)`.

## Flujo

```text
ReportDraft + ResearchResult
        │
        ├── validate_claim_references
        └── validate_evidence_quality
                    │
                    ▼
             run_basic_review
                    │
                    ▼
               ReviewResult
                    │
          choose_review_route(review, revision_count)
                    │
     ┌──────────────┼──────────────┬─────────────┐
     ▼              ▼              ▼             ▼
pending_review  revise_research  revise_analysis  revise_writing
     │                                              │
     ▼                                              └──► nueva ronda
revisión humana                                         (máx. 2)
     │
     ▼
ApprovalRecord (Isabella) ──► exportación (Gema)
```

## Límites importantes

- Pasar la revisión básica **no equivale a aprobar** el informe; el estado queda en `pending_review`.
- No se comprueba la veracidad semántica de las afirmaciones.
- No se consulta Internet ni se vuelve a leer la fuente.
- No se corrige el borrador automáticamente: solo se indica la etapa.
- La aprobación humana y la exportación pertenecen a Isabella y Gema respectivamente.

## Pruebas

```bash
python -m pytest \
  tests/test_review_validation.py \
  tests/test_evidence_quality.py \
  tests/test_quality_checks.py \
  tests/test_review_routes.py -q
```

Ver [demo-review.md](demo-review.md) para la demostración de tres casos y
[maria-integration-status.md](maria-integration-status.md) para la versión revisada,
los archivos compartidos y los pendientes del workflow.
