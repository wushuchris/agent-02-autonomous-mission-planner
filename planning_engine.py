"""Bounded generate/validate/revise workflow, independent of Streamlit."""
from dataclasses import dataclass, field

import planner
from models import MissionPlan, MissionRequest, PlanStatus, ReplanAttempt, ValidationResult
from validator import apply_validation_status, validate_plan

MAX_REPLAN_ATTEMPTS = 2


@dataclass
class PlanningOutcome:
    plan: MissionPlan
    validation: ValidationResult
    replan_count: int = 0
    attempts: list[ReplanAttempt] = field(default_factory=list)
    stopped_reason: str = ""


def run_planning(mission_request: MissionRequest, hf_token: str) -> PlanningOutcome:
    """At most three planner calls: initial proposal plus two revisions.

    Initial generation errors propagate to the caller. A failed revision stops the
    loop and retains the last schema-valid but deterministically invalid proposal,
    explicitly escalated for human review. Provider errors are never exposed raw.
    """
    plan = planner.generate_structured_plan(mission_request=mission_request, hf_token=hf_token)
    validation = validate_plan(mission_request, plan)
    outcome = PlanningOutcome(plan=plan, validation=validation)
    while not validation.valid and outcome.replan_count < MAX_REPLAN_ATTEMPTS:
        outcome.replan_count += 1
        try:
            revised = planner.generate_structured_plan(
                mission_request=mission_request, hf_token=hf_token,
                previous_plan=plan, validation_feedback=validation,
            )
        except planner.PlannerOutputError:
            outcome.stopped_reason = "Replanning stopped: the revised output failed schema or mission identity checks. The last invalid proposal is shown for human review."
            break
        except Exception:
            outcome.stopped_reason = "Replanning stopped because the planning service failed. The last invalid proposal is shown for human review."
            break
        plan = revised
        validation = validate_plan(mission_request, plan)
        outcome.attempts.append(ReplanAttempt(
            attempt_number=outcome.replan_count, plan=plan, validation_result=validation))
    outcome.validation = validation
    if validation.valid:
        outcome.plan = apply_validation_status(plan, validation)
    else:
        outcome.plan = plan.model_copy(update={"plan_status": PlanStatus.REQUIRES_HUMAN_REVIEW})
        if not outcome.stopped_reason:
            outcome.stopped_reason = "Both replanning attempts failed deterministic validation. Human review is required; this proposal is not ready for use."
    return outcome
