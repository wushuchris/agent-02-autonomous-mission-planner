"""Human review transitions for advisory proposals; no operational execution."""
import hashlib
import json
from datetime import datetime, timezone

from pydantic import Field

from models import HumanDecision, MissionPlan, MissionRequest, PlanningModel, PlanStatus
from validator import validate_plan


class ReviewDecision(PlanningModel):
    decision: HumanDecision
    proposal_fingerprint: str
    notes: str = ""
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def proposal_fingerprint(request: MissionRequest, plan: MissionPlan) -> str:
    payload = {"request": request.model_dump(mode="json"), "plan": plan.model_dump(mode="json")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def decide_proposal(request: MissionRequest, plan: MissionPlan, decision: HumanDecision,
                    expected_fingerprint: str, notes: str = "") -> tuple[MissionPlan, ReviewDecision]:
    """Apply one human decision to an unchanged reviewable proposal.

    Caller must obtain the decision from a human UI, never model output. The
    fingerprint detects stale proposals, not identity or authorization. Sessions
    have no authentication or durable audit store in this educational prototype.
    """
    if plan.plan_status not in (PlanStatus.AWAITING_HUMAN_APPROVAL, PlanStatus.REQUIRES_HUMAN_REVIEW):
        raise ValueError("This proposal is not awaiting a human decision.")
    if proposal_fingerprint(request, plan) != expected_fingerprint:
        raise ValueError("The proposal changed. Review the current proposal before deciding.")
    if decision == HumanDecision.APPROVED:
        if not validate_plan(request, plan).valid:
            raise ValueError("Invalid proposals cannot be approved. Request revision or reject the proposal.")
        status = PlanStatus.APPROVED
    elif decision == HumanDecision.REJECTED:
        status = PlanStatus.REJECTED
    elif decision == HumanDecision.REVISION_REQUESTED:
        if not notes.strip():
            raise ValueError("Describe the changes needed before requesting revision.")
        status = PlanStatus.REVISION_REQUESTED
    else:
        raise ValueError("Choose approve, reject or request revision.")
    record = ReviewDecision(decision=decision, proposal_fingerprint=expected_fingerprint, notes=notes)
    return plan.model_copy(update={"plan_status": status}), record
