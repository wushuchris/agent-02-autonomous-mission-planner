"""Planning run snapshots and JSON export, without credentials or raw errors."""
import os
from datetime import datetime, timezone
from uuid import uuid4

from approval import ReviewDecision, proposal_fingerprint
from models import HumanDecision, MissionPlan, MissionRequest, PlanningRunRecord


def new_run(request: MissionRequest) -> PlanningRunRecord:
    model_name = os.getenv("MODEL_ID", "").strip() or "MODEL_ID not configured"
    return PlanningRunRecord(
        run_id=uuid4().hex,
        mission_request=request.model_copy(deep=True),
        model_name=model_name,
    )


def record_decision(run: PlanningRunRecord, plan: MissionPlan, decision: ReviewDecision) -> PlanningRunRecord:
    """Return a new audit snapshot bound to the proposal actually reviewed."""
    if run.human_decision != HumanDecision.PENDING or run.reviewable_plan is None:
        raise ValueError("This run is not awaiting a review decision.")
    if decision.proposal_fingerprint != proposal_fingerprint(run.mission_request, run.reviewable_plan):
        raise ValueError("Review decision does not match this run's proposal.")
    # Reuse the transition checks instead of trusting caller-supplied final status.
    from approval import decide_proposal
    expected, _ = decide_proposal(run.mission_request, run.reviewable_plan, decision.decision,
                                  decision.proposal_fingerprint, decision.notes)
    if expected != plan:
        raise ValueError("Final plan does not match the human review transition.")
    updated = run.model_copy(deep=True)
    updated.final_plan = plan.model_copy(deep=True)
    updated.final_status = plan.plan_status
    updated.human_decision = decision.decision
    updated.review_notes = decision.notes
    updated.review_fingerprint = decision.proposal_fingerprint
    updated.reviewed_at = decision.decided_at
    updated.updated_at = datetime.now(timezone.utc)
    return updated


def export_run(run: PlanningRunRecord) -> str:
    """Produce a standalone JSON snapshot suitable for saving and reloading."""
    return run.model_dump_json(indent=2)
