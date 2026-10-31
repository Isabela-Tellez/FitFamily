# Streamlit y aprobación humana

Responsable: **Isabella (Persona 5)**.

> **Estado: aplicación pendiente.** No existe todavía una aplicación Streamlit en `dev`. `src/ui/report_preview.py` aporta un adaptador reutilizable con Markdown, identidad, huella y opciones de entrega; no implementa la aplicación ni una segunda aprobación. Este documento fija el contrato que debe respetar la interfaz al integrarse.

## Objetivo

Dar a la persona usuaria una vista única del flujo —investigación, análisis, borrador, revisión— y recoger una **decisión humana explícita** antes de exportar. La interfaz no puede aprobar por defecto ni exportar sin `ApprovalRecord`.

## Lo que ya existe (no hay que reimplementarlo)

| Pieza | Archivo | Uso desde la UI |
|---|---|---|
| `render_report_preview` | `src/ui/report_preview.py` | Mostrar una instantánea del borrador y las opciones de entrega |
| `ApprovalRecord` | `src/automation/models.py` | Registrar la decisión humana |
| `calculate_draft_fingerprint` | `src/automation/exporter.py` | Ligar la aprobación al contenido exacto |
| `validate_export_approval` | `src/automation/exporter.py` | Validar la autorización antes de exportar |
| `export_markdown` | `src/automation/exporter.py` | Publicar Markdown |
| `export_pdf` | `src/automation/exporter.py` | Publicar PDF |
| `run_basic_review` | `src/review/quality_checks.py` | Mostrar incidencias antes de aprobar |
| `choose_review_route` | `src/graph/review_routes.py` | Decidir si toca corregir o pasar a revisión |

## Contrato de aprobación

```python
ApprovalRecord(
    run_id="run-001",
    draft_id=draft.draft_id,
    draft_version=draft.version,
    draft_fingerprint=calculate_draft_fingerprint(draft),
    approved=True,
    actions=("export_markdown", "export_pdf"),
    decided_at=datetime.now(timezone.utc),
)
```

Reglas que la UI debe cumplir:

1. Mostrar el borrador y el `ReviewResult` **antes** de pedir la decisión.
2. No crear un `ApprovalRecord` con `approved=True` sin una acción explícita de la persona usuaria.
3. Calcular la huella con el borrador que se está mostrando; si el borrador cambia, la aprobación anterior deja de ser válida.
4. Autorizar solo las acciones seleccionadas (`export_markdown`, `export_pdf`, `update_tracking_csv`).
5. Usar `decided_at` con zona horaria; el exportador rechaza fechas sin `tzinfo`.
6. No exportar si `ReviewResult.status == "needs_revision"` o si `choose_review_route` devuelve una ruta de corrección.
7. No permitir que la UI escriba directamente en `reports/generated`: debe llamar a `export_markdown`/`export_pdf`.
8. Mantener el `run_id` estable durante toda la ejecución.

## Pantallas propuestas

| Pantalla | Contenido | Datos |
|---|---|---|
| 1. Brief | Formulario de `ResearchBrief` | `business_type`, `location`, `study_area`, `questions`, límites |
| 2. Investigación | Evidencias, competidores, fuentes y preguntas sin resolver | `ResearchResult` |
| 3. Análisis | Resumen de competidores y escenarios | Salida de Laura |
| 4. Borrador y revisión | Texto del informe + incidencias por severidad y etapa | `ReportDraft`, `ReviewResult` |
| 5. Aprobación | Casillas de acciones, comentario y botón de decisión | `ApprovalRecord` |
| 6. Exportación | Rutas de los archivos y confirmación | `export_markdown`, `export_pdf` |

## Flujo de aprobación

```text
[Streamlit]
    │
    ├── 1. Recoger ResearchBrief
    ├── 2. Ejecutar investigación y análisis
    ├── 3. Generar ReportDraft
    ├── 4. Ejecutar run_basic_review
    │
    ├── ¿ReviewResult.status == "needs_revision"?
    │       ├── Sí → mostrar incidencias y ruta de corrección
    │       └── No → habilitar pantalla de aprobación
    │
    ├── 5. La persona usuaria decide: aprobar / rechazar / corregir
    │
    ├── 6. Si aprueba:
    │       ApprovalRecord(
    │           run_id, draft_id, draft_version,
    │           calculate_draft_fingerprint(draft),
    │           approved=True,
    │           actions=seleccionadas,
    │           decided_at=now(timezone.utc),
    │       )
    │
    └── 7. export_markdown / export_pdf
             └── mostrar ruta publicada
```

## Criterios de aceptación

- [ ] La app arranca con `streamlit run src/ui/app.py` (o la ruta que se acuerde).
- [ ] Se puede recorrer el flujo sin editar código.
- [ ] El botón de aprobación está deshabilitado mientras `status == "needs_revision"`.
- [ ] Rechazar una aprobación no genera archivos.
- [ ] Cambiar el borrador después de aprobar invalida la exportación (la huella no coincide).
- [ ] Se muestran las incidencias con `code`, `message` y `correction_stage`.
- [ ] Se muestran las rutas finales de Markdown/PDF.
- [ ] Hay pruebas del flujo de aprobación y de los casos de rechazo.
- [ ] `streamlit` se añade a `requirements.txt` solo cuando la app exista.

## Dependencias y decisiones pendientes

- Añadir `streamlit` a `requirements.txt`.
- Decidir si el estado de la sesión se guarda en `st.session_state` o en un checkpointer de LangGraph.
- Acordar con Gema el formato exacto de `ApprovalRecord` y con María el renderizado de `ReviewResult`.
- Definir si la UI permite editar el borrador o solo aprobarlo/rechazarlo.

## Referencias

- [review-quality.md](review-quality.md) — incidencias y rutas de María.
- [report-export.md](report-export.md) — contrato de exportación de Gema.
- [langgraph-flow.md](langgraph-flow.md) — orquestación propuesta.
