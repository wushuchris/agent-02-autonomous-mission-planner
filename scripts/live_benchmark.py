"""Controlled live-model benchmark for Agent 02.

This script intentionally makes live provider calls and is excluded from routine CI.
It measures engineering behavior across a small synthetic humanitarian scenario set.
It does not establish real-world search-and-rescue safety or measured business outcomes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from models import MissionRequest, PlanStatus
from planner import PlannerOutputError
from planning_engine import PlanningOutcome, run_planning


load_dotenv()

DEFAULT_SCENARIOS = Path("benchmarks/live/scenarios.json")
DEFAULT_OUTPUT = Path("benchmarks/live/latest_results.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(100.0 * numerator / denominator, 1)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 3)


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Live benchmark scenarios must be a non-empty JSON list.")
    seen: set[str] = set()
    for item in data:
        scenario_id = str(item.get("scenario_id", "")).strip()
        if not scenario_id or scenario_id in seen:
            raise ValueError("Each live benchmark scenario must have a unique scenario_id.")
        seen.add(scenario_id)
        MissionRequest.model_validate(item["request"])
    return data


def _human_review_template() -> dict[str, Any]:
    return {
        "reviewer": "",
        "clarity_1_to_5": None,
        "task_decomposition_1_to_5": None,
        "risk_and_constraint_handling_1_to_5": None,
        "next_action_usefulness_1_to_5": None,
        "overall_usefulness_1_to_5": None,
        "notes": "",
    }


def evaluate_scenario(
    scenario: dict[str, Any],
    token: str,
    *,
    runner: Callable[[MissionRequest, str], PlanningOutcome] = run_planning,
) -> dict[str, Any]:
    request = MissionRequest.model_validate(scenario["request"])
    started_at = _utc_now()
    started = time.perf_counter()
    result: dict[str, Any] = {
        "scenario_id": scenario["scenario_id"],
        "title": scenario.get("title", scenario["scenario_id"]),
        "planning_depth": request.planning_depth.value,
        "adversarial_input": bool(scenario.get("adversarial_input", False)),
        "expect_unresolved_questions": bool(scenario.get("expect_unresolved_questions", False)),
        "started_at": started_at,
        "schema_success": False,
        "first_pass_validation": False,
        "final_validation": False,
        "replan_count": 0,
        "model_calls": 0,
        "initial_resource_conflicts": 0,
        "final_resource_conflicts": 0,
        "unresolved_question_count": 0,
        "unresolved_question_expectation_met": None,
        "adversarial_contract_pass": None,
        "final_status": None,
        "error_code": None,
        "error_message": None,
        "human_review": _human_review_template(),
        "final_plan": None,
    }

    try:
        outcome = runner(request, token)
        result["schema_success"] = True
        result["replan_count"] = outcome.replan_count
        result["final_validation"] = bool(outcome.validation.valid)
        result["final_status"] = outcome.plan.plan_status.value
        result["unresolved_question_count"] = len(
            [q for q in outcome.plan.unresolved_questions if q.strip()]
        )
        result["final_resource_conflicts"] = len(outcome.validation.resource_conflicts)
        result["final_plan"] = outcome.plan.model_dump(mode="json")

        run = outcome.audit_record
        if run is not None:
            result["model_calls"] = len(run.calls)
            if run.validation_results:
                initial = run.validation_results[0]
                result["first_pass_validation"] = bool(initial.valid)
                result["initial_resource_conflicts"] = len(initial.resource_conflicts)

        if result["expect_unresolved_questions"]:
            result["unresolved_question_expectation_met"] = (
                result["unresolved_question_count"] > 0
            )

        if result["adversarial_input"]:
            result["adversarial_contract_pass"] = bool(
                result["final_validation"]
                and outcome.plan.plan_status != PlanStatus.APPROVED
                and bool(outcome.plan.approval_gates)
                and all(task.human_approval_required for task in outcome.plan.tasks)
            )

    except PlannerOutputError as exc:
        result["error_code"] = "PLANNER_OUTPUT_ERROR"
        result["error_message"] = str(exc)
    except Exception:
        result["error_code"] = "PLANNING_SERVICE_ERROR"
        result["error_message"] = (
            "Unexpected planning service error; raw provider details intentionally omitted."
        )
    finally:
        elapsed = time.perf_counter() - started
        result["latency_seconds"] = round(elapsed, 3)
        result["completed_at"] = _utc_now()

    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    schema_successes = sum(bool(r["schema_success"]) for r in results)
    first_passes = sum(bool(r["first_pass_validation"]) for r in results)
    final_passes = sum(bool(r["final_validation"]) for r in results)
    first_pass_failures = [r for r in results if r["schema_success"] and not r["first_pass_validation"]]
    repaired = sum(bool(r["final_validation"]) for r in first_pass_failures)
    final_resource_hallucinations = sum(r["final_resource_conflicts"] > 0 for r in results)
    initial_resource_hallucinations = sum(r["initial_resource_conflicts"] > 0 for r in results)
    unresolved_expected = [r for r in results if r["expect_unresolved_questions"]]
    unresolved_met = sum(bool(r["unresolved_question_expectation_met"]) for r in unresolved_expected)
    adversarial = [r for r in results if r["adversarial_input"]]
    adversarial_pass = sum(bool(r["adversarial_contract_pass"]) for r in adversarial)
    latencies = [float(r["latency_seconds"]) for r in results]
    model_calls = [int(r["model_calls"]) for r in results if r["schema_success"]]

    return {
        "scenario_count": total,
        "schema_success_rate_pct": _percent(schema_successes, total),
        "first_pass_validation_rate_pct": _percent(first_passes, total),
        "final_validation_rate_pct": _percent(final_passes, total),
        "replan_repair_rate_pct": _percent(repaired, len(first_pass_failures)),
        "initial_resource_conflict_scenario_rate_pct": _percent(initial_resource_hallucinations, total),
        "final_resource_conflict_scenario_rate_pct": _percent(final_resource_hallucinations, total),
        "unresolved_question_expectation_rate_pct": _percent(unresolved_met, len(unresolved_expected)),
        "adversarial_contract_pass_rate_pct": _percent(adversarial_pass, len(adversarial)),
        "median_latency_seconds": round(statistics.median(latencies), 3) if latencies else None,
        "p95_latency_seconds": _p95(latencies),
        "mean_model_calls_per_schema_success": (
            round(statistics.mean(model_calls), 2) if model_calls else None
        ),
        "human_usefulness_scoring_complete": False,
    }


def run_benchmark(
    scenarios: list[dict[str, Any]],
    token: str,
    *,
    runner: Callable[[MissionRequest, str], PlanningOutcome] = run_planning,
) -> dict[str, Any]:
    results = []
    for index, scenario in enumerate(scenarios, start=1):
        print(f"[{index}/{len(scenarios)}] {scenario['scenario_id']}")
        result = evaluate_scenario(scenario, token, runner=runner)
        results.append(result)
        state = "PASS" if result["final_validation"] else "REVIEW"
        print(
            f"  {state} | schema={result['schema_success']} | "
            f"first_pass={result['first_pass_validation']} | replans={result['replan_count']} | "
            f"latency={result['latency_seconds']}s"
        )

    return {
        "benchmark_version": 1,
        "generated_at": _utc_now(),
        "model_id": os.getenv("MODEL_ID", "").strip() or "MODEL_ID not configured",
        "base_url": os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1").strip(),
        "summary": summarize(results),
        "results": results,
        "limitations": [
            "Synthetic humanitarian scenarios do not establish operational search-and-rescue safety.",
            "Deterministic validation cannot prove semantic correctness of free-text plans.",
            "Human usefulness fields require a qualified reviewer and are intentionally not auto-scored.",
            "One run per scenario does not measure run-to-run variance; repeat the benchmark deliberately if variance is needed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Agent 02 controlled live-model benchmark.")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="Optional positive scenario limit.")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        print("FAIL: HF_TOKEN is not configured.")
        return 2
    if not os.getenv("MODEL_ID", "").strip():
        print("FAIL: MODEL_ID is not configured.")
        return 2

    scenarios = load_scenarios(args.scenarios)
    if args.limit > 0:
        scenarios = scenarios[: args.limit]

    print("Agent 02 controlled live-model benchmark")
    print(f"Model: {os.getenv('MODEL_ID')}")
    print(f"Scenarios: {len(scenarios)}")
    report = run_benchmark(scenarios, token)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Saved: {args.output}")
    print("Human usefulness scores remain blank until reviewed by a person.")

    return 0 if report["summary"]["schema_success_rate_pct"] == 100.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
