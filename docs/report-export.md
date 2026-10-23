# Exportación de informes

## Estado actual

Se puede exportar un ReportDraft a Markdown después de comprobar
un registro de aprobación.

Todavía no están implementadas la conexión con la interfaz,
la exportación PDF ni la actualización del CSV.

## Responsabilidades

- El WriterAgent prepara el borrador; no concede aprobación.
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

La acción disponible actualmente es export_markdown.

export_pdf y update_tracking_csv están reservadas para las
siguientes entregas; todavía no tienen implementación.

## Vinculación con el borrador

La huella se calcula mediante:

calculate_draft_fingerprint(draft)

El controlador debe conservar la huella del borrador mostrado.
No debe recalcularla sobre un contenido modificado y utilizar
la aprobación anterior.

Si cambia el borrador, se requiere una nueva aprobación.

## Uso del exportador

La función pública es:

export_markdown(draft, approval, run_id, output_dir)

Devuelve la ruta del archivo generado.

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

El Markdown conserva actualmente el aviso de borrador pendiente
de revisión y aprobación incluido por el renderer.

La autorización para exportarlo se comprueba por separado.
La presentación del estado final queda pendiente de integración.

## Pruebas

Ejecutar:

python -m pytest tests/test_exporter.py -q

Incluyen huella, aprobación, creación del archivo, repetición,
conflictos y reintento tras un fallo simulado.