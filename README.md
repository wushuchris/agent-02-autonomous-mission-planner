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
an LLM or Streamlit. The current pipeline is:

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
- The app shows schema validity separately from deterministic validity, structured
  graph details, errors and limitations. Failed proposals become `VALIDATION_FAILED`;
  passing proposals become `AWAITING_HUMAN_APPROVAL` when gated, otherwise
  `REQUIRES_HUMAN_REVIEW`. No proposal becomes approved. Markdown and plan JSON retain
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

### Next: Phase 4 — Bounded Replanning

Feed structured validation errors back to the planner, allow at most **two replan
attempts**, validate each revised proposal, stop on success and escalate exhausted
attempts to `REQUIRES_HUMAN_REVIEW`. `replan_required` currently records the need for
correction; it does not trigger any retry. Human approve/reject/revise controls remain
Phase 5, and complete audit records remain Phase 6.

The humanitarian safety boundary and existing structured planner are preserved.
This repository upgrade does not redeploy the Hugging Face Space.
