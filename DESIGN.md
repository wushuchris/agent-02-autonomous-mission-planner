# Agent 02 Design Specification

## Planning Agent — Constraint-Aware Search and Rescue Mission Planner

This document defines the upgrade path for Agent 02 in the **30 Agents for AI Engineers** portfolio.

The project remains a humanitarian search and rescue planning demonstration, but the engineering goal is broader: build a reusable planning-agent primitive that can convert objectives, constraints, resources, and success criteria into a validated, auditable execution plan.

> **Engineering pattern:** The LLM proposes. Rules validate. The agent replans. Humans approve.

---

## 1. Business Case

Organizations often struggle with complex objectives because planning information is incomplete, dependencies are missed, constraints are ignored, risks are not made explicit, and human approval points are unclear.

A planning agent can create business value by:

- reducing the time required to turn a high-level objective into an actionable plan;
- making assumptions and missing information explicit;
- identifying dependencies, resource conflicts, and operational risks before execution;
- improving consistency in planning workflows;
- preserving human approval for consequential decisions;
- creating an auditable planning record;
- supporting repeatable planning across operations, incident response, logistics, research, project execution, and multi-agent coordination.

The search and rescue scenario is the domain implementation used to demonstrate this pattern. The underlying planning primitive is intended to be reusable outside that domain.

### Business Value Demonstrated

The upgraded agent should demonstrate:

1. **Faster structured planning** — convert ambiguous intent into an organized plan.
2. **Reduced omission risk** — expose assumptions, missing inputs, dependencies, and constraints.
3. **Better decision visibility** — show why a plan is valid or why it failed validation.
4. **Human control** — require approval where policy or risk demands it.
5. **Auditability** — retain the original request, generated plan, validation results, replan attempts, and final disposition.
6. **Reusable planning capability** — provide a planning primitive that can later support orchestration and multi-agent systems.

---

## 2. Engineering Case

Free-form LLM plans can be useful, but they are not reliable enough to accept as execution plans without validation.

The engineering problem is therefore not simply:

> Generate a plan.

It is:

> Convert intent into a machine-readable plan, validate it deterministically, identify infeasible or inconsistent elements, replan within bounded limits, require human approval where appropriate, and preserve an audit trail.

The upgraded system should separate probabilistic reasoning from deterministic control.

The LLM is responsible for proposing a plan. Deterministic code is responsible for validating structural and policy requirements. The agent may revise a failed plan within a bounded number of attempts. Human approval remains required for defined checkpoints.

---

## 3. Reusable Agent Primitive

The core reusable primitive is:

```text
Objective
+ Constraints
+ Available Resources
+ Success Criteria
+ Approval Policy
        ↓
Validated PlanGraph
```

The search and rescue interface is one implementation of that primitive.

Future agents should be able to call the same planning engine without depending on Streamlit or search-and-rescue-specific UI code.

---

## 4. Scope

### In Scope

- structured planning from high-level objectives;
- task decomposition;
- explicit assumptions and unresolved questions;
- dependency modeling;
- resource assignment;
- risk classification;
- success and completion criteria;
- deterministic plan validation;
- bounded replanning;
- human approval gates;
- audit logging;
- evaluation of planning quality;
- humanitarian search and rescue as the demonstration domain.

### Out of Scope

- autonomous real-world mission execution;
- direct control of drones, vehicles, robots, or emergency systems;
- replacement of trained responders or incident commanders;
- weaponization, targeting, attack planning, evasion, or harmful engagement logic;
- unlimited autonomous replanning;
- claims that a generated plan is operationally safe without qualified human review.

---

## 5. Target Architecture

```text
Business / Mission Objective
            ↓
Structured Mission Request
            ↓
Input Validation
            ↓
LLM Planner
            ↓
Structured MissionPlan
            ↓
Plan Graph Construction
            ↓
Deterministic Plan Validator
       ┌────┴────┐
       │         │
      FAIL      PASS
       │         │
Validation      Human Approval Gate
Feedback         │
       │         ↓
Bounded Replan   Final Approved Plan
       │         ↓
       └────→ Audit Record
```

The architecture deliberately separates:

- **planning** from **validation**;
- **model judgment** from **deterministic rules**;
- **proposal** from **approval**;
- **domain UI** from the **reusable planning engine**.

