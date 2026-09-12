import unittest
from unittest.mock import patch
from pathlib import Path

from test_validation import request, plan, task
from approval import decide_proposal, proposal_fingerprint
from models import HumanDecision, PlanStatus


class ApprovalTests(unittest.TestCase):
    def proposal(self):
        return plan(plan_status=PlanStatus.REQUIRES_HUMAN_REVIEW)

    def test_each_decision(self):
        for decision, status in [(HumanDecision.APPROVED, PlanStatus.APPROVED),
                                 (HumanDecision.REJECTED, PlanStatus.REJECTED),
                                 (HumanDecision.REVISION_REQUESTED, PlanStatus.REVISION_REQUESTED)]:
            p = self.proposal()
            updated, record = decide_proposal(request(), p, decision, proposal_fingerprint(request(), p), 'Review notes')
            self.assertEqual(updated.plan_status, status)
            self.assertEqual(record.decision, decision)
            self.assertIsNotNone(record.decided_at.tzinfo)
            self.assertEqual(p.plan_status, PlanStatus.REQUIRES_HUMAN_REVIEW)
            with self.assertRaises(ValueError):
                decide_proposal(request(), updated, decision, proposal_fingerprint(request(), updated), 'Notes')

    def test_invalid_approval_and_stale_proposals(self):
        p = self.proposal()
        bad = p.model_copy(update={'tasks': [task(assigned_resources=['Invented'])]})
        with self.assertRaises(ValueError):
            decide_proposal(request(), bad, HumanDecision.APPROVED, proposal_fingerprint(request(), bad))
        for changed_request, changed_plan in [(request(), p.model_copy(update={'summary': 'Changed'})),
                                               (request().model_copy(update={'objective': 'Changed'}), p)]:
            with self.assertRaises(ValueError):
                decide_proposal(changed_request, changed_plan, HumanDecision.APPROVED, proposal_fingerprint(request(), p))

    def test_revision_notes_required_and_pending_rejected(self):
        p = self.proposal()
        for decision in [HumanDecision.REVISION_REQUESTED, HumanDecision.PENDING]:
            with self.assertRaises(ValueError):
                decide_proposal(request(), p, decision, proposal_fingerprint(request(), p))

    def test_app_approval_and_new_generation_clear_decision(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        def generate(mission_request, hf_token):
            return plan(mission_id=mission_request.mission_id,
                        tasks=[task(assigned_resources=mission_request.available_resources, human_approval_required=True)],
                        covered_constraints=mission_request.constraints, approval_gates=mission_request.approval_rules)
        with patch('planner.generate_structured_plan', side_effect=generate):
            app.button[0].click().run()
            approve = next(b for b in app.button if b.label == 'Approve advisory plan')
            self.assertTrue(approve.disabled)
            app.checkbox[0].check().run()
            next(b for b in app.button if b.label == 'Approve advisory plan').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['mission_plan'].plan_status, PlanStatus.APPROVED)
            self.assertEqual(app.session_state['review_decision'].decision, HumanDecision.APPROVED)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertNotIn('review_decision', app.session_state)
            self.assertEqual(app.session_state['mission_plan'].plan_status, PlanStatus.AWAITING_HUMAN_APPROVAL)

    def test_app_invalid_reject_and_revision(self):
        from streamlit.testing.v1 import AppTest
        for label, status in [('Reject proposal', PlanStatus.REJECTED), ('Request revision', PlanStatus.REVISION_REQUESTED)]:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
            with patch('planner.generate_structured_plan', return_value=plan()) as generate:
                app.button[0].click().run()
                self.assertTrue(next(b for b in app.button if b.label == 'Approve advisory plan').disabled)
                app.text_area(key='review_notes').set_value('Correct resources').run()
                next(b for b in app.button if b.label == label).click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['mission_plan'].plan_status, status)
                self.assertEqual(generate.call_count, 3)
