# Redactor con Groq: contexto y presupuesto

El redactor conserva CrewAI (Agent, Task y Crew), con salida JSON y validación
local del contrato de transporte y de WritingOutput. No utiliza output_pydantic: así se evita que la
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

Se mide localmente el texto de la tarea y el esquema de salida con el contador de LiteLLM. Por encima de
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
El recuento de los mensajes finales incluye también el response_format efectivo.

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
python -m pytest tests/test_strategic_writer.py tests/test_report_templates.py tests/test_writer_prompt_budget.py tests/test_writer_fixed_sections.py -q
```

Comprobación manual con el proveedor (usa la clave configurada, consume cuota y
puede esperar entre lotes; no consulta webs ni exporta):

```bash
python scripts/check_writer_groq.py --plan-only
python scripts/check_writer_groq.py
```

## Revisión de estructura del PR #35 (30 de octubre de 2026)

La revisión señaló un fallo en la comprobación final de once apartados. La
ejecución previa a esta revisión local terminó correctamente; no se ha podido
reproducir ese fallo concreto sin los títulos o traceback de la ejecución señalada.
Se refuerza el contrato para evitar que el modelo decida el número y orden de títulos.

- `sections` pasa a ser un objeto con los once títulos como claves obligatorias.
  El código construye la lista ordenada de apartados. No rellena campos ausentes
  ni descarta claves adicionales o duplicadas. Se mantiene la validación local
  del contenido no vacío y la compatibilidad con listas de respuestas anteriores.
- Para `groq/openai/gpt-oss-120b` y `groq/openai/gpt-oss-20b` se envía un esquema
  estricto. Otros modelos conservan JSON mode y la validación local. El soporte
  está documentado en [Groq](https://console.groq.com/docs/structured-outputs).
- CrewAI 1.15.28 solo admite json_object en su campo tipado response_format.
  El esquema se pasa a LiteLLM mediante additional_params, que prevalece en la
  petición. Una prueba construye el cliente instalado e inspecciona esa petición,
  sin API, para detectar incompatibilidades que los mocks no cubren.
- La prueba manual compara los títulos y el contenido con el contrato compartido,
  después de incorporar las métricas, e informa del número y los títulos reales.
  Ya no depende de un assert genérico ni del número 11 escrito por separado.
- `--plan-only` no construye un cliente ni necesita una clave; las rutas se
  resuelven desde el script. Con este esquema el plan actual da 3 lotes para la
  muestra y 12 para los 18 registros. Los tamaños cambian con el contrato y los
  datos; no son una condición de aceptación. Se conservan todos los registros.

Diez pruebas nuevas cubren campos fuera de orden, ausentes, extra, vacíos,
de tipo incorrecto o duplicados; esquema, compatibilidad del cliente, diagnóstico
final y recorrido de dos lotes + constructor + cálculo + revisión. En este último
se simula solo el límite LLM: los once apartados permanecen y el cálculo aparece
una sola vez. El workflow completo de Isabela sigue siendo una comprobación aparte.

Validación final de esta revisión:
- Suite completa después de incorporar el PR #36 de Laura: 498 pruebas pasadas.
- Groq real con el esquema estricto: once títulos correctos, catorce afirmaciones,
  tres fuentes y punto de equilibrio hipotético de 25 clientes. Revisión y ruta
  pending_review, sin incidencias automáticas. Sin aprobación ni exportación.
- La ejecución real valida el constructor y revisor con la muestra guardada;
  no sustituye la prueba del workflow completo de Isabela.
