"""Deterministic proposal checks. Passing is never operational approval."""
from models import MissionPlan, MissionRequest, PlanStatus, RiskLevel, TaskStatus, ValidationResult
from plan_graph import build_plan_graph


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


def validate_plan(request: MissionRequest, plan: MissionPlan) -> ValidationResult:
    """Validate typed proposals without modifying them or calling the planner.

    Resource labels and policy entries match whole strings after case/whitespace
    normalization. Free-text meaning, capacity, timing and feasibility are not inferred.
    """
    graph = build_plan_graph(plan)
    errors = list(graph.errors)
    resources, constraints, approvals = [], [], []
    warnings = [
        "Passing deterministic checks does not establish operational safety or full semantic validity. Qualified human review is required.",
        "Resource capacity, scheduling conflicts and factual completeness cannot be verified from the current contract.",
    ]
    if request.mission_id != plan.mission_id:
        errors.append("Plan mission_id does not match the request.")
    if not plan.tasks:
        errors.append("Plan must contain at least one task.")
    if not plan.next_action.strip():
        errors.append("Plan is missing a next action.")
    available = {_key(item) for item in request.available_resources if item.strip()}
    rules = {_key(item) for item in request.approval_rules if item.strip()}
    gates = {_key(item) for item in plan.approval_gates if item.strip()}
    for rule in request.approval_rules:
        if not rule.strip() or _key(rule) not in gates:
            approvals.append(f"Approval rule missing from approval_gates: {rule!r}")
    for task in plan.tasks:
        if not task.completion_criteria or any(not item.strip() for item in task.completion_criteria):
            errors.append(f"Task {task.task_id} has missing or blank completion criteria.")
        for resource in task.assigned_resources:
            if not resource.strip() or _key(resource) not in available:
                resources.append(f"Task {task.task_id} assigns an unavailable resource: {resource!r}")
        # Conservative policy until task-specific approval rules and trusted decisions exist.
        sensitive = bool(rules) or task.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        if sensitive and not task.human_approval_required:
            approvals.append(f"Task {task.task_id} must require human approval (request policy or high/critical risk).")
        if sensitive or task.human_approval_required:
            if not gates:
                approvals.append(f"Task {task.task_id} requires a nonblank approval gate.")
            if task.status not in (TaskStatus.PLANNED, TaskStatus.BLOCKED):
                approvals.append(f"Task {task.task_id} cannot be {task.status.value} without a trusted human approval record.")
    if plan.plan_status == PlanStatus.APPROVED:
        approvals.append("A proposed plan cannot claim APPROVED without a trusted human decision.")
    covered = {_key(item) for item in plan.covered_constraints if item.strip()}
    requested = {_key(item) for item in request.constraints if item.strip()}
    for constraint in request.constraints:
        if not constraint.strip() or _key(constraint) not in covered:
            constraints.append(f"Constraint missing from covered_constraints: {constraint!r}")
    for constraint in plan.covered_constraints:
        if not constraint.strip() or _key(constraint) not in requested:
            constraints.append(f"Unrecognized covered constraint: {constraint!r}")
    if request.constraints:
        warnings.append("Constraint coverage checks explicit representation only; compliance with free-text constraints requires human review.")
    if rules or gates:
        warnings.append("Approval gates are text: rule applicability, gate timing and actual approval require human review. Request approval rules conservatively gate every task.")
    if any(item.strip() for item in plan.unresolved_questions):
        warnings.append("Unresolved questions remain; a human must assess their criticality before using this proposal.")
    errors.extend(resources + constraints + approvals)
    return ValidationResult(
        valid=not errors, errors=errors, warnings=warnings,
        dependency_issues=graph.errors, resource_conflicts=resources,
        constraint_violations=constraints, approval_issues=approvals,
        replan_required=bool(errors),
    )


def apply_validation_status(plan: MissionPlan, result: ValidationResult) -> MissionPlan:
    """Return an advisory proposal; never authorize execution or perform retries."""
    status = PlanStatus.VALIDATION_FAILED
    if result.valid:
        status = PlanStatus.REQUIRES_HUMAN_REVIEW
        if any(task.human_approval_required for task in plan.tasks) or plan.approval_gates:
            status = PlanStatus.AWAITING_HUMAN_APPROVAL
    return plan.model_copy(update={"plan_status": status})