---

## 6. Core Data Models

The first implementation step should define Pydantic models for the planning contract.

### MissionRequest

Represents the structured input to the planner.

Suggested fields:

- `mission_id`
- `objective`
- `environment`
- `search_area`
- `available_resources`
- `sensors`
- `constraints`
- `approval_rules`
- `success_criteria`
- `planning_depth`

### MissionTask

Represents one executable planning unit.

Suggested fields:

- `task_id`
- `title`
- `description`
- `dependencies`
- `assigned_resources`
- `risk_level`
- `human_approval_required`
- `completion_criteria`
- `status`

### MissionPlan

Represents the planner's machine-readable output.

Suggested fields:

- `mission_id`
- `summary`
- `assumptions`
- `unresolved_questions`
- `milestones`
- `tasks`
- `risks`
- `approval_gates`
- `success_criteria`
- `next_action`
- `plan_status`

### ValidationResult

Represents deterministic review of a proposed plan.

Suggested fields:

- `valid`
- `errors`
- `warnings`
- `dependency_issues`
- `resource_conflicts`
- `constraint_violations`
- `approval_issues`
- `replan_required`

### PlanningRunRecord

Represents the audit record for one planning attempt.

Suggested fields:

- `run_id`
- `mission_request`
- `initial_plan`
- `validation_results`
- `replan_attempts`
- `final_plan`
- `final_status`
- `human_decision`
- `timestamps`

---

## 7. Deterministic Validation Rules

The validator should check conditions that do not require model judgment.

Initial validation rules should include:

1. task IDs are unique;
2. every dependency refers to an existing task;
3. the dependency graph contains no circular dependencies;
4. required resources exist in the mission request;
5. resources are not assigned in logically conflicting ways where conflicts can be determined from the plan;
6. every task has completion criteria;
7. required approval gates exist;
8. tasks marked as approval-sensitive cannot proceed without approval;
9. explicit mission constraints are represented in the plan;
10. unresolved critical information is surfaced rather than silently invented;
11. the plan contains a next action;
12. the plan conforms to the Pydantic schema.

The validator should return structured errors rather than only a pass/fail string.

---

## 8. Bounded Replanning Loop

A failed validation should not automatically terminate the planning attempt.

The planner should receive structured validation feedback and be allowed to revise the plan within a fixed retry budget.

Initial policy:

```text
Maximum replan attempts: 2
```

Expected behavior:

```text
Generate Plan
    ↓
Validate
    ↓
PASS → Approval Gate

FAIL → Return validation errors to planner
    ↓
Replan
    ↓
Validate again
```

If the retry budget is exhausted, the system should stop and return a safe failure state such as:

```text
PLAN_REQUIRES_HUMAN_REVIEW
```

It should never silently accept an invalid plan.

---

## 9. Human-in-the-Loop Approval

Human approval should become an enforced state transition rather than text that merely appears in the generated plan.

Possible plan states:

```text
DRAFT
VALIDATION_FAILED
REPLANNING
AWAITING_HUMAN_APPROVAL
APPROVED
REJECTED
REQUIRES_HUMAN_REVIEW
```

A valid plan that requires approval should stop at:

```text
AWAITING_HUMAN_APPROVAL
```

The user should be able to:

- approve the plan;
- reject the plan;
- request revision.

The resulting decision should be retained in the audit record.

---

## 10. Evaluation Strategy

The upgraded agent should include an explicit evaluation suite rather than relying on subjective review of generated prose.

### Minimum Evaluation Package

- 10 success cases
- 5 edge cases
- 5 failure cases
- adversarial or prompt-injection tests where relevant

### Evaluation Dimensions

The initial scorecard should evaluate:

- schema validity;
- task completeness;
- dependency validity;
- constraint adherence;
- resource consistency;
- milestone coverage;
- human-approval compliance;
- unresolved-information handling;
- safe failure behavior;
- replanning success;
- audit-record completeness.

### Example Test Scenarios

1. straightforward missing-person search with sufficient resources;
2. missing critical mission information;
3. a task referencing a nonexistent dependency;
4. circular task dependencies;
5. one resource assigned to incompatible simultaneous tasks;
6. a mission requiring approval but lacking an approval gate;
7. conflicting success criteria and operational constraints;
8. planner invents a resource not supplied by the user;
9. malformed model output;
10. repeated validation failure triggering safe escalation;
11. user input containing instructions that attempt to override system planning rules;
12. incomplete or ambiguous mission objective requiring clarification or explicit assumptions.

