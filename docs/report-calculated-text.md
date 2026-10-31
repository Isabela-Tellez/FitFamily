# Texto generado desde cálculos

build_report() y build_report_markdown() admiten el argumento opcional
calculated_metrics.

La primera integración admite únicamente métricas del punto de equilibrio
creadas mediante metric_from_break_even().

## Comportamiento

- El texto y los campos numéricos se generan desde la misma métrica.
- No se repite la fórmula económica ni se pide al LLM que calcule la cifra.
- La afirmación se identifica como inferencia.
- Se conservan las referencias a evidencias.
- Se incorporan los supuestos y las limitaciones mediante metric_context_notes().
- Un resultado no disponible se declara como limitación; no se convierte en cero.
- Se rechazan identificadores de métricas duplicados.
- Los informes sin métricas mantienen su comportamiento anterior.

Con use_llm=True, el redactor genera el contenido de investigación y después
el constructor añade el texto calculado de forma determinista.

## Integración

El controlador debe conservar las métricas actuales y el mismo ReportDraft.
Debe pasar esas métricas tanto a run_basic_review() como a
choose_review_route_for_context() mediante calculated_metrics.

El constructor no sustituye la validación del cálculo y su procedencia
que realiza el revisor. Tampoco concede aprobación ni exporta archivos.

## Estado de entrega (31 de octubre de 2026)

Markdown y PDF ya muestran la métrica, el valor declarado y la unidad. La
previsualización reutilizable está disponible en src/ui/report_preview.py.
La ejecución real de scripts/check_writer_groq.py ha comprobado el constructor
y el revisor con una muestra municipal guardada y un escenario hipotético;
no es una ejecución completa del workflow ni una validación de viabilidad.

Quedan como integración del equipo: otros tipos de cálculo, datos visuales y
gráficos, la interfaz y el controlador global. El contrato de esta primera
entrega sigue limitado al punto de equilibrio con su contexto original.
Véase [reporting-handoff.md](reporting-handoff.md).
