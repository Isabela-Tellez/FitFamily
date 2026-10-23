# Exportación de informes

## Estado actual

Se puede exportar un ReportDraft a Markdown después de comprobar
un registro de aprobación.

Todavía no están implementadas la conexión con la interfaz,
la exportación PDF ni la actualización del CSV.

## Responsabilidades

- El redactor prepara el ReportDraft; no concede aprobación.
- El controlador muestra el borrador y recibe la decisión humana.
- El controlador crea ApprovalRecord con esa decisión.
- El exportador comprueba el registro antes de escribir el archivo.

Crear un ApprovalRecord no demuestra por sí mismo que haya existido
una aprobación humana. El controlador debe garantizar su procedencia.

## Registro de aprobación

ApprovalRecord se encuentra en src/automation/models.py.

Contiene:

- run_id: identificador de la ejecución.
- draft_id: identificador del borrador mostrado.
- draft_version: versión mostrada.
- draft_fingerprint: huella del contenido mostrado.
- approved: decisión humana.
- actions: tupla con las acciones autorizadas.
- decided_at: fecha de la decisión con zona horaria.

Las acciones disponibles actualmente son `export_markdown` y `export_pdf`.
Cada formato requiere su propia autorización en `actions`.

La acción `update_tracking_csv` está reservada para una siguiente
entrega; todavía no tiene implementación.

## Vinculación con el borrador

La huella se calcula mediante:

calculate_draft_fingerprint(draft)

El controlador debe conservar la huella del borrador mostrado.
No debe recalcularla sobre un contenido modificado y utilizar
la aprobación anterior.

Si cambia el borrador, se requiere una nueva aprobación.

## Uso del exportador

Las funciones públicas de src/automation/exporter.py son:

- `export_markdown(draft, approval, run_id, output_dir)`
- `export_pdf(draft, approval, run_id, output_dir)`

Ambas devuelven la ruta del archivo generado.

output_dir lo configura el controlador y debe ser una carpeta
de salida permitida, por ejemplo reports/generated.
No debe obtenerse del contenido web ni de una respuesta del LLM.

## Rechazos

El exportador lanza ValueError si:

- Falta la aprobación o es negativa.
- La ejecución, el borrador o la versión no coinciden.
- La huella indica que ha cambiado el contenido.
- La acción no está autorizada o no es reconocida.
- La fecha de decisión no incluye zona horaria.
- Ya existe un archivo diferente para la misma operación.

Los errores de escritura se propagan como OSError.
El controlador debe comunicar el fallo sin mostrar éxito.

## Repeticiones y escritura

La operación se identifica por ejecución, borrador, versión y acción.

Repetirla devuelve el archivo existente si coincide con el contenido
esperado. Nunca sobrescribe un archivo diferente.

Se escribe primero un temporal en la carpeta de salida y después
se publica mediante un enlace de archivo. Si la operación termina
o falla con una excepción controlada, se elimina el temporal.

El sistema de archivos debe admitir enlaces duros.
No se garantiza la limpieza de temporales tras un apagado brusco.

## Presentación

La vista previa muestra el estado de borrador pendiente de revisión
y aprobación. Tras validar la aprobación, los exportadores Markdown
y PDF muestran el estado de aprobado para exportación.

El estado mostrado no concede autorización: el exportador comprueba
el registro de aprobación antes de guardar el documento.

## Exportación PDF

`export_pdf(draft, approval, run_id, output_dir)` genera y publica
un PDF del mismo `ReportDraft` revisado y aprobado.

Requiere que la aprobación autorice expresamente `export_pdf`.
Una autorización para Markdown no permite exportar PDF.

Antes de generar el documento o crear la carpeta, comprueba la
ejecución, el identificador, la versión y la huella del borrador.

El documento incluye secciones, fuentes, limitaciones, registro de
afirmaciones y páginas numeradas. Utiliza ReportLab y fuentes
incluidas en la dependencia.

La publicación utiliza un archivo temporal y enlaces duros,
con las mismas restricciones del exportador Markdown.
Un reintento devuelve el archivo existente si sus bytes coinciden;
si son diferentes, se rechaza sin sobrescribirlo.

La reproducción de los mismos bytes se comprueba en el mismo
entorno. Cambiar las dependencias puede cambiar el PDF generado.

`render_report_pdf` genera bytes en memoria y no valida aprobaciones.
Su parámetro `approved` solo controla el estado mostrado.
La autorización se comprueba en `export_pdf`.

## Pruebas

Ejecutar desde la raíz del proyecto:

```bash
python -m pytest tests/test_pdf_exporter.py tests/test_exporter.py tests/test_markdown_renderer.py -q
```

Las pruebas comprueban aprobación, huella, creación de archivos,
repeticiones, rechazo de sobrescrituras y reintento de publicación
Markdown tras un fallo simulado.

Para PDF también comprueban que la generación no modifique el
borrador y produzca los mismos bytes en el mismo entorno.

La revisión visual del ejemplo comprobó tildes, eñes, símbolo €,
márgenes, saltos de página y numeración.