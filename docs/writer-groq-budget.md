# Redactor con Groq: contexto y presupuesto

El redactor conserva CrewAI (Agent, Task y Crew), con salida JSON y validación
local mediante WritingOutput. No utiliza output_pydantic: así se evita que la
conversión interna genere una segunda llamada con herramientas. Un JSON inválido
se rechaza sin repararlo ni volver a consultar al modelo para convertirlo.

## Contexto sin duplicados

writer_payload.py crea un catálogo de evidencias por evidence_id. Los competidores
las enlazan por identificador. Se conservan los campos de la investigación y del
encargo, incluidos fragmentos, valores, unidades, periodicidad, fechas, ámbito,
fuentes, limitaciones, preguntas pendientes y notas. Solo se omiten campos null.
El contrato compartido y la investigación original no se modifican.

Un identificador con dos contenidos diferentes provoca un error antes de redactar.

## Investigaciones grandes

Se mide localmente el texto de la tarea con el contador de LiteLLM. Por encima de
3000 tokens se divide por competidor y por evidencias generales independientes.
Se conservan todos los registros; no se seleccionan solo los primeros ni se
truncan textos. Los metadatos del método, notas y preguntas acompañan cada lote.

Cada respuesta se valida contra las referencias de su lote. Los apartados se
combinan de forma determinista bajo los once títulos originales, marcando los
bloques como contexto parcial. Se conservan referencias, fuentes y limitaciones,
y se renumeran las afirmaciones. Esta combinación no es una síntesis global.
El constructor incorpora después los cálculos una sola vez.

Si el encargo/notas o un registro individual no caben, se devuelve un error claro
antes de generar ningún lote. Ese caso requiere un resumen trazable preparado
explícitamente; no se oculta información para conseguir que la petición quepa.

## Protección de la petición real

Un hook elimina cache_breakpoint, marca interna de CrewAI no admitida por Groq.
Para el agente redactor, comprueba además los mensajes finales que añade CrewAI.
El límite de 7600 tokens incluye la reserva de salida de 4096 y deja margen frente
a los 8000 TPM observados. Una petición excesiva se bloquea antes del proveedor.

Las peticiones del redactor en el mismo proceso reservan presupuesto en una
ventana de 61 segundos. Los lotes pueden requerir esperas; no se lanzan en paralelo.
Se desactivan los reintentos automáticos del agente ante errores de ejecución.
El presupuesto local no conoce el consumo de otros procesos o personas con la
misma cuenta: aún puede haber un límite externo de Groq o errores transitorios.
El contador local es una estimación del proveedor, no una garantía de cuota.

## Verificación (29 de octubre de 2026)

- 23 pruebas enfocadas: redactor, estructura y nueve pruebas nuevas de presupuesto.
- Caso de 100 registros: todos se reparten en tareas dentro del límite sin perder
  evidencias ni contexto. Se prueban también conflictos, registro individual
  excesivo, combinación, JSON inválido, hook y espera del presupuesto.
- Llamada real a Groq con tres registros del archivo municipal guardado, en dos
  lotes, más un escenario económico hipotético: once apartados, siete afirmaciones,
  tres fuentes y punto de equilibrio de 25 clientes. Revisión y ruta:
  pending_review, sin incidencias automáticas.

Esta comprobación usa build_report y el revisor con las mismas métricas; no es
una ejecución completa del workflow de Isabela ni valida la verdad del informe.
No concede aprobación humana ni exporta entregables. Falta repetir el workflow
completo de Isabela con estos cambios y el LLM real.

Pruebas locales, desde la raíz del repositorio:

```bash
python -m pytest tests/test_strategic_writer.py tests/test_report_templates.py tests/test_writer_prompt_budget.py -q
```

Comprobación manual con el proveedor (usa la clave configurada, consume cuota y
puede esperar entre lotes; no consulta webs ni exporta):

```bash
python scripts/check_writer_groq.py --plan-only
python scripts/check_writer_groq.py
```
