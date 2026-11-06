# Integración de redacción, revisión y entrega

Este documento describe cómo conectar los módulos existentes de Gema y María con el futuro controlador de Isabella.

La integración del análisis se completa con el contrato `calculation-review-contract.md` y el nodo `analysis` del workflow (`src/graph/workflow.py`). El recorrido descrito ahora incluye cálculos económicos (`CalculatedMetric`) conectados al borrador y al revisor.

## 1. Generar y conservar el borrador

El controlador recibe `ResearchBrief` y `ResearchResult` y genera un borrador:

```python
from src.reporting.report_builder import build_report
from src.reporting.markdown_renderer import render_report_markdown

# Modo determinista para comprobar la integración sin llamadas externas.
draft = build_report(brief, research_result)

# Mostramos el mismo objeto que después se revisará y aprobará.
preview = render_report_markdown(draft)
```

Para utilizar CrewAI y Groq, la construcción se cambia por:

```python
draft = build_report(brief, research_result, use_llm=True)
```

Esta segunda opción necesita el proveedor configurado y puede devolver errores que el controlador debe mostrar.

El controlador debe conservar `draft`. No debe volver a llamar a `build_report` para mostrar la vista previa o exportar después de aprobar.

## 2. Ejecutar la revisión básica

from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context

review = run_basic_review(draft, research_result)

# Se inicializa una sola vez al comenzar la ejecución.
# El controlador debe conservarlo durante las correcciones.
revision_count = 0

route = choose_review_route_for_context(
    review,
    draft,
    research_result,
    revision_count=revision_count,
    max_revisions=2,
)

El controlador muestra las incidencias de `review.issues`.

- `revise_research`, `revise_analysis` o `revise_writing`: se necesita una corrección.
- `blocked`: se alcanzó el límite de correcciones y se requiere intervención.
- `pending_review`: las comprobaciones básicas no han encontrado errores que obliguen a corregir.

`pending_review` no significa que el informe esté aprobado ni que sus afirmaciones se hayan comprobado semánticamente.

Si se corrige el borrador, se conserva su identificador, se incrementa su versión y se ejecuta una revisión nueva. La aprobación anterior no se reutiliza.

## 3. Comprobar que la revisión sigue vigente

Antes de presentar la decisión humana, el controlador vuelve a comprobar
que la revisión corresponde al borrador y a la investigación actuales:

```python
route = choose_review_route_for_context(
    review,
    draft,
    research_result,
    revision_count=revision_count,
    max_revisions=2,
)

if route != "pending_review":
    raise ValueError(
        "Hay correcciones pendientes o el proceso está bloqueado."
    )
```

Si cambia el borrador o la investigación, la función lanza `ValueError`.
El controlador debe detener el avance hacia la aprobación y ejecutar
una nueva revisión con los datos actuales.

Volver a revisar no concede aprobación ni garantiza que desaparezcan
los errores. Tampoco debe reiniciar el contador de correcciones.

Los errores de configuración, como un contador inválido, deben
corregirse; no deben provocar reintentos automáticos ilimitados.

Para incluir resultados de análisis guardados por separado, deben proporcionarse mediante calculated_metrics, como se explica al final de este documento.

## 4. Recoger la decisión humana

La interfaz muestra el borrador y la revisión, y permite seleccionar las acciones de entrega.

Solo después de recibir una aprobación humana explícita, el controlador crea el registro:

```python
from datetime import datetime, timezone
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord

# run_id debe existir desde el comienzo de la ejecución.
# selected_actions procede de las opciones elegidas en la interfaz.
# human_approved procede de la decisión explícita de la persona usuaria.

approval = ApprovalRecord(
    run_id=run_id,
    draft_id=draft.draft_id,
    draft_version=draft.version,
    draft_fingerprint=calculate_draft_fingerprint(draft),
    approved=human_approved,
    actions=tuple(selected_actions),
    decided_at=datetime.now(timezone.utc),
)
```

Acciones disponibles:

- `export_markdown`
- `export_pdf`
- `update_tracking_csv`

El seguimiento CSV requiere al menos un formato de informe autorizado.

Crear este objeto no demuestra por sí mismo que hubo una decisión humana. La interfaz y el controlador deben garantizarla. Si la persona rechaza la entrega, el controlador no llama al coordinador.

