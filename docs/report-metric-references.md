# Referencias numéricas del informe

ReportClaim admite tres campos opcionales:

- metric_id: identificador del resultado de análisis citado.
- reported_value: valor numérico utilizado en el informe.
- reported_unit: unidad del valor utilizado.

Los tres campos deben estar ausentes o informados conjuntamente.
El identificador y la unidad no pueden estar vacíos.
El valor debe ser un número finito; no se admiten booleanos.

Las afirmaciones existentes pueden conservar los tres campos en None.
Un resultado no disponible se explica como limitación, sin inventar
una cifra ni sustituirlo por cero.

Estos campos forman parte de la huella del borrador. Cambiar cualquiera
de ellos invalida una aprobación anterior.

## Presentación

Markdown y PDF muestran metric_id, reported_value y reported_unit
en el registro de afirmaciones cuando la afirmación tiene una métrica.

La presentación no recalcula valores, no modifica el borrador
ni sustituye la revisión numérica.

Verificación: pruebas de ambos formatos y revisión visual de un PDF
con datos ficticios.

## Estado

Implementados el almacenamiento, la validación al crear la afirmación
y las pruebas de invalidación de aprobación.

Para el punto de equilibrio ya se reciben los resultados estructurados mediante
metric_from_break_even(), se genera texto coherente desde la misma métrica y el
revisor compara el valor y la unidad con el cálculo original. Markdown y PDF
muestran esos campos; la previsualización conserva la huella del borrador.

Se usa el entero de clientes calculado por el módulo de análisis, sin un nuevo
redondeo en redacción. Otras métricas y sus reglas de presentación requieren
ampliar el contrato con análisis y revisión; no forman parte de esta integración.

La validación al crear la afirmación no impide modificaciones posteriores
del objeto. La comprobación de la huella detecta esos cambios frente
a una aprobación previa.