---

## 11. Safety and Security Requirements

The upgraded design should preserve the existing humanitarian boundary and add engineering controls around it.

Requirements:

- mission text is treated as untrusted input data, not as system instructions;
- system-level safety rules cannot be overridden by user-provided mission content;
- secrets are loaded only from environment variables or platform secret stores;
- secrets are never written to audit records;
- generated plans must remain advisory and human-reviewed;
- validation failures must fail closed rather than being hidden;
- no direct real-world actuator or drone-control integration is included in this portfolio implementation;
- harmful, weaponized, targeting, attack, evasion, or tactical engagement requests remain outside project scope.

---

## 12. Auditability and Observability

Every planning run should make it possible to answer:

- What did the user ask for?
- What assumptions did the planner make?
- What plan did the model propose?
- What validation errors were found?
- Was replanning attempted?
- What changed between attempts?
- Did the final plan pass validation?
- Was human approval required?
- What did the human decide?

The audit record should be machine-readable JSON and suitable for later evaluation or batch analysis.

---

## 13. Product / Demo Experience

The Streamlit app should eventually present both the **business value** and the **engineering behavior**.

The UI should make visible:

- the original mission request;
- the structured plan;
- validation status;
- validation warnings and errors;
- replan attempt count;
- approval status;
- final plan status;
- downloadable Markdown plan;
- downloadable structured JSON audit record.

This helps the portfolio viewer understand that the project is not simply an LLM prompt wrapper.

---

## 14. Portfolio Story

### Why would an organization use this?

To turn complex objectives into structured plans faster while exposing assumptions, dependencies, resource conflicts, risks, and approval requirements.

### What engineering problem does it solve?

It addresses the unreliability of free-form LLM planning by introducing schemas, graph validation, deterministic checks, bounded replanning, approval gates, and auditability.

### What reusable agent pattern does it teach?

A constraint-aware planning agent:

> **The LLM proposes. Rules validate. The agent replans. Humans approve.**

### How do we know it works?

Through repeatable evaluation of schema validity, dependency correctness, constraint compliance, resource consistency, human-approval behavior, safe failure handling, and bounded replanning.

---

## 15. Future Portfolio Reuse

Agent 02 should become the centralized planning baseline for later portfolio agents.

Potential reuse includes:

- orchestrator agents;
- multi-agent task decomposition;
- tool-using workflows;
- human approval workflows;
- centralized versus decentralized planning benchmarks;
- plan evaluation for agent teams.

The target reusable interface should eventually resemble:

```python
plan_result = planner.plan(
    objective=objective,
    constraints=constraints,
    resources=resources,
    success_criteria=success_criteria,
    approval_policy=approval_policy,
)
```

The result should contain the validated structured plan, validation record, plan status, and audit metadata.

---

## 16. Incremental Implementation Plan

The upgrade should be built in small, understandable steps.

### Phase 1 — Planning Contract

Create Pydantic schemas for:

- `MissionRequest`
- `MissionTask`
- `MissionPlan`
- `ValidationResult`
- `PlanningRunRecord`

### Phase 2 — Structured Planner

Change the LLM interaction from Markdown-only output to structured plan generation.

### Phase 3 — Plan Graph and Validator

Build deterministic dependency, resource, constraint, completion-criteria, and approval checks.

### Phase 4 — Bounded Replanning

Feed validation failures back to the planner with a maximum retry count.

### Phase 5 — Human Approval State Machine

Add explicit approval, rejection, and revision states.

### Phase 6 — Audit Layer

Capture complete planning run records and export JSON.

### Phase 7 — Evaluation Suite

Implement success, edge, failure, and adversarial test cases with measurable results.

### Phase 8 — Streamlit Upgrade

Expose planning, validation, replanning, approval, and audit behavior in the UI.

### Phase 9 — Documentation and Portfolio Review

Update the README to present:

- business case;
- engineering case;
- architecture;
- reusable primitive;
- evaluation evidence;
- failure modes;
- limitations;
- production upgrade path;
- relationship to future agents.