## 5. Ejecutar la entrega aprobada

Este paso requiere que esté disponible el módulo `src/automation/delivery.py`, incluido en el PR #22.

```python
from src.automation.delivery import export_approved_report

result = export_approved_report(
    draft,
    approval,
    run_id=run_id,
    output_dir="reports/generated",
    csv_path="reports/generated/tracking.csv",
)
```

Las rutas las configura el controlador, no el LLM.

El coordinador valida las autorizaciones antes de escribir. Devuelve un `DeliveryResult` con acciones completadas, fallidas, rutas y errores.

El controlador solo muestra “Entrega completada” cuando `result.complete` es verdadero. Si es falso, muestra qué se ha conseguido y qué sigue pendiente.

Los errores de validación que se propaguen deben mostrarse como un rechazo de la operación; no como una entrega correcta.

## 6. Conservar el resultado y permitir reintentos

El controlador conserva juntos:

- `run_id`
- `draft`
- `review`
- `approval`
- `result`

Si falla una parte de la entrega, puede ofrecer un reintento:

```python
result = export_approved_report(
    draft,
    approval,
    run_id=run_id,
    output_dir="reports/generated",
    csv_path="reports/generated/tracking.csv",
    previous_result=result,
)
```

El reintento mantiene el borrador y la aprobación. No vuelve a redactar el informe.

Los informes completados que siguen existiendo se reutilizan. Su contenido no se vuelve a comprobar durante esa reutilización; se presupone que nadie los ha modificado externamente.

El coordinador no persiste el resultado ni reintenta automáticamente. Esas decisiones corresponden al controlador.

## Límites del ejemplo

Los fragmentos describen puntos de integración; no forman una aplicación ejecutable completa.

Quedan pendientes la interfaz (`streamlit`), la persistencia del estado global (`workflows.py` con `ApprovalRecord` aún pendiente), la gestión global de correcciones y la integración del contrato de análisis de Laura (`calculation_adapter.py` implementado; pendiente integración en flujo completo con `workflows.py` y PR #35).

## Revisión con resultados del análisis

Cuando el controlador dispone de indicadores calculados, debe pasar
la misma lista actual tanto a la revisión como al enrutamiento:

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

Esta llamada de enrutamiento se repite antes de presentar la aprobación,
utilizando el estado actual y sin reiniciar el contador.

`calculated_metrics` es una lista de `CalculatedMetric` suministrada por
el análisis. Las cifras declaradas están en cada elemento de `draft.claims`, en los
campos `metric_id`, `reported_value` y `reported_unit`.

Si hay cifras declaradas pero falta el análisis, la revisión genera una
incidencia. Si cambia el análisis después de revisar, el control de
vigencia exige una nueva revisión.

El control numérico compara campos estructurados. No comprueba por sí
solo que todas las cifras del texto estén registradas ni que el texto
coincida con esos campos. Tampoco valida aún la procedencia completa
de los cálculos.

## Formato numérico único

Cada afirmación admite como máximo un indicador. Para presentar dos
indicadores, se crean dos afirmaciones.

```python
claim = ReportClaim(
    claim_id="average_price",
    text="La cuota media de la muestra ficticia es de 45 euros al mes.",
    kind="inference",
    evidence_ids=["demo_price"],
    metric_id="market.average_monthly_price_eur",
    reported_value=45.0,
    reported_unit="EUR/month",
)
```

No existe una lista numérica separada en el borrador ni un contrato
ReportedMetric. El comparador recibe las afirmaciones del borrador.
CalculatedMetric se conserva para los resultados del análisis.
Los valores declarados son int/float finitos; para compararlos con Decimal
se utiliza Decimal(str(valor)), sin introducir una tolerancia implícita.

La revisión vuelve a comprobar las referencias numéricas mutables.
Un valor no finito modificado después de crear una afirmación impide
calcular una huella JSON válida y rechaza la revisión mediante ValueError.
Hay que corregirlo antes de revisar de nuevo.

Este cambio requiere volver a revisar y aprobar los borradores existentes.
No convierte archivos de datos guardados con el formato anterior.
La comparación no extrae cifras del texto ni verifica la procedencia
completa de los cálculos.
