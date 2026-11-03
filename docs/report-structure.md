# Estructura común del informe

Los títulos y su orden se definen en src/reporting/templates.py.

El informe contiene once apartados:
resumen ejecutivo, objetivo y alcance, método y fuentes de datos,
público potencial, competencia, precios y servicios, análisis visual,
escenarios económicos, oportunidades y riesgos, incertidumbres
y próximos pasos.

Los renderizadores añaden por separado las fuentes, las limitaciones
y el registro de afirmaciones.

## Redactor con LLM

La tarea solicita los títulos comunes y un máximo de 600 palabras.
El límite de palabras es una instrucción, no una validación automática.

En el contrato actual, el modelo devuelve los cuerpos en once campos con los
títulos como claves; el código construye su orden. Los modelos GPT-OSS admitidos
usan esquema estricto y se mantienen las comprobaciones locales. Véanse los
detalles y las pruebas en [writer-groq-budget.md](writer-groq-budget.md).

Se rechazan respuestas con títulos ausentes, duplicados, adicionales,
desordenados o apartados sin contenido.

Los apartados sin información deben declararse pendientes.
La validación estructural no comprueba la veracidad del contenido.

## Redactor determinista

Reorganiza los apartados anteriores conservando su contenido.
Los apartados sin información muestran un aviso de pendiente.
Los títulos desconocidos provocan un error para evitar perder información.

## Cálculos

Los puntos de equilibrio se incorporan dentro de Escenarios económicos.
El texto numérico procede de las métricas y no lo recalcula el LLM.
Se conservan el contenido existente, los supuestos y las limitaciones.

## Validación

58 pruebas pasadas del conjunto seleccionado de redacción,
construcción, estructura, integración, presentación y entrega.

## Comprobación real con Groq

Se realiza una ejecución con CrewAI y Groq,
utilizando datos sintéticos y response_format={"type": "json_object"}.

La ejecución superó la validación de los once apartados y las referencias.
Conservó la identificación de datos ficticios, las limitaciones y la
pregunta pendiente sobre demanda. No interpretó coverage_percentage=0.0
como cobertura del mercado.

Una ejecución correcta no garantiza ausencia de fallos posteriores.
Quedan pendientes la validación con datos reales y el recorrido integrado
con análisis y workflow.
