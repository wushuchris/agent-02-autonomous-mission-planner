# Search and Rescue Mission Planning Agent

Agent 2 in my **30 Agents for AI Engineers** portfolio.

This project is a human-in-the-loop mission planning assistant for search and rescue scenarios. It converts high-level rescue intent into structured mission plans with search phases, asset allocation, risks, communication checkpoints, safety considerations, and next best actions.

## Important Disclaimer

This project is an educational portfolio prototype for search and rescue planning. It is not a production emergency response system, does not replace trained responders or incident commanders, and should not be used for real-world mission execution without proper validation, safety controls, legal review, and human supervision.

## Project Purpose

Search and rescue operations often require teams to make decisions under uncertainty, limited visibility, changing weather, terrain constraints, and incomplete information.

This agent demonstrates how an AI planning system can help organize a safe and structured response plan for humanitarian and emergency scenarios. It is designed to support planning, not replace trained responders or incident commanders.

## What the Agent Does

The agent takes mission inputs such as:

- Rescue objective
- Search environment
- Search area
- Available assets
- Sensor payloads
- Operational constraints
- Human approval rules
- Success criteria
- Planning depth

It returns a structured mission plan with:

- Mission summary
- Mission assumptions
- Search phases
- Asset allocation
- Dependencies
- Risk assessment
- Human-in-the-loop checkpoints
- Safe response recommendations
- Success criteria review
- Next best action

## Safety Boundary

This project is designed for humanitarian, emergency response, and public safety planning. It does not provide support for weaponization, targeting, attack planning, evasion, or harmful engagement logic.

The agent focuses on:

- Search and rescue
- Missing person response
- Disaster response
- Infrastructure inspection after emergencies
- Wilderness search planning
- Flood, wildfire, or earthquake response
- Operator alerts
- Human approval workflows

## Example Use Case

An incident coordinator provides the following intent:

> Search a 30-meter area around the last known location of a missing hiker, complete one full sweep, report findings, identify possible hazards, and recommend the next safest search action.

The agent converts that intent into a structured plan with search phases, asset tasking, risks, checkpoints, and next actions.

## Tech Stack

- Python
- Streamlit
- Hugging Face Inference API
- Qwen/Qwen2.5-7B-Instruct
- python-dotenv

## Portfolio Context

This is part of my broader **30 Agents for AI Engineers** learning portfolio.

Agent 1 focused on autonomous decision-making.

Agent 2 focuses on planning: decomposing a complex objective into structured, executable steps with dependencies, risks, and human oversight.

## Disclaimer

This project is for educational and portfolio purposes. It is not a production emergency response system and should not be used for real-world mission execution without trained responders, appropriate engineering validation, safety controls, legal review, and human supervision.
## Phase 3 — Plan Graph and Deterministic Validator

**Business case:** Reduce omissions before a person reviews a proposal by exposing
broken dependencies, unavailable resources, missing constraint coverage and approval requirements.

**Engineering case:** Separate the LLM proposal from repeatable checks that run without
an LLM or Streamlit. The Phase 3 foundation is:

```text
MissionRequest → structured planner → MissionPlan schema check
→ dependency graph → deterministic validator → advisory proposal + ValidationResult
```

- `plan_graph.py` checks unique task IDs, missing dependencies and cycles (including
  self-dependencies), and returns a topological order for structurally valid graphs.
  If IDs or references are invalid, graph sorting/cycle analysis is deferred until
  they are repaired. The order is not a schedule or authorization to execute.
- `validator.py` checks resource membership, nonblank completion criteria, next-action
  presence, mission identity, explicit constraint representation and approval requirements.
  Errors are available both in `errors` and the existing category lists;
  `resource_conflicts` currently contains membership errors, not capacity analysis.
- `MissionPlan.covered_constraints` is a backward-compatible field defaulting to `[]`.
  The planner copies each request constraint into it. Missing or unknown entries fail
  validation. Whole-entry matching ignores case and repeated whitespace, but not wording.
  Copying a constraint proves representation only, **not semantic compliance**.
- Resource assignments must use exact `available_resources` labels (ignoring case and
  repeated whitespace). Quantity labels are not split into inferred units; sensors are
  context, not separately assignable resources unless also listed as available resources.
- Each request approval rule must appear in `approval_gates`. Because free-text rules
  cannot reliably be assigned to individual tasks, any request approval rule conservatively
  requires **every task** to set `human_approval_required`. High/critical risk tasks also
  require approval. Sensitive tasks need a nonblank gate and must stay `planned` or
  `blocked`; `ready`, `in_progress`, `complete` and a plan claiming `APPROVED` cannot be
  accepted without trusted approval evidence. Phase 3 has no approval-record input.
- The Phase 3 validator reports failures as `VALIDATION_FAILED` before the Phase 4 retry loop.
  The app shows schema validity separately from deterministic validity, structured
  graph details, errors and limitations. After Phase 4 exhaustion, failed proposals become `REQUIRES_HUMAN_REVIEW`;
  passing proposals become `AWAITING_HUMAN_APPROVAL` when gated, otherwise
  `REQUIRES_HUMAN_REVIEW`. The planner and validator never approve a proposal; Phase 5 records an explicit human review decision. Markdown and plan JSON retain
  that status; a separate validation JSON download exposes all findings.

