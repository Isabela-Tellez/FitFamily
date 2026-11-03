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
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from src.reporting.calculated_claims import ECONOMIC_TRACE_HEADERS, economic_trace_row, format_scenario_note
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
        fontSize=36,
        leading=43,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="ReportHeading",
        fontName="FitFamily-Bold",
        textColor=colors.HexColor("#102C3A"),
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

    styles.add(ParagraphStyle(
        name="ScenarioHeading", parent=styles["ReportHeading"],
        fontSize=16, leading=21, textColor=colors.HexColor("#006D66"),
    ))
    styles.add(ParagraphStyle(
        name="MetricHeading", parent=styles["ReportHeading"],
        fontSize=11, leading=14, spaceBefore=6, spaceAfter=3,
    ))

    styles.add(ParagraphStyle(
        name="CoverLabel", parent=styles["ReportHeading"],
        fontSize=10, leading=14, textColor=colors.HexColor("#85DAC7"),
    ))

    for name, parent in (("LossLabel", "ReportBody"), ("LossAmount", "ScenarioHeading")):
        styles.add(ParagraphStyle(
            name=name, parent=styles[parent], textColor=colors.HexColor("#A12626"),
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
    cover_rows = [
        [Paragraph("FITFAMILY · ESTUDIO DE MERCADO", styles["CoverLabel"])],
        [Spacer(1, 28)],
        [Paragraph(_paragraph_text(draft.title), styles["ReportTitle"])],

    ]
    if draft.study_area and draft.study_area.casefold() not in draft.title.casefold():
        cover_rows.append([
            Paragraph(_paragraph_text(draft.study_area), styles["CoverLabel"])
        ])
    cover_rows.append([Spacer(1, 28)])
    cover = LongTable(cover_rows, colWidths=[465])
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#102C3A")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 22),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.extend([cover, Spacer(1, 18)])

    add_text(f"Identificador del borrador: {draft.draft_id}")
    add_text(f"Versión: {draft.version}")

    status = (
        "aprobado para exportación."
        if approved
        else "borrador pendiente de revisión y aprobación."
    )
    add_text(f"Estado: {status}")
    story.append(Spacer(1, 0.3 * cm))

    executive_summary = next(
        (section for section in draft.sections
         if section.strip().partition("\n")[0] == "Resumen ejecutivo"),
        None,
    )
    if executive_summary:
        _, _, summary_body = executive_summary.strip().partition("\n")
        add_text("Resumen ejecutivo", "ScenarioHeading")
        for paragraph in summary_body.split("\n\n"):
            if paragraph.strip():
                add_text(paragraph.strip())

    # Seguimos el formato actual de ReportDraft:
    # la primera línea de cada sección contiene su título.
    for section in draft.sections:
        clean_section = section.strip()
        if not clean_section:
            continue

        heading, _, body = clean_section.partition("\n")
        if section == executive_summary:
            continue
        if heading == "Escenarios económicos":
            story.append(PageBreak())
            add_text(heading, "ScenarioHeading")
        else:
            add_text(heading, "ReportHeading")

        if heading == "Escenarios económicos":
            result_rows = []
            for claim in draft.claims:
                if not (claim.metric_id or "").endswith(".monthly_result"):
                    continue
                row = economic_trace_row(claim)
                if row is None:
                    continue
                scenario, _, value, _ = row
                result = claim.reported_value
                label = "Resultado estimado"
                if result < 0:
                    label = "Pérdida estimada"
                elif result > 0:
                    label = "Beneficio estimado"
                result_rows.append([
                    Paragraph(_paragraph_text(f"Escenario {scenario.lower()}"), styles["ScenarioHeading"]),
                    Paragraph(_paragraph_text(label), styles["LossLabel" if result < 0 else "ReportBody"]),
                    Paragraph(_paragraph_text(value.lstrip("-")), styles["LossAmount" if result < 0 else "ScenarioHeading"]),
                ])
            if result_rows:
                assumption_rows = []
                for block in body.split("\n\n### "):
                    if not block.startswith("Escenario "):
                        continue
                    title, _, assumptions = block.split("\n\n#### ", 1)[0].strip().partition("\n")
                    assumption_rows.append([
                        [
                            Paragraph(_paragraph_text(title), styles["ScenarioHeading"]),
                            Paragraph(_paragraph_text(assumptions.strip()), styles["ReportBody"]),
                        ]
                    ])
                if assumption_rows:
                    add_text("Supuestos de los escenarios", "ReportHeading")
                    assumptions_table = LongTable(assumption_rows, colWidths=[465])
                    assumptions_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF5F2")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ]))
                    story.extend([assumptions_table, Spacer(1, 12)])
                for start in range(0, len(result_rows), 2):
                    cards = result_rows[start:start + 2]
                    summary = LongTable([cards], colWidths=[465 / len(cards)] * len(cards))
                    summary.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF5F2")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 14),
                        ("LINEAFTER", (0, 0), (0, 0), 6, colors.white),
                    ]))
                    story.extend([summary, Spacer(1, 10)])

                comparison = {}
                for claim in draft.claims:
                    row = economic_trace_row(claim)
                    if row is not None:
                        scenario, metric, value, _ = row
                        comparison.setdefault(scenario, {})[metric] = value
                metrics = dict.fromkeys(
                    metric for values in comparison.values() for metric in values
                )
                cells = [["Indicador", *comparison]]
                cells.extend(
                    [metric, *(values.get(metric, "No disponible") for values in comparison.values())]
                    for metric in metrics
                )
                table = LongTable(
                    [[Paragraph(_paragraph_text(value), styles["ReportBody"]) for value in row]
                     for row in cells],
                    colWidths=[165, *([300 / len(comparison)] * len(comparison))],
                    repeatRows=1,
                )
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D4E7EA")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F7")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.extend([table, Spacer(1, 10)])
                add_text("Cómo leer la comparación", "ReportHeading")
                add_text(
                    "Los resultados estimados dependen de la clientela, la cuota "
                    "y los costes de cada escenario. El punto de equilibrio indica "
                    "cuántos clientes hacen falta para cubrir los costes incluidos."
                )

        # Los párrafos separados permiten repartir el contenido
        # entre páginas sin tratar toda la sección como un bloque.
        for paragraph in body.split("\n\n"):
            if paragraph.strip():
                content = paragraph.strip()
                title, _, details = content.partition("\n")
                if heading == "Escenarios económicos" and title.startswith("### "):
                    add_text(title[4:], "ScenarioHeading")
                elif heading == "Escenarios económicos" and title.startswith("#### "):
                    add_text(title[5:], "MetricHeading")
                    if details:
                        add_text(details)
                else:
                    add_text(content)

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
    limitations = [
        visible
        for note in dict.fromkeys(draft.limitations)
        if (visible := format_scenario_note(note)) is not None
    ]
    for limitation in limitations:
        add_text(limitation)
    if not limitations:
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

    economic_rows = []
    for claim in draft.claims:
        row = economic_trace_row(claim)
        if row is not None:
            economic_rows.append(row)
            continue
        add_text(claim.claim_id, "ReportHeading")
        add_text(f"Tipo: {kind_labels.get(claim.kind, claim.kind)}")
        add_text(claim.text)
        references = ", ".join(dict.fromkeys(claim.evidence_ids))
        add_text(
            f"Evidencias: {references or 'sin referencias registradas.'}"
        )

        # Mostramos la referencia numérica sin recalcularla.
        if claim.metric_id is not None:
            add_text(f"Métrica: {claim.metric_id}")
            add_text(f"Valor declarado: {claim.reported_value}")
            add_text(f"Unidad: {claim.reported_unit}")

    if economic_rows:
        rows = [
            [Paragraph(_paragraph_text(cell), styles["ReportBody"]) for cell in row]
            for row in [ECONOMIC_TRACE_HEADERS, *economic_rows]
        ]
        table = LongTable(rows, colWidths=[85, 99, 66, 215], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#E9EFF5"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, "#667788"),
        ]))
        story.append(table)

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
