import unittest
from unittest.mock import patch
from pathlib import Path

from test_validation import request, plan, task
from audit import new_run, record_decision, export_run
from approval import decide_proposal, proposal_fingerprint
from models import HumanDecision, PlanningRunRecord, PlanStatus
from planner import PlannerOutputError
from planning_engine import run_planning


class AuditTests(unittest.TestCase):
    def test_full_history_and_roundtrip(self):
        bad = plan(tasks=[task(assigned_resources=['Invented'])])
        with patch('planner.generate_structured_plan', side_effect=[bad, bad, plan()]):
            outcome = run_planning(request(), 'credential-123')
        run = outcome.audit_record
        self.assertEqual(run.initial_plan, bad)
        self.assertEqual([r.valid for r in run.validation_results], [False, False, True])
        self.assertEqual([c.attempt_number for c in run.calls], [0, 1, 2])
        self.assertEqual(len(run.replan_attempts), 2)
        self.assertTrue(all(c.started_at <= c.completed_at for c in run.calls))
        self.assertEqual(PlanningRunRecord.model_validate_json(export_run(run)), run)
        self.assertNotIn('credential-123', export_run(run))
        outcome.plan.summary = 'Changed later'
        self.assertNotEqual(run.final_plan.summary, outcome.plan.summary)

    def test_initial_and_revision_failures_recorded_without_raw_errors(self):
        for error in [PlannerOutputError('secret-content'), RuntimeError('secret-content')]:
            run = new_run(request())
            with patch('planner.generate_structured_plan', side_effect=error):
                with self.assertRaises(type(error)):
                    run_planning(request(), 'credential-123', audit_record=run)
            self.assertEqual(len(run.calls), 1)
            self.assertIsNone(run.final_plan)
            self.assertEqual(run.final_status, PlanStatus.REQUIRES_HUMAN_REVIEW)
            self.assertNotIn('secret-content', export_run(run))
            bad = plan(tasks=[task(assigned_resources=['Invented'])])
            with patch('planner.generate_structured_plan', side_effect=[bad, error]):
                result = run_planning(request(), 'credential-123')
            self.assertEqual(len(result.audit_record.calls), 2)
            self.assertEqual(result.audit_record.calls[-1].outcome, 'failed')
            self.assertEqual(result.audit_record.replan_attempts, [])
            self.assertEqual(result.audit_record.final_plan, result.plan)

    def test_human_decision_preserves_reviewed_snapshot(self):
        with patch('planner.generate_structured_plan', return_value=plan()):
            run = run_planning(request(), 'token').audit_record
        for decision in [HumanDecision.APPROVED, HumanDecision.REJECTED, HumanDecision.REVISION_REQUESTED]:
            final, review = decide_proposal(request(), run.final_plan, decision,
                proposal_fingerprint(request(), run.final_plan), 'Change search area')
            updated = record_decision(run, final, review)
            self.assertEqual(updated.human_decision, decision)
            self.assertEqual(updated.final_status, final.plan_status)
            self.assertEqual(updated.reviewable_plan, run.final_plan)
            self.assertEqual(updated.reviewed_at, review.decided_at)
            self.assertEqual(run.human_decision, HumanDecision.PENDING)
            with self.assertRaises(ValueError):
                record_decision(updated, final, review)
            with self.assertRaises(ValueError):
                record_decision(run, final.model_copy(update={'summary': 'Changed'}), review)

    def test_fresh_run_required(self):
        run = new_run(request())
        with patch('planner.generate_structured_plan', return_value=plan()):
            run_planning(request(), 'token', audit_record=run)
            with self.assertRaises(ValueError):
                run_planning(request(), 'token', audit_record=run)
        self.assertNotEqual(new_run(request()).run_id, run.run_id)

    def test_app_exports_failed_run_and_resets_id(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        with patch('planner.generate_structured_plan', side_effect=PlannerOutputError('Malformed output')):
            app.button[0].click().run()
            self.assertFalse(app.exception)
            first = app.session_state['audit_record'].run_id
            self.assertEqual(len(app.session_state['audit_record'].calls), 1)
            app.button[0].click().run()
            self.assertNotEqual(app.session_state['audit_record'].run_id, first)
            self.assertEqual(len(app.session_state['audit_record'].calls), 1)
