"""Pruebas locales sin LLM; compatibles con unittest y pytest."""
import unittest
from decimal import Decimal
from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.analysis.calculation_adapter import metric_from_scenario_calculation
from src.review.calculation_validation import validate_calculation_contexts
from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.schemas import ResearchBrief, ResearchResult


def metrics(clients=100):
    scenario = create_economic_scenario('intermediate', clients, 50, 1000, 10,
                                       assumptions=['Datos ficticios.'])
    return [metric_from_scenario_calculation(scenario, c)
            for c in evaluate_economic_scenario(scenario, limitations=['Sin impuestos.'])]


class EconomicReviewTests(unittest.TestCase):
    def test_four_metrics_and_report(self):
        ms = metrics()
        originals = [m.model_dump(mode='json') for m in ms]
        research = ResearchResult()
        draft = build_report(ResearchBrief(business_type='gimnasio', location='Madrid',
                             study_area='Zona ficticia'), research, calculated_metrics=ms)
        review = run_basic_review(draft, research, calculated_metrics=ms)
        self.assertEqual(review.issues, ())
        self.assertEqual(len([c for c in draft.claims if c.metric_id]), 4)
        self.assertEqual(choose_review_route_for_context(review, draft, research, 0,
                         calculated_metrics=ms), 'pending_review')
        self.assertEqual(originals, [m.model_dump(mode='json') for m in ms])

    def test_tampering_each_indicator(self):
        for index in range(4):
            for field in ('value', 'unit', 'id', 'reference', 'operation', 'input', 'result', 'input_unit'):
                with self.subTest(index=index, field=field):
                    m = metrics()[index]
                    c = m.context.calculation_result
                    if field == 'value': m.value += Decimal('1')
                    elif field == 'unit': m.unit = 'EUR'
                    elif field == 'id': m.metric_id = 'wrong'
                    elif field == 'reference': m.calculation = 'wrong'
                    elif field == 'operation': c.operation = 'wrong'
                    elif field == 'input': c.inputs[0].value += 1
                    elif field == 'input_unit': c.inputs[0].unit = 'wrong'
                    else: c.result.value += 1
                    issues = validate_calculation_contexts([m], ResearchResult())
                    self.assertEqual(issues[0].code, 'invalid_calculation_context')
                    self.assertEqual(issues[0].correction_stage, 'analysis')

    def test_missing_context(self):
        for m in metrics():
            m.context = None
            self.assertTrue(validate_calculation_contexts([m], ResearchResult()))

    def test_missing_result_is_not_zero(self):
        for m in metrics():
            m.context.calculation_result.result = None
            m.value = None
            self.assertEqual(validate_calculation_contexts([m], ResearchResult()), [])
            m.value = Decimal('0')
            self.assertTrue(validate_calculation_contexts([m], ResearchResult()))

    def test_negative_monthly_result_and_zero_clients(self):
        ms = metrics(0)
        self.assertEqual(ms[2].value, Decimal('-1000'))
        self.assertEqual(validate_calculation_contexts(ms, ResearchResult()), [])

    def test_intermediate_revenue_cannot_be_changed_with_total(self):
        m = metrics()[2]

        m.context.calculation_result.inputs[0].value += 100
        m.context.calculation_result.result.value += 100
        m.value += Decimal("100")

        issues = validate_calculation_contexts(
            [m],
            ResearchResult(),
        )

        self.assertTrue(issues)
        self.assertEqual(
            issues[0].code,
            "invalid_calculation_context",
        )

    def test_observed_inputs_need_evidence(self):
        for m in metrics():
            m.context.calculation_result.inputs[0].input_type = 'evidence'
            self.assertTrue(validate_calculation_contexts([m], ResearchResult()))

    def test_context_change_requires_new_review(self):
        ms = metrics()
        research = ResearchResult()
        draft = build_report(ResearchBrief(business_type='gimnasio', location='Madrid',
                             study_area='Zona ficticia'), research, calculated_metrics=ms)
        review = run_basic_review(draft, research, calculated_metrics=ms)
        ms[0].context.scenario.assumptions.append('Cambio posterior')
        with self.assertRaisesRegex(ValueError, 'análisis cambió'):
            choose_review_route_for_context(review, draft, research, 0, calculated_metrics=ms)

if __name__ == '__main__':
    unittest.main()
