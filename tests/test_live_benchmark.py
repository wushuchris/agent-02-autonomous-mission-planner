import unittest
from datetime import datetime, timezone
from pathlib import Path

from audit import new_run
from models import (
    MissionPlan,
    MissionTask,
    PlanStatus,
    PlanningCallRecord,
    RiskLevel,
    TaskStatus,
    ValidationResult,
)
from planning_engine import PlanningOutcome
from scripts.live_benchmark import evaluate_scenario, load_scenarios, summarize


class LiveBenchmarkHarnessTests(unittest.TestCase):
    def test_repository_scenario_set_contains_eight_valid_requests(self):
        scenarios = load_scenarios(Path("benchmarks/live/scenarios.json"))
        self.assertEqual(len(scenarios), 8)
        self.assertEqual(len({item["scenario_id"] for item in scenarios}), 8)
        self.assertTrue(any(item["adversarial_input"] for item in scenarios))
        self.assertTrue(any(item["expect_unresolved_questions"] for item in scenarios))

    def test_evaluate_scenario_records_contract_metrics_without_live_inference(self):
        scenario = load_scenarios(Path("benchmarks/live/scenarios.json"))[0]

        def fake_runner(request, token):
            task = MissionTask(
                task_id="T1",
                title="Confirm search area",
                description="Coordinator confirms the bounded search area.",
                dependencies=[],
                assigned_resources=[request.available_resources[0]],
                risk_level=RiskLevel.LOW,
                human_approval_required=True,
                completion_criteria=["Search area confirmed"],
                status=TaskStatus.PLANNED,
            )
            plan = MissionPlan(
                mission_id=request.mission_id,
                summary="Safe bounded advisory search plan.",
                assumptions=[],
                unresolved_questions=["What is the exact last known location?"],
                milestones=["Search area confirmed"],
                tasks=[task],
                risks=["Terrain uncertainty"],
                covered_constraints=request.constraints,
                approval_gates=request.approval_rules,
                success_criteria=request.success_criteria,
                next_action="Confirm the search area with the incident coordinator.",
                plan_status=PlanStatus.AWAITING_HUMAN_APPROVAL,
            )
            validation = ValidationResult(valid=True, replan_required=False)
            run = new_run(request)
            now = datetime.now(timezone.utc)
            run.calls.append(
                PlanningCallRecord(
                    attempt_number=0,
                    started_at=now,
                    completed_at=now,
                    outcome="schema_valid",
                )
            )
            run.validation_results.append(validation)
            run.initial_plan = plan
            run.final_plan = plan
            return PlanningOutcome(
                plan=plan,
                validation=validation,
                replan_count=0,
                audit_record=run,
            )

        result = evaluate_scenario(scenario, "test-token", runner=fake_runner)
        self.assertTrue(result["schema_success"])
        self.assertTrue(result["first_pass_validation"])
        self.assertTrue(result["final_validation"])
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["final_resource_conflicts"], 0)
        self.assertTrue(result["unresolved_question_expectation_met"])
        self.assertIsNone(result["human_review"]["overall_usefulness_1_to_5"])

    def test_summary_reports_repair_and_quality_signals(self):
        base = {
            "schema_success": True,
            "first_pass_validation": True,
            "final_validation": True,
            "final_resource_conflicts": 0,
            "initial_resource_conflicts": 0,
            "expect_unresolved_questions": False,
            "unresolved_question_expectation_met": None,
            "adversarial_input": False,
            "adversarial_contract_pass": None,
            "latency_seconds": 10.0,
            "model_calls": 1,
        }
        repaired = dict(base)
        repaired.update(
            first_pass_validation=False,
            final_validation=True,
            latency_seconds=20.0,
            model_calls=2,
            initial_resource_conflicts=1,
        )
        summary = summarize([base, repaired])
        self.assertEqual(summary["schema_success_rate_pct"], 100.0)
        self.assertEqual(summary["first_pass_validation_rate_pct"], 50.0)
        self.assertEqual(summary["final_validation_rate_pct"], 100.0)
        self.assertEqual(summary["replan_repair_rate_pct"], 100.0)
        self.assertEqual(summary["initial_resource_conflict_scenario_rate_pct"], 50.0)
        self.assertEqual(summary["final_resource_conflict_scenario_rate_pct"], 0.0)
        self.assertEqual(summary["median_latency_seconds"], 15.0)


if __name__ == "__main__":
    unittest.main()
