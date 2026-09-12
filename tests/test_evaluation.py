import unittest
from unittest.mock import patch

from evaluation.run import evaluate


class EvaluationTests(unittest.TestCase):
    def test_all_expected_outcomes(self):
        report = evaluate()
        self.assertEqual(report['passed'], report['total'], report)
        for group, minimum in [('success', 10), ('edge', 5), ('failure', 5), ('adversarial', 1)]:
            self.assertGreaterEqual(report['groups'][group]['total'], minimum)

    def test_scorecard_detects_regression(self):
        from models import ValidationResult
        with patch('evaluation.run.validate_plan', return_value=ValidationResult(valid=True)):
            report = evaluate()
        self.assertLess(report['passed'], report['total'])
