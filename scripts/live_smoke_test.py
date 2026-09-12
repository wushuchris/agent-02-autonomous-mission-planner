"""Deliberate live-provider smoke test for the end-to-end planning path.

This script is intentionally excluded from normal CI because it consumes live inference.
It verifies runtime configuration, provider connectivity, structured planning, deterministic
validation and bounded replanning on one synthetic humanitarian scenario.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

from model_adapter import ModelConfigurationError, ModelServiceError
from models import MissionRequest, PlanningDepth
from planner import PlannerOutputError
from planning_engine import run_planning


load_dotenv()


def build_smoke_request() -> MissionRequest:
    return MissionRequest(
        mission_id="sar-live-smoke",
        objective="Create a safe, advisory plan for one documented search sweep around a missing hiker's last known location.",
        environment="Wilderness trail with moderate tree cover and uneven terrain.",
        search_area="30-meter radius around the last known location",
        available_resources=[
            "2 small drones with cameras",
            "1 ground search team",
            "1 incident coordinator",
            "radio communication",
        ],
        sensors=["RGB cameras", "GPS positioning", "telemetry feed"],
        constraints=[
            "Preserve battery life",
            "Maintain visual line of sight",
            "Maintain communication with the ground team",
            "Do not enter unsafe terrain without responder review",
        ],
        approval_rules=[
            "The incident coordinator must confirm the search area",
            "The incident coordinator must approve any search-area expansion",
        ],
        success_criteria=[
            "Complete one structured sweep",
            "Document findings and hazards",
            "Recommend the next safe search action",
        ],
        planning_depth=PlanningDepth.STANDARD,
    )


def main() -> int:
    token = os.getenv("HF_TOKEN", "").strip()
    model_id = os.getenv("MODEL_ID", "").strip()
    base_url = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1").strip()

    print("Agent 02 live inference smoke test")
    print(f"Model: {model_id or 'MODEL_ID not configured'}")
    print(f"Endpoint: {base_url}")

    try:
        outcome = run_planning(build_smoke_request(), token)
    except (ModelConfigurationError, ModelServiceError, PlannerOutputError) as exc:
        print(f"FAIL: {exc}")
        return 1
    except Exception:
        print("FAIL: unexpected planning service error; raw provider details are intentionally hidden.")
        return 1

    print(f"Replanning attempts: {outcome.replan_count} / 2")
    print(f"Final status: {outcome.plan.plan_status.value}")
    print(f"Deterministic validation: {'PASS' if outcome.validation.valid else 'FAIL'}")

    if not outcome.validation.valid:
        for error in outcome.validation.errors:
            print(f"- {error}")
        return 1

    print("PASS: live provider returned a schema-valid plan that passed deterministic validation.")
    print("Reminder: this smoke test does not establish operational search-and-rescue safety.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
