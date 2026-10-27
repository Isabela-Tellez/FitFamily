from src.reporting.numeric_text import render_claim, render_section
"""Genera la presentación PDF de un informe sin guardar archivos."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from src.reporting.models import ReportDraft


def _register_fonts() -> None:
    """Registra las fuentes que utilizaremos en el documento."""
    # Usamos fuentes incluidas en ReportLab para no depender
    # de las que tenga instaladas cada compañero.
    font_directory = Path(reportlab.__file__).parent / "fonts"

    for name, filename in (
        ("FitFamily", "Vera.ttf"),
        ("FitFamily-Bold", "VeraBd.ttf"),
    ):
        # Evitamos registrar la misma fuente en cada generación.
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(name, str(font_directory / filename))
            )


def _paragraph_text(text: str) -> str:
    """Prepara el contenido para mostrarlo como texto."""
    # Paragraph interpreta algunas etiquetas. Escapamos caracteres
    # como < y > para que el contenido del informe no se interprete
    # como instrucciones de formato.
    # Después convertimos los saltos de línea al formato de Paragraph.
    return escape(text).replace("\n", "<br/>")


def _draw_page_number(canvas: Canvas, document) -> None:
    """Añade el número de página al pie del documento."""
    # Guardamos el estado del dibujo para que el color y la fuente
    # del pie no alteren el contenido del informe.
    canvas.saveState()
    canvas.setFont("FitFamily", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(
        A4[0] - document.rightMargin,
        1.2 * cm,
        f"Página {document.page}",
    )
    canvas.restoreState()


def _deterministic_canvas(*args, **kwargs) -> Canvas:
    """Evita introducir fechas e identificadores variables."""
    # Con la misma entrada y el mismo entorno buscamos obtener
    # los mismos bytes, facilitando las comprobaciones de duplicados.
    kwargs["invariant"] = True
    return Canvas(*args, **kwargs)


def render_report_pdf(
    draft: ReportDraft,
    *,
    approved: bool = False,
) -> bytes:
    """
    Convierte un ReportDraft en los bytes de un PDF.

    No modifica el borrador ni escribe archivos.
    approved solo cambia el estado mostrado en el documento:
    el exportador debe comprobar la autorización antes de guardarlo.
    """
    _register_fonts()

    # Definimos una presentación común para título, apartados y texto.
    # leading controla la separación entre líneas.
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="FitFamily-Bold",
        fontSize=18,
        leading=23,
        alignment=TA_CENTER,
        spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="ReportHeading",
        fontName="FitFamily-Bold",
        fontSize=12,
        leading=16,
        spaceBefore=14,
        spaceAfter=8,
        # Intentamos mantener el título junto al contenido siguiente.
        keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        name="ReportBody",
        fontName="FitFamily",
        fontSize=10,
        leading=15,
        spaceAfter=8,
        # Permite dividir textos largos, como algunas direcciones web.
        splitLongWords=True,
    ))

    # ReportLab coloca estos elementos en orden y distribuye
    # el contenido entre las páginas disponibles.
    story = []

    def add_text(text: str, style: str = "ReportBody") -> None:
        """Añade un párrafo utilizando los estilos del informe."""
        story.append(
            Paragraph(_paragraph_text(text), styles[style])
        )

    # Conservamos los datos del borrador para identificar exactamente
    # qué informe y qué versión se están mostrando.
    add_text(draft.title, "ReportTitle")
    add_text(f"Zona de estudio: {draft.study_area}")
    add_text(f"Identificador del borrador: {draft.draft_id}")
    add_text(f"Versión: {draft.version}")

    status = (
        "aprobado para exportación."
        if approved
        else "borrador pendiente de revisión y aprobación."
    )
    add_text(f"Estado: {status}")
    story.append(Spacer(1, 0.3 * cm))

    # Seguimos el formato actual de ReportDraft:
    # la primera línea de cada sección contiene su título.
    for section in draft.sections:
        clean_section = render_section(section, draft.claims).strip()
        if not clean_section:
            continue

        heading, _, body = clean_section.partition("\n")
        add_text(heading, "ReportHeading")

        # Los párrafos separados permiten repartir el contenido
        # entre páginas sin tratar toda la sección como un bloque.
        for paragraph in body.split("\n\n"):
            if paragraph.strip():
                add_text(paragraph.strip())

    # Eliminamos duplicados al mostrar las fuentes, manteniendo
    # su orden original y sin modificar la lista del borrador.
    add_text("Fuentes", "ReportHeading")
    for source in dict.fromkeys(draft.sources):
        add_text(source)
    if not draft.sources:
        add_text("No se han registrado fuentes.")

    # Conservamos las limitaciones para que también estén presentes
    # en el documento que recibe la persona usuaria.
    add_text("Limitaciones", "ReportHeading")
    for limitation in dict.fromkeys(draft.limitations):
        add_text(limitation)
    if not draft.limitations:
        add_text(
            "No se han registrado limitaciones. "
            "Esto no implica que el estudio carezca de ellas."
        )

    # Mostramos las afirmaciones y sus referencias para mantener
    # la trazabilidad disponible en el borrador.
    add_text("Registro de afirmaciones", "ReportHeading")
    kind_labels = {
        "fact": "Afirmación factual",
        "assumption": "Supuesto",
        "inference": "Inferencia",
    }

    for claim in draft.claims:
        add_text(claim.claim_id, "ReportHeading")
        add_text(f"Tipo: {kind_labels.get(claim.kind, claim.kind)}")
        add_text(render_claim(claim))
        references = ", ".join(dict.fromkeys(claim.evidence_ids))
        add_text(
            f"Evidencias: {references or 'sin referencias registradas.'}"
        )

    if not draft.claims:
        add_text(
            "No se han registrado afirmaciones "
            "con referencias individuales."
        )

    # Construimos el PDF en memoria. El exportador será responsable
    # de validar la aprobación y publicar después el archivo.
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=draft.title,
        author="FitFamily",
    )
    document.build(
        story,
        onFirstPage=_draw_page_number,
        onLaterPages=_draw_page_number,
        canvasmaker=_deterministic_canvas,
    )

    return buffer.getvalue()