---

## 17. Definition of Done

The Agent 02 upgrade is complete when:

- planning inputs and outputs use typed schemas;
- the planner generates machine-readable plans;
- plans are represented as dependency graphs;
- deterministic validation is enforced;
- invalid plans trigger bounded replanning;
- repeated failure escalates safely;
- human approval is an explicit system state;
- planning runs generate auditable records;
- automated evaluation covers success, edge, failure, and adversarial cases;
- the Streamlit demo exposes the engineering behavior clearly;
- the README explains both the business case and engineering case;
- the planning engine can be reused independently of the search and rescue UI.

At that point, Agent 02 will function as both a polished portfolio application and a reusable planning primitive for later agents in the 30-agent curriculum.

## Phase 3 Implementation Note

Phase 3 now provides `plan_graph.py`, `validator.py`, focused regression tests and
Streamlit validation visibility. See the README for exact matching and approval policy.
The only additive contract field is `MissionPlan.covered_constraints` (default `[]`),
which makes representation mechanically checkable without claiming semantic compliance.
Resource capacity/scheduling and approval gate applicability/timing remain human-review
limitations of the existing text-based contract. Approval rules conservatively gate all
tasks, and high/critical risk tasks require approval. No trusted approval is recorded yet.
Phase 4 bounded replanning is implemented below. Phase 5 human decisions and Phase 6 audit logging remain pending.

## Phase 4 Implementation Note

`planning_engine.py` permits two revisions after a deterministically invalid initial
proposal and passes the latest plan and structured validation feedback to the existing
planner. Every schema-valid revision is deterministically validated. Success stops
replanning; exhaustion escalates the invalid proposal to `REQUIRES_HUMAN_REVIEW`.
Malformed revision output or provider failure stops early with the last invalid
proposal retained for review. Initial generation errors still fail closed without
retries. Streamlit exposes attempt counts, revision results and the reason for stopping.
No human approval is inferred and no execution is enabled. Full audit persistence,
trusted human decision capture and provider resilience remain outside this phase.

## Phase 5 Implementation Note

`approval.py` now applies explicit human approve/reject/request-revision decisions to
reviewable proposals. Approval revalidates the saved request and plan; fingerprints
reject stale content, and terminal decisions cannot be overwritten. Revision requires
notes and uses the additive `REVISION_REQUESTED` plan state. A new generation clears
the previous decision. Revision requests require manual input changes and a fresh run,
not an automatic model call. Session review records include decision, notes, timestamp
and fingerprint; they do not authenticate the reviewer or authorize real-world execution.
Phase 6 remains responsible for complete planning-run audit records and persistence.

## Phase 6 Implementation Note

The planning engine now fills `PlanningRunRecord` from initial generation through
validation, revisions and final disposition. All model calls, including malformed or
failed calls, have timestamps and fixed outcome/error codes. Human review retains the
pre-decision snapshot and final decision details. Streamlit exports the complete JSON
record even when initial generation fails. Raw provider errors and credentials are not
captured. Persistence is by user download; automated server-side storage and authenticated
reviewer identities remain production extensions. Phase 7's full evaluation package is
still pending, distinct from the 30 focused regression tests delivered through Phase 6.

## Phase 7 Implementation Note

The offline package now contains 10 success, 5 edge, 7 failure and 3 adversarial proposal
fixtures, a JSON scorecard and failure-exit CLI. The 32-test regression suite covers
workflow, review and audit behavior. CI runs both packages. `evaluation/README.md` maps
every design dimension to evidence or an explicit measurement limit. Semantic plan
quality and live-model prompt-injection resistance remain unmeasured; fixture success
must not be described as operational readiness. Phases 8 and 9 remain next.

## Phases 8–9 Implementation Note

The interface now follows mission input → saved request/proposal and validation evidence
→ human decision → downloads. Review controls follow the proposal; warnings and detailed
engineering data are expandable. Planning and approval policy are unchanged. The README
now consolidates current business/engineering framing, architecture, setup, exact checks,
failure behavior, audit limits, evaluation evidence and deployment status. Earlier phase
notes are historical. The repository implementation is complete through Phase 9; live-model
quality evaluation and Hugging Face redeployment remain separate work, and production
limitations are explicitly documented rather than treated as resolved.
