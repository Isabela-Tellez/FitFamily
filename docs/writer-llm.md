# Redactor con LLM

## Estado actual

Integración de CrewAI con Groq para redactar un borrador
a partir de ResearchBrief y ResearchResult.

Se conserva el WriterAgent determinista existente.

El constructor permite elegir explícitamente el redactor con LLM.
Por defecto conserva el modo determinista para mantener compatibilidad.

La conexión con la interfaz y el flujo global está implementada
en la rama `integration/pr40-pr41-local`.

> **Ejecución real verificada el 4 de noviembre de 2026.** Se realizó una
> llamada real a Groq (modelo `groq/openai/gpt-oss-120b`) con investigación
> real mediante Tavily. El informe se generó correctamente (11 secciones,
> 19 afirmaciones) y pasó la revisión de calidad (0 incidencias).

## Configuración

Instalar las dependencias:

python -m pip install -r requirements.txt

Crear un archivo .env local usando .env.example como referencia:

GROQ_API_KEY=clave_privada
WRITER_LLM_MODEL=groq/openai/gpt-oss-120b

No compartir ni versionar la clave.

## Formato de respuesta del proveedor

El proveedor se configura con `response_format = {"type": "json_object"}`.
La validación estricta se realiza localmente mediante Pydantic
(`WritingResponse`, `extra="forbid"`, `strict=True`).

Motivo: con `json_schema` estricto, Groq rechazaba la respuesta del LLM
porque este la envolvía en un array `[{...}]` en lugar de un objeto
`{...}`. El esquema se validaba en el servidor y la respuesta nunca
llegaba al parser. Con `json_object` la respuesta llega y se valida
localmente.

El parser `parse_writing_output` normaliza de forma segura:
- Objeto JSON válido: se valida directamente.
- Array con un único objeto: se extrae ese objeto.
- Array vacío o con varios objetos: se rechaza (estructura ambigua).
- Contenido no-objeto: se rechaza con mensaje explicativo.
- Objeto con campos incorrectos: validación estricta (Pydantic).

La normalización no cambia valores, no completa campos y no oculta errores.

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