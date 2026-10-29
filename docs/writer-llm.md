# Redactor con LLM

## Estado actual (actualizado tras PR #30 y PR #35)

- PR #30 implementa `workflows.py`, `persistence.py` y conecta análisis, redacción y revisión.
- PR #35 corrige la redacción con LLM (CrewAI + Groq): solicita JSON, valida localmente, evita duplicar evidencias, divide investigaciones grandes en lotes, comprueba presupuesto de tokens y elimina `cache_breakpoint` (no admitido por Groq).
- 475 tests pasados. Ejecución real con Groq: 11 apartados, punto de equilibrio de 25 clientes, revisión con `pending_review`, sin incidencias automáticas.
- No concede aprobación humana ni exporta entregables (pendiente en workflow completo de Isabela).

El constructor permite elegir explícitamente el redactor con LLM.
Por defecto conserva el modo determinista para mantener compatibilidad.

La conexión con la interfaz (`streamlit`) sigue pendiente; el flujo global (`workflows.py`) está implementado (PR #30) y conecta la redacción con análisis y revisión.

> **Revisión documental del 26 de octubre de 2026.** No se ha ejecutado una llamada real a Groq. Las pruebas de esta revisión usan respuestas simuladas; la ejecución real descrita más abajo es histórica y no se ha reproducido. El CI no tiene una clave de proveedor.

## Configuración

Instalar las dependencias:

python -m pip install -r requirements.txt

Crear un archivo .env local usando .env.example como referencia:

GROQ_API_KEY=clave_privada
WRITER_LLM_MODEL=groq/openai/gpt-oss-120b

No compartir ni versionar la clave.

CrewAI utiliza el extra litellm.
Se fija litellm==1.88.6 porque la versión 1.106.2 instalada
intentaba importar CacheableResult, ausente en MCP 1.28.1.
La configuración corregida pasó las pruebas MCP del proyecto.

## Funciones

- build_writer_llm(): configura el cliente sin enviar una petición.
- build_writer(): construye el agente.
- build_writing_task(brief, research_result, agent): prepara la tarea.
- run_writing(brief, research_result): ejecuta CrewAI y devuelve ReportDraft.

run_writing realiza llamadas externas y consume la cuota de Groq.
No exporta archivos ni concede aprobación.

## Salida y comprobaciones

El LLM devuelve WritingOutput con secciones, afirmaciones y limitaciones.

El código de la aplicación crea el identificador del borrador,
su versión inicial y los identificadores de las afirmaciones.

Se rechazan:
- Respuestas sin la estructura esperada.
- Secciones o afirmaciones vacías.
- Hechos sin referencias.
- Referencias a evidencias inexistentes.
- Referencias con el prefijo access_attempt_.

Se conservan las preguntas pendientes de la investigación
y las limitaciones de las evidencias citadas.

## Validación histórica y cobertura actual

- Una ejecución real con datos ficticios produjo un borrador,
  conservó la cuota de 45 euros mensuales y su referencia,
  y dejó la disponibilidad de ludoteca como pendiente. Es un registro
  histórico, no una comprobación repetida en esta revisión.
- Esa ejecución interpretó incorrectamente coverage_percentage.
  Después se añadió una instrucción para evitar esa interpretación;
  queda pendiente comprobarla en otra ejecución real.
- Cuatro pruebas sin red validan la conversión y los rechazos.
- Las pruebas conjuntas seleccionadas y las pruebas MCP pasaron.
- En la suite actual, `tests/test_strategic_writer.py` cubre la ruta LLM
  con mocks; no acredita que el proveedor responda ni que el modelo
  real respete las referencias.

## Limitaciones

- Todavía no recibe el análisis financiero de Laura.
- Comprobar referencias no demuestra que respalden las frases.
- La estructura no garantiza que todas las afirmaciones del texto
  estén registradas individualmente.
- Los textos de fuentes se tratan como datos no confiables.
  Las instrucciones del prompt no garantizan evitar toda manipulación.
- Los límites del agente no constituyen un presupuesto global
  de tokens, coste o llamadas.
- No hay exportación ni aprobación accesibles como herramientas
  del agente.

## Integración con el constructor

Para obtener un ReportDraft redactado con el LLM:

build_report(brief, research_result, use_llm=True)

Para obtener directamente el texto Markdown:

build_report_markdown(brief, research_result, use_llm=True)

Ambas funciones están en src/reporting/report_builder.py.

Para renderizar un borrador que ya existe, sin volver a generarlo:

render_report_markdown(draft)

Si se omite use_llm, se utiliza el Writer determinista.
Si el LLM falla, el error se propaga: no se cambia de modo
automáticamente.

El controlador debe elegir el modo explícitamente. Para mostrar,
revisar, aprobar y exportar un mismo informe, debe conservar el
ReportDraft generado y renderizar ese objeto. No debe volver a
generarlo después de la aprobación.