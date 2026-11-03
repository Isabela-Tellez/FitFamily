# Entrega del módulo de redacción, informe y automatización

Estado revisado: 31 de octubre de 2026. Responsable: Persona 3 (Gema).
Este documento describe componentes disponibles y límites de la entrega;
no declara terminado el producto completo ni el workflow compartido.

## Componentes entregados

| Componente | Interfaz pública | Responsabilidad |
| --- | --- | --- |
| Redactor CrewAI/Groq | run_writing(brief, research) | JSON validado, once apartados y referencias; contexto por lotes sin perder registros |
| Constructor | build_report(brief, research, use_llm=..., calculated_metrics=...) | Conserva el borrador y añade el punto de equilibrio desde las métricas originales |
| Previsualización | render_report_preview(draft) | Instantánea con Markdown, ID, versión, huella y opciones de entrega |
| Presentación | render_report_markdown(draft), render_report_pdf(draft) | Texto y referencias numéricas; no conceden autorización |
| Entrega | export_approved_report(draft, approval, run_id, output_dir, csv_path=...) | Markdown/PDF/CSV, autorización por acción, éxitos parciales y reintentos |

Los datos de análisis y los textos procedentes de fuentes se conservan como
evidencias, hipótesis y limitaciones. El redactor no calcula nuevas cifras ni
concede aprobación. La exportación no es una herramienta de libre uso del agente.

## Contrato con la interfaz de Persona 5

```python
from src.ui.report_preview import render_report_preview

preview = render_report_preview(draft)
# Mostrar preview.markdown y permitir seleccionar preview.delivery_actions.
# Conservar el mismo draft y preview.draft_fingerprint.
```

ReportPreview es una instantánea inmutable de:

- markdown: texto del borrador, con su estado pendiente de revisión/aprobación;
- draft_id, draft_version, draft_fingerprint: identidad del contenido mostrado;
- delivery_actions: export_markdown, export_pdf y update_tracking_csv.

Las acciones son opciones, no autorizaciones. Renderizar la vista no escribe
archivos ni crea ApprovalRecord. No hay dependencia de Streamlit; la interfaz
puede mostrar el Markdown y las tres opciones con sus propios componentes.

Inmediatamente antes de aceptar una decisión, el controlador debe:

1. Comprobar que la revisión corresponde al borrador, investigación y métricas
   actuales mediante choose_review_route_for_context(..., calculated_metrics=metrics).
   Una ruta de corrección o bloqueo no permite solicitar la entrega.
2. Comprobar que la huella actual coincide con preview.draft_fingerprint. Si
   cambió el contenido mostrado, presentar y revisar la versión nueva.
3. Recibir una decisión humana explícita y las acciones seleccionadas.
4. Crear ApprovalRecord con run_id, la identidad y huella de preview, las
   acciones realmente autorizadas y decided_at con zona horaria.
5. Llamar a export_approved_report con el mismo borrador. Mostrar complete o
   partial y los errores; conservar DeliveryResult para reintentar lo pendiente.

El exportador vuelve a verificar la aprobación antes de escribir. Un cambio de
texto o cifra invalida una autorización antigua aunque no cambien ID y versión.
completed en el grafo no equivale a una entrega exportada ni sustituye ApprovalRecord.

## Contrato con análisis y revisión

La primera integración del constructor admite únicamente puntos de equilibrio
creados por metric_from_break_even(scenario, calculation). Hay que conservar su
contexto, los cuatro cálculos originales y sus supuestos/limitaciones en el estado.
Solo las métricas admitidas se pasan al constructor; las mismas deben acompañar
la revisión y el control de vigencia. No se reconstruyen métricas a mano.

La expansión a ingresos, resultados mensuales, gráficos y observaciones visuales
requiere un acuerdo de contrato y pruebas conjuntas. Las funciones de gráficos de
análisis no se insertan automáticamente en el PDF por existir en el repositorio.

## Verificación de esta entrega

- El punto de equilibrio usa el entero calculado por análisis, sin recalcularlo.
- La previsualización conserva cifras, contexto y huella sin mutar el borrador.
- Una vista previa no autoriza exportaciones.
- El recorrido con cálculo y revisión reales entrega Markdown, PDF y CSV
  para la misma huella. En los tests la aprobación es explícitamente simulada.
- El reintento no duplica archivos ni filas. Las pruebas existentes cubren fallos
  parciales, aprobaciones ausentes, negativas, antiguas y acciones no autorizadas.
- Las llamadas reales a Groq de PR #35 verificaron muestras guardadas y cálculos
  hipotéticos; no verifican el workflow completo de Persona 5.

```bash
python -m pytest tests/test_report_preview.py tests/test_report_delivery_integration.py tests/test_delivery.py -q
python -m pytest -q
```

La validación semántica final, la decisión humana y la prueba integrada de la
aplicación son responsabilidades compartidas. Esta entrega aporta el componente
reutilizable de previsualización y la API de entrega que deben consumir.

### Resultado de validación del cierre

- Base: dev con el PR #37 integrado.
- Suite completa: 509 pruebas pasadas (36 avisos de obsolescencia de CrewAI).
- Cinco casos nuevos de previsualización y entrega con métrica calculada.
- PDF de tres páginas generado por la prueba de entrega e inspeccionado
  visualmente: encabezados, punto de equilibrio, contexto, referencias y páginas
  legibles. El dato de 25 clientes y la autorización son sintéticos de prueba.
- No se ha ejecutado una nueva investigación ni una aprobación humana real.
