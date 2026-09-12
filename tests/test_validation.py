import unittest
from unittest.mock import patch
from pathlib import Path

from models import MissionPlan, MissionRequest, MissionTask, PlanStatus, RiskLevel, TaskStatus
from plan_graph import build_plan_graph
from validator import validate_plan, apply_validation_status


def request():
    return MissionRequest(mission_id="demo", objective="Locate hiker", environment="Trail",
                          search_area="Trailhead", available_resources=["Ground team"],
                          success_criteria=["Report findings"])


def task(task_id="survey", **changes):
    values = dict(task_id=task_id, title="Survey", description="Review search area",
                  assigned_resources=["Ground team"], completion_criteria=["Report reviewed"])
    values.update(changes)
    return MissionTask(**values)


def plan(**changes):
    values = dict(mission_id="demo", summary="Search proposal", tasks=[task()],
                  success_criteria=["Report findings"], next_action="Ask coordinator to review")
    values.update(changes)
    return MissionPlan(**values)


class ValidatorTests(unittest.TestCase):
    def test_valid_and_pure(self):
        proposal = plan()
        before = proposal.model_dump()
        result = validate_plan(request(), proposal)
        self.assertTrue(result.valid)
        self.assertFalse(result.replan_required)
        self.assertEqual(proposal.model_dump(), before)
        self.assertEqual(apply_validation_status(proposal, result).plan_status, PlanStatus.REQUIRES_HUMAN_REVIEW)

    def test_dependency_order_and_disconnected_node(self):
        graph = build_plan_graph(plan(tasks=[task("report", dependencies=["survey"]), task(), task("brief")]))
        self.assertFalse(graph.errors)
        self.assertLess(graph.topological_order.index("survey"), graph.topological_order.index("report"))
        self.assertIn("brief", graph.topological_order)

    def test_bad_graphs(self):
        for tasks, message in [([task(), task()], "Duplicate"),
                               ([task(dependencies=["absent"])], "nonexistent"),
                               ([task(dependencies=["survey"])], "Circular"),
                               ([task(dependencies=["b"]), task("b", dependencies=["survey"])], "Circular")]:
            with self.subTest(message=message, tasks=tasks):
                result = validate_plan(request(), plan(tasks=tasks))
                self.assertFalse(result.valid)
                self.assertIn(message, " ".join(result.dependency_issues))
                self.assertEqual(build_plan_graph(plan(tasks=tasks)).topological_order, [])

    def test_resources_exact_labels_only(self):
        self.assertTrue(validate_plan(request(), plan(tasks=[task(assigned_resources=[" GROUND  team "])])).valid)
        for name in ["Helicopter", "Ground", ""]:
            self.assertTrue(validate_plan(request(), plan(tasks=[task(assigned_resources=[name])])).resource_conflicts)

    def test_blank_completion_criteria(self):
        for criteria in [[" "], ["Report", ""]]:
            self.assertFalse(validate_plan(request(), plan(tasks=[task(completion_criteria=criteria)])).valid)
        # Defensive checks also cover trusted callers bypassing Pydantic validation.
        bad = task().model_copy(update={"completion_criteria": []})
        self.assertFalse(validate_plan(request(), plan(tasks=[bad])).valid)

    def test_next_action_and_identity(self):
        self.assertFalse(validate_plan(request(), plan().model_copy(update={"next_action": " "})).valid)
        self.assertFalse(validate_plan(request(), plan(mission_id="other")).valid)

    def test_constraint_representation_not_semantics(self):
        req = request().model_copy(update={"constraints": ["Maintain radio contact"]})
        self.assertTrue(validate_plan(req, plan()).constraint_violations)
        result = validate_plan(req, plan(covered_constraints=["maintain  RADIO contact"]))
        self.assertTrue(result.valid)
        self.assertIn("compliance", " ".join(result.warnings))
        self.assertFalse(validate_plan(req, plan(covered_constraints=["No radio contact"])).valid)
        self.assertFalse(validate_plan(request(), plan(covered_constraints=["Invented constraint"])).valid)

    def test_approval_rule_and_flag(self):
        req = request().model_copy(update={"approval_rules": ["Coordinator review"]})
        self.assertFalse(validate_plan(req, plan()).valid)
        self.assertFalse(validate_plan(req, plan(approval_gates=["Coordinator review"])).valid)
        proposal = plan(tasks=[task(human_approval_required=True)], approval_gates=["Coordinator review"])
        result = validate_plan(req, proposal)
        self.assertTrue(result.valid)
        self.assertEqual(apply_validation_status(proposal, result).plan_status, PlanStatus.AWAITING_HUMAN_APPROVAL)
        self.assertFalse(validate_plan(req, proposal.model_copy(update={"approval_gates": ["Other gate"]})).valid)

    def test_sensitive_tasks_cannot_proceed(self):
        for status in [TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETE]:
            self.assertFalse(validate_plan(request(), plan(tasks=[task(human_approval_required=True, status=status)],
                                                          approval_gates=["Review"])).valid)
        self.assertFalse(validate_plan(request(), plan(tasks=[task(human_approval_required=True)], approval_gates=[" "])).valid)
        for risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self.assertFalse(validate_plan(request(), plan(tasks=[task(risk_level=risk)])).valid)
        self.assertFalse(validate_plan(request(), plan(plan_status=PlanStatus.APPROVED)).valid)

    def test_failure_status_and_feedback(self):
        proposal = plan(tasks=[task(assigned_resources=["Invented"])])
        result = validate_plan(request(), proposal)
        self.assertTrue(result.replan_required)
        self.assertEqual(apply_validation_status(proposal, result).plan_status, PlanStatus.VALIDATION_FAILED)

    def test_unresolved_information_warning(self):
        result = validate_plan(request(), plan(unresolved_questions=["Weather unknown"]))
        self.assertTrue(result.valid)
        self.assertIn("criticality", " ".join(result.warnings))


class AppTests(unittest.TestCase):
    def test_pass_fail_and_stale_result_clearing(self):
        from streamlit.testing.v1 import AppTest
        from planner import PlannerOutputError
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run()
        def proposal(mission_request, hf_token):
            return plan(mission_id=mission_request.mission_id,
                        tasks=[task(assigned_resources=mission_request.available_resources,
                                    human_approval_required=True)],
                        approval_gates=mission_request.approval_rules,
                        covered_constraints=mission_request.constraints)
        with patch("planner.generate_structured_plan", side_effect=proposal):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual([metric.value for metric in app.metric][:2], ["VALID", "PASS"])
        with patch("planner.generate_structured_plan", return_value=plan()):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual([metric.value for metric in app.metric][:2], ["VALID", "FAIL"])
        self.assertEqual(app.session_state["mission_plan"].plan_status, PlanStatus.VALIDATION_FAILED)
        with patch("planner.generate_structured_plan", side_effect=PlannerOutputError("Malformed output")):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)
        self.assertNotIn("mission_plan", app.session_state)


if __name__ == "__main__":
    unittest.main()
