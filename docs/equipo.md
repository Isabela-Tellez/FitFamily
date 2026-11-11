# Componentes y responsabilidades

Los créditos del equipo se encuentran en la [portada del proyecto](../README.md). Esta guía organiza las responsabilidades por módulo.

| Área | Responsabilidad | Código y documentación |
|---|---|---|
| Investigación y fuentes | Recopila evidencias web y municipales, registra competidores y publica indicadores locales mediante MCP. | [Investigación](research-module.md) · [Auditoría de fuentes](auditoria-fuentes-datos.md) |
| Análisis económico y visual | Calcula ingresos, costes variables, resultado mensual y punto de equilibrio. Genera gráficos y admite observaciones sobre imágenes. | [Análisis](analysis.md) · [Multimodalidad](multimodal.md) |
| Redacción e informes | Construye borradores a partir de la investigación y las métricas. Presenta supuestos, resultados, evidencias y limitaciones en la vista previa, Markdown y PDF. | [Redactor Groq](writer-llm.md) · [Entrega](report-export.md) |
| Revisión | Comprueba la procedencia y coherencia de las cifras y la vigencia de la revisión frente al borrador, la investigación y el análisis. | [Revisión y calidad](review-quality.md) |
| Orquestación e interfaz | Coordina estudios mediante LangGraph, guarda su estado en SQLite y presenta los resultados en FitFamily Studio. Gestiona la decisión humana y la entrega autorizada. | [Workflow](langgraph-flow.md) · [Aprobación y entrega](streamlit-approval.md) |

Studio arranca con `python -m streamlit run src/ui/app.py`. El controlador vincula la aprobación a la versión y la huella de la vista previa. La entrega ejecuta las acciones autorizadas de Markdown, PDF y seguimiento CSV.

La [demostración local](demo-review.md) permite comprobar la revisión con datos ficticios. El [README](../README.md#demostración-y-resultados) documenta la prueba de redacción con Groq sobre una muestra guardada.
