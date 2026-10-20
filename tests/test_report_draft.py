"""
Pruebas unitarias del modelo ReportDraft.

Comprobamos que los borradores de informes
almacenan correctamente la información.
"""

import unittest

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
# Permite ejecutar las pruebas directamente con Python.
if __name__ == "__main__":
    unittest.main()

      