The validator does not prove real-world safety, interpret arbitrary natural-language
constraints, resolve scheduling/capacity conflicts, verify gate timing or identify all
missing critical facts. Unresolved questions are surfaced for human review. There are
no task times, resource capacities or structured constraint predicates in the current
contract, so these limits are explicit rather than inferred from prose.

### Run and verify

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

The focused tests cover valid and invalid graphs, resource labels, completion criteria,
constraint representation, approval policy, status handling and Streamlit pass/fail/error
behavior. Model calls in app tests are mocked; they require no token or network access.
This is Phase 3 regression coverage, not the full Phase 7 evaluation package.

## Phase 4 — Bounded Replanning

`planning_engine.run_planning` now wraps the existing planner and validator. After
an invalid proposal it sends the original request, latest proposal and structured
validation feedback to the planner. It permits at most **two replan attempts**
(three planner calls total), validates every returned proposal and stops on success.
Passing plans still await human approval or review; no run authorizes execution.

**Business value:** Correct mechanically detectable omissions automatically while
keeping a clear limit on model usage and preserving human review for unresolved failures.
**Engineering behavior:** Retry control is deterministic and independent of the LLM
and Streamlit. Previous proposals and feedback are serialized as untrusted JSON data;
the existing humanitarian rules, schema check and mission identity check still apply.

If both revisions fail validation, the final invalid proposal is labeled
`REQUIRES_HUMAN_REVIEW`. If a revision fails schema/identity checks or the provider
fails, the loop stops early and retains the last invalid proposal with the same
review status and a visible explanation. Initial generation errors still fail closed
without retries. Provider error details are not shown or saved in the outcome.
The limit bounds planner calls; it is not a wall-clock or provider-internal retry budget.

Streamlit shows the number of revisions, each schema-valid revision's validation
result, and any stop reason. The displayed proposal's schema status is separate from
its deterministic validity. Markdown exports include the count and stop reason.
The outcome now carries the Phase 6 audit record; malformed
responses and service failures have no structured plan to include in revision history.

The tests include no-retry success, repair on either revision, exhausted retries,
latest-feedback propagation, schema/identity rejection and safe service-error handling.
Model calls are mocked; no live model quality evaluation or Space deployment is included.

## Phase 5 — Human Approval State Machine

The app now offers approve, reject and request-revision controls for the displayed
proposal and its saved mission request. Approval requires review acknowledgement and
passing deterministic validation; `approval.decide_proposal` independently revalidates
before approval. Rejection is available for invalid proposals. Revision requires notes
and moves the plan to the additive `REVISION_REQUESTED` status.

**Business value:** Make the human disposition explicit instead of leaving review as
prose. **Engineering behavior:** A separate transition function accepts decisions only
from reviewable states and checks a fingerprint of the saved request and proposal.
Final decisions cannot be overwritten; a new generation clears the decision and review
acknowledgement. Task states stay unchanged. Approval is advisory review, never an
execution command or replacement for operational authorization.

Requesting revision does not call the LLM automatically: the user edits mission inputs
using their notes and generates a fresh proposal under the same two-retry budget.
Editing input fields alone does not change the saved proposal being reviewed.

Decision, notes, timestamp and proposal fingerprint are retained in Streamlit session
state and downloadable as review JSON. Markdown includes the human disposition, and
plan JSON includes the resulting status. These are prototype session decisions, not
identity-authenticated approvals. The fingerprint detects changed content; it does not
prove identity or prevent a trusted caller from fabricating a decision. Session loss
loses the record unless downloaded. Phase 6 adds a complete run export; server-side persistence is not enabled.

Tests cover all decisions, invalid approval, stale request/plan detection, terminal
states, required revision notes, UI acknowledgement, invalid-proposal rejection and
revision, and decision reset on a new generation. The full suite uses mocked model calls.

## Phase 6 — Audit Layer

Every run now has a `PlanningRunRecord` with a unique run ID, saved mission request,
initial plan, ordered validation results, schema-valid revisions, all model-call outcomes,
reviewable proposal, final plan/status and timestamps. Human review updates a new snapshot
with decision, notes, proposal fingerprint and review time, preserving the proposal
actually reviewed and all earlier plans.

**Business value:** One download answers what was requested, what failed, what changed,
and what the human decided. **Engineering behavior:** The engine captures snapshots at
planning boundaries; `audit.py` validates review linkage and exports typed JSON that can
be reloaded through `PlanningRunRecord.model_validate_json`.

Call zero is initial generation; calls one and two are bounded revisions. Failed calls
record fixed error codes and timestamps, never raw provider errors or response bodies.
An initial generation failure produces a downloadable record with no final plan and a
human-review status. An invalid mission-input form does not create a planning run.
Credentials are not passed to the audit layer. User-entered mission and review text is
included as provided; this is not a general-purpose redaction service.

Use **Download Complete Audit JSON** to save the record before starting another run or
ending the session. Storage is session-local plus user-downloaded JSON, not automatic
server-side persistence. Authenticated identities, tamper-evident storage, retention
policies and a database remain production extensions. The full Phase 7 evaluation
package remains pending; the focused regression suite now contains 30 passing tests.
No live-model evaluation or Hugging Face deployment has been performed.
