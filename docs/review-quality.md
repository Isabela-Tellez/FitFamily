# Revisión, validación y calidad

Responsable: **María (Persona 4)**.

La revisión comprueba que el borrador no cite evidencias inexistentes, que los hechos tengan respaldo y que no se usen como prueba accesos fallidos o fuentes descartadas. **No aprueba el informe ni autoriza exportaciones**: emite un diagnóstico y decide a qué etapa devolver las correcciones.

## Archivos

| Archivo | Contenido |
|---|---|
| `src/review/validation.py` | `validate_claim_references`, `validate_evidence_quality` |
| `src/review/quality_checks.py` | `run_basic_review` |
| `src/review/models.py` | `ReviewIssue`, `ReviewResult` |
| `src/graph/review_routes.py` | `choose_review_route` |
| `tests/test_review_validation.py` | Referencias y afirmaciones |
| `tests/test_evidence_quality.py` | Calidad de evidencias |
| `tests/test_quality_checks.py` | Resultado agregado |
| `tests/test_review_routes.py` | Enrutamiento y límite de correcciones |

## Modelos

```python
@dataclass(frozen=True)
class ReviewIssue:
    code: str
    reference_id: str
    message: str
    severity: Literal["error", "warning"]
    correction_stage: Literal["research", "analysis", "writing"]


@dataclass(frozen=True)
class ReviewResult:
    draft_id: str
    draft_version: int
    draft_fingerprint: str
    issues: tuple[ReviewIssue, ...]
    checks_performed: tuple[str, ...]
```

`ReviewResult.status` se calcula automáticamente:

- `needs_revision` si hay al menos una incidencia con `severity="error"`.
- `pending_review` si no hay errores (las advertencias no bloquean por sí solas).

La huella (`draft_fingerprint`) se obtiene con `calculate_draft_fingerprint` de `src/automation/exporter.py`, de modo que la revisión queda ligada al contenido exacto del borrador.

## `validate_claim_references`

Comprueba:

| Código | Problema |
|---|---|
| `missing_evidence` | El borrador cita una evidencia que no existe en la investigación |
| `fact_without_evidence` | Una afirmación marcada como `fact` no tiene `evidence_ids` |
| `duplicate_claim_id` | El mismo `claim_id` aparece en varias afirmaciones |

Reutiliza `find_missing_evidence_ids` de `src/reporting/report_builder.py` para no duplicar la lógica de Gema.

**No verifica** que el contenido de la fuente demuestre realmente la afirmación; solo comprueba existencia y estructura de las referencias.

## `validate_evidence_quality`

Detecta:

| Código | Problema |
|---|---|
| `empty_evidence_reference` | Una afirmación contiene una referencia vacía |
| `evidence_without_source` | Una evidencia que respalda un hecho no indica procedencia (`source_url`) |
| `failed_access_as_evidence` | Se usa una evidencia `access_attempt_*` (acceso fallido) como respaldo |
| `rejected_source_as_evidence` | Se usa una evidencia `source_*` marcada como `[rejected]` |

Las evidencias se buscan tanto en `research_result.evidences` como en `competitor.evidences`. Los problemas duplicados para la misma referencia se eliminan.

## `run_basic_review`

```python
def run_basic_review(
    draft: ReportDraft,
    research_result: ResearchResult,
) -> ReviewResult:
    ...
```

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
