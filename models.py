from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanningDepth(str, Enum):
    QUICK = "Quick"
    STANDARD = "Standard"
    DETAILED = "Detailed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    PLANNED = "planned"
    BLOCKED = "blocked"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    REPLANNING = "REPLANNING"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class HumanDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class PlanningModel(BaseModel):
    """Shared strict configuration for the Agent 02 planning contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MissionRequest(PlanningModel):
    """Structured input supplied to the planning engine."""

    mission_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    search_area: str = Field(min_length=1)
    available_resources: list[str] = Field(default_factory=list)
    sensors: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    approval_rules: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(min_length=1)
    planning_depth: PlanningDepth = PlanningDepth.STANDARD


class MissionTask(PlanningModel):
    """One executable unit in the mission plan graph."""

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    assigned_resources: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    human_approval_required: bool = False
    completion_criteria: list[str] = Field(min_length=1)
    status: TaskStatus = TaskStatus.PLANNED


class MissionPlan(PlanningModel):
    """Machine-readable plan proposed by the planner."""

    mission_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    tasks: list[MissionTask] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    covered_constraints: list[str] = Field(default_factory=list)
    approval_gates: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(min_length=1)
    next_action: str = Field(min_length=1)
    plan_status: PlanStatus = PlanStatus.DRAFT


class ValidationResult(PlanningModel):
    """Structured result from deterministic plan validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dependency_issues: list[str] = Field(default_factory=list)
    resource_conflicts: list[str] = Field(default_factory=list)
    constraint_violations: list[str] = Field(default_factory=list)
    approval_issues: list[str] = Field(default_factory=list)
    replan_required: bool = False


class ReplanAttempt(PlanningModel):
    """One bounded replanning attempt and its validation result."""

    attempt_number: int = Field(ge=1)
    plan: MissionPlan
    validation_result: ValidationResult


class PlanningRunRecord(PlanningModel):
    """Auditable record for one end-to-end planning run."""

    run_id: str = Field(min_length=1)
    mission_request: MissionRequest
    initial_plan: Optional[MissionPlan] = None
    validation_results: list[ValidationResult] = Field(default_factory=list)
    replan_attempts: list[ReplanAttempt] = Field(default_factory=list)
    final_plan: Optional[MissionPlan] = None
    final_status: PlanStatus = PlanStatus.DRAFT
    human_decision: HumanDecision = HumanDecision.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
