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

## Estado

Implementados el almacenamiento, la validación al crear la afirmación
y las pruebas de invalidación de aprobación.

Pendientes:
- Recibir los resultados estructurados del análisis.
- Generar el texto numérico de forma coherente con estos campos.
- Mostrar las referencias numéricas en Markdown y PDF.
- Comparar valor y unidad con el análisis desde el revisor.
- Acordar el tratamiento del redondeo entre los tres módulos.

La validación al crear la afirmación no impide modificaciones posteriores
del objeto. La comprobación de la huella detecta esos cambios frente
a una aprobación previa.