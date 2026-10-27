"""
Pruebas unitarias del modelo ReportDraft.

Comprobamos que los borradores de informes
almacenan correctamente la información.
"""

import unittest
import pytest

from src.reporting.models import ReportDraft


class TestReportDraft(unittest.TestCase):
    """Pruebas para comprobar el funcionamiento de ReportDraft."""

    def test_guardar_datos(self):
        """Comprueba que el borrador conserva los datos recibidos."""

        # 1. Creamos un borrador con información ficticia.
        borrador = ReportDraft(
            title="Informe FitFamily",
            study_area="Madrid",
            sections=["Introducción", "Resultados"],
            sources=["Fuente de prueba"],
            limitations=["Datos ficticios"],
        )

        # 2. Comprobamos que los datos se han guardado correctamente.
        # assertEqual compara el valor esperado con el valor real.
        # Si son diferentes, la prueba falla.

        self.assertEqual(borrador.title, "Informe FitFamily")
        self.assertEqual(borrador.study_area, "Madrid")
        self.assertEqual(borrador.sections, ["Introducción", "Resultados"])
        self.assertEqual(borrador.sources, ["Fuente de prueba"])
        self.assertEqual(borrador.limitations, ["Datos ficticios"])

    def test_listas_independientes(self):
        """
        Comprueba que dos borradores no comparten sus listas.

        Cada instancia debe tener sus propias secciones,
        fuentes y limitaciones.
        """

        # 1. Creamos dos borradores diferentes.
        # No proporcionamos listas, así que Python
        # debe crear listas vacías para cada uno.

        borrador_a = ReportDraft(
            title="Informe Madrid",
            study_area="Madrid"
        )

        borrador_b = ReportDraft(
            title="Informe Barcelona",
            study_area="Barcelona"
        )

        # 2. Añadimos información únicamente al borrador A.

        borrador_a.sections.append("Introducción")
        borrador_a.sources.append("Fuente Madrid")
        borrador_a.limitations.append("Datos incompletos")

        # 3. Comprobamos que el borrador B sigue
        # teniendo sus tres listas vacías.

        self.assertEqual(borrador_b.sections, [])
        self.assertEqual(borrador_b.sources, [])
        self.assertEqual(borrador_b.limitations, [])   


def test_drafts_have_different_identifiers():
    """Cada borrador nuevo tiene un identificador independiente."""
    from src.reporting.models import ReportDraft

    first = ReportDraft(title="Informe A", study_area="El Cañaveral")
    second = ReportDraft(title="Informe B", study_area="El Cañaveral")

    assert first.draft_id
    assert second.draft_id
    assert first.draft_id != second.draft_id
    assert first.version == 1
    assert second.version == 1


def test_draft_keeps_claim_and_evidence_reference():
    """La afirmación conserva la referencia a su evidencia."""
    from src.reporting.models import ReportClaim, ReportDraft

    claim = ReportClaim(
        claim_id="precio_gym_1",
        text="El gimnasio publica una cuota mensual de 45 euros.",
        kind="fact",
        evidence_ids=["test_price_1"],
    )

    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[claim],
    )

    assert draft.claims[0].text == claim.text
    assert draft.claims[0].kind == "fact"
    assert draft.claims[0].evidence_ids == ["test_price_1"]



# Permite ejecutar las pruebas directamente con Python.
if __name__ == "__main__":
    unittest.main()

def test_claim_can_reference_an_analysis_metric():
    """Conserva la métrica y el valor utilizado en el informe."""
    from src.reporting.models import ReportClaim

    claim = ReportClaim(
        claim_id="claim_average_price",
        text="La cuota mensual media es de 45 EUR.",
        kind="fact",
        evidence_ids=["price_a", "price_b"],
        metric_id="scenario_base.average_monthly_price_eur",
        reported_value=45.0,
        reported_unit="EUR/month",
    )

    assert claim.metric_id == "scenario_base.average_monthly_price_eur"
    assert claim.reported_value == 45.0
    assert claim.reported_unit == "EUR/month"
    assert claim.evidence_ids == ["price_a", "price_b"]


def test_claim_without_metric_keeps_optional_fields_empty():
    """Las afirmaciones existentes no necesitan una métrica."""
    from src.reporting.models import ReportClaim

    claim = ReportClaim(
        claim_id="claim_assumption",
        text="Se plantea ofrecer una ludoteca.",
        kind="assumption",
    )

    assert claim.metric_id is None
    assert claim.reported_value is None
    assert claim.reported_unit is None

@pytest.mark.parametrize(
    "metric_fields",
    [
        # Falta el valor y la unidad.
        {"metric_id": "average_price"},
        # Falta el identificador.
        {"reported_value": 45.0, "reported_unit": "EUR/month"},
        # Identificador vacío.
        {
            "metric_id": " ",
            "reported_value": 45.0,
            "reported_unit": "EUR/month",
        },
        # Unidad vacía.
        {
            "metric_id": "average_price",
            "reported_value": 45.0,
            "reported_unit": " ",
        },
        # Un booleano no debe aceptarse como cifra.
        {
            "metric_id": "average_price",
            "reported_value": True,
            "reported_unit": "EUR/month",
        },
        # El valor debe ser numérico, no texto.
        {
            "metric_id": "average_price",
            "reported_value": "45",
            "reported_unit": "EUR/month",
        },
        # No admitimos valores infinitos ni indefinidos.
        {
            "metric_id": "average_price",
            "reported_value": float("inf"),
            "reported_unit": "EUR/month",
        },
        {
            "metric_id": "average_price",
            "reported_value": float("nan"),
            "reported_unit": "EUR/month",
        },
    ],
)
def test_claim_rejects_invalid_metric_reference(metric_fields):
    """Una referencia numérica debe estar completa y ser válida."""
    from src.reporting.models import ReportClaim

    with pytest.raises(ValueError):
        ReportClaim(
            claim_id="claim_invalid_metric",
            text="Afirmación ficticia para comprobar la validación.",
            kind="inference",
            **metric_fields,
        )