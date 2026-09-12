"""Bounded generate/validate/revise workflow, independent of Streamlit."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from audit import new_run

import planner
from models import MissionPlan, MissionRequest, PlanStatus, ReplanAttempt, ValidationResult, PlanningRunRecord, PlanningCallRecord
from validator import apply_validation_status, validate_plan

MAX_REPLAN_ATTEMPTS = 2


@dataclass
class PlanningOutcome:
    plan: MissionPlan
    validation: ValidationResult
    replan_count: int = 0
    attempts: list[ReplanAttempt] = field(default_factory=list)
    stopped_reason: str = ""
    audit_record: PlanningRunRecord | None = None


def run_planning(mission_request: MissionRequest, hf_token: str, *,
                 audit_record: PlanningRunRecord | None = None) -> PlanningOutcome:
    """At most three planner calls: initial proposal plus two revisions.

    Initial generation errors propagate to the caller. A failed revision stops the
    loop and retains the last schema-valid but deterministically invalid proposal,
    explicitly escalated for human review. Provider errors are never exposed raw.
    """
    run = audit_record if audit_record is not None else new_run(mission_request)
    if run.mission_request != mission_request or run.calls or run.initial_plan is not None:
        raise ValueError("Audit record must be a fresh run for this request.")

    def generate(attempt_number, **feedback):
        started = datetime.now(timezone.utc)
        error_code = None
        try:
            return planner.generate_structured_plan(mission_request=mission_request, hf_token=hf_token, **feedback)
        except planner.PlannerOutputError:
            error_code = "PLANNER_OUTPUT_ERROR"
            raise
        except Exception:
            error_code = "PLANNING_SERVICE_ERROR"
            raise
        finally:
            completed = datetime.now(timezone.utc)
            run.calls.append(PlanningCallRecord(attempt_number=attempt_number,
                started_at=started, completed_at=completed,
                outcome="failed" if error_code else "schema_valid", error_code=error_code))
            run.updated_at = completed
            if error_code:
                run.final_status = PlanStatus.REQUIRES_HUMAN_REVIEW
                run.stop_reason = error_code

    plan = generate(0)
    run.initial_plan = plan.model_copy(deep=True)
    validation = validate_plan(mission_request, plan)
    run.validation_results.append(validation.model_copy(deep=True))
    outcome = PlanningOutcome(plan=plan, validation=validation, audit_record=run)
    while not validation.valid and outcome.replan_count < MAX_REPLAN_ATTEMPTS:
        outcome.replan_count += 1
        try:
            revised = generate(
                outcome.replan_count,
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
        run.validation_results.append(validation.model_copy(deep=True))
        outcome.attempts.append(ReplanAttempt(
            attempt_number=outcome.replan_count, plan=plan, validation_result=validation))
    outcome.validation = validation
    if validation.valid:
        outcome.plan = apply_validation_status(plan, validation)
    else:
        outcome.plan = plan.model_copy(update={"plan_status": PlanStatus.REQUIRES_HUMAN_REVIEW})
        if not outcome.stopped_reason:
            outcome.stopped_reason = "Both replanning attempts failed deterministic validation. Human review is required; this proposal is not ready for use."
    run.replan_attempts = [attempt.model_copy(deep=True) for attempt in outcome.attempts]
    run.final_plan = outcome.plan.model_copy(deep=True)
    run.reviewable_plan = outcome.plan.model_copy(deep=True)
    run.final_status = outcome.plan.plan_status
    run.stop_reason = outcome.stopped_reason
    run.updated_at = datetime.now(timezone.utc)
    return outcome
