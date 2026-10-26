# Exportación de informes

> Revisión documental: **26 de octubre de 2026**. La exportación Markdown y PDF está implementada a nivel de API. La interfaz que recoge la aprobación humana y la actualización de un CSV de seguimiento **no** están implementadas.

## Estado actual

- `export_markdown()` y `export_pdf()` validan un `ApprovalRecord` y publican un archivo.
- `render_report_markdown()` y `render_report_pdf()` generan contenido en memoria y **no** validan aprobaciones.
- No hay UI, controlador global ni botón de aprobación.
- La acción `update_tracking_csv` está reservada y no tiene función de exportación.

## Responsabilidades

- El redactor prepara el `ReportDraft`; no concede aprobación.
- El controlador muestra el borrador y recibe la decisión humana.
- El controlador crea el `ApprovalRecord` con esa decisión.
- El exportador comprueba el registro antes de escribir el archivo.

Crear un `ApprovalRecord` no demuestra por sí mismo que haya existido una aprobación humana. El controlador debe garantizar su procedencia.

## Registro de aprobación

`ApprovalRecord` se encuentra en `src/automation/models.py` y es un dataclass congelado:

```python
@dataclass(frozen=True)
class ApprovalRecord:
    run_id: str
    draft_id: str
    draft_version: int
    draft_fingerprint: str
    approved: bool
    actions: tuple[str, ...]
    decided_at: datetime
```

Campos:

- `run_id`: identificador de la ejecución.
- `draft_id`: identificador del borrador mostrado.
- `draft_version`: versión mostrada.
- `draft_fingerprint`: huella del contenido revisado.
- `approved`: decisión humana.
- `actions`: acciones autorizadas.
- `decided_at`: fecha de la decisión, con zona horaria.

Las acciones implementadas son `export_markdown` y `export_pdf`. Cada formato requiere su propia autorización en `actions`. La acción `update_tracking_csv` está reconocida por el validador como nombre permitido, pero no existe una función que la ejecute.

## Vinculación con el borrador

La huella se calcula mediante:

```python
calculate_draft_fingerprint(draft)
```

El controlador debe conservar la huella del borrador que mostró a la persona usuaria. Si el borrador cambia después, se requiere una nueva aprobación aunque se conserve el mismo `draft_id`.

La huella incluye todos los campos serializables del `ReportDraft`, incluido su `draft_id`. Por eso el exportador comprueba también la identidad y la versión del borrador.

## Uso del exportador

Las funciones públicas de `src/automation/exporter.py` son:

```python
export_markdown(draft, approval, run_id, output_dir) -> Path
export_pdf(draft, approval, run_id, output_dir) -> Path
```

Ejemplo mínimo:

```python
from datetime import datetime, timezone
from pathlib import Path

from src.automation.exporter import (
    calculate_draft_fingerprint,
    export_markdown,
)
from src.automation.models import ApprovalRecord

approval = ApprovalRecord(
    run_id="run-2026-10-26",
    draft_id=draft.draft_id,
    draft_version=draft.version,
    draft_fingerprint=calculate_draft_fingerprint(draft),
    approved=True,
    actions=("export_markdown",),
    decided_at=datetime.now(timezone.utc),
)

path = export_markdown(
    draft,
    approval,
    run_id=approval.run_id,
    output_dir=Path("reports/generated"),
)
```

`output_dir` lo configura el controlador y debe ser una carpeta de salida permitida. No debe obtenerse del contenido web ni de una respuesta del LLM.

## Rechazos

El exportador lanza `ValueError` si:

- Falta la aprobación o es negativa.
- La ejecución, el borrador o la versión no coinciden.
- La huella indica que ha cambiado el contenido.
- La acción no está autorizada o no es reconocida.
- La fecha de decisión no incluye zona horaria.
- Ya existe un archivo diferente para la misma operación.

Los errores de escritura se propagan como `OSError`. El controlador debe comunicar el fallo sin mostrar éxito.

## Repeticiones y escritura

La operación se identifica por ejecución, borrador, versión y acción. Repetirla devuelve el archivo existente si coincide con el contenido esperado. Nunca sobrescribe un archivo diferente.

Se escribe primero un temporal en la carpeta de salida y después se publica mediante un enlace duro. Si la operación termina o falla con una excepción controlada, se elimina el temporal. El sistema de archivos debe admitir enlaces duros. No se garantiza la limpieza de temporales tras un apagado brusco.

## Presentación

La vista previa muestra el estado de borrador pendiente de revisión y aprobación. Tras validar la aprobación, los exportadores Markdown y PDF muestran el estado de aprobado para exportación.

El estado mostrado no concede autorización: el exportador comprueba el registro de aprobación antes de guardar el documento.

## Exportación PDF

`export_pdf(draft, approval, run_id, output_dir)` genera y publica un PDF del mismo `ReportDraft` revisado y aprobado. Requiere que la aprobación autorice expresamente `export_pdf`; una autorización para Markdown no permite exportar PDF.

Antes de generar el documento o crear la carpeta, comprueba la ejecución, el identificador, la versión y la huella del borrador. El documento incluye secciones, fuentes, limitaciones, registro de afirmaciones y páginas numeradas. Utiliza ReportLab y fuentes incluidas en la dependencia.

La publicación utiliza un archivo temporal y enlaces duros, con las mismas restricciones del exportador Markdown. Un reintento devuelve el archivo existente si sus bytes coinciden; si son diferentes, se rechaza sin sobrescribirlo. La reproducción de los mismos bytes se comprueba en el mismo entorno; cambiar las dependencias puede cambiar el PDF generado.

`render_report_pdf` genera bytes en memoria y no valida aprobaciones. Su parámetro `approved` solo controla el estado mostrado. La autorización se comprueba en `export_pdf`.

## Pruebas

Ejecutar desde la raíz del proyecto:

```bash
python -m pytest tests/test_pdf_exporter.py tests/test_exporter.py tests/test_markdown_renderer.py -q
```

Las pruebas comprueban aprobación, huella, creación de archivos, repeticiones, rechazo de sobrescrituras y reintento de publicación Markdown tras un fallo simulado. Para PDF también comprueban que la generación no modifique el borrador y produzca los mismos bytes en el mismo entorno.

La suite no hace una revisión visual automatizada del PDF ni valida tipografías en un visor externo.
