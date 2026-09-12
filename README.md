# Planning Agent — Search and Rescue Mission Planner

Agent 02 in **30 Agents for AI Engineers**. A reusable planning primitive demonstrated
through humanitarian search and rescue: turn objectives, resources and constraints into
structured proposals, check them, revise within limits, and record human review.

> **The LLM proposes. Rules validate. The agent replans. Humans approve.**

This is an educational advisory prototype. It does not replace trained responders,
incident commanders, emergency services or legal authority. Approval in this app records
review of a proposal; it does not authorize real-world execution. No drones, vehicles or
other actuators are connected. Weaponization, targeting, attack planning, evasion and
harmful engagement are outside its scope.

## Business case

Complex plans often omit dependencies, resources, constraints or decision points.
This project demonstrates how structured proposals and repeatable checks can expose
those omissions before human review. A complete JSON record makes the request, revisions,
validation findings and human disposition inspectable. No measured time or cost savings
are claimed; the evidence here is engineering behavior on synthetic cases.

## Engineering case and reusable pattern

```text
MissionRequest → LLM proposal → MissionPlan schema check
→ dependency graph + deterministic validation
    FAIL → latest proposal + feedback → at most 2 revisions
    PASS → human review
→ approve / reject / request revision → PlanningRunRecord JSON
```

The engine is independent of Streamlit. It can support future orchestration, logistics,
incident-response and multi-agent decomposition work, while this interface remains a
search-and-rescue demonstration.

| Module | Responsibility |
| --- | --- |
| `models.py` | Request, plan, validation, state and audit contracts |
| `planner.py` | Qwen structured generation, schema/mission identity checks and Markdown rendering |
| `plan_graph.py` | Unique IDs, existing dependencies, cycles and topological order |
| `validator.py` | Deterministic resource, completion, approval, constraint-representation and next-action checks |
| `planning_engine.py` | Up to two revisions after the initial proposal; stop on success or escalate |
| `approval.py` | Human decisions with revalidation and changed-proposal detection |
| `audit.py` | Review-linked snapshots and complete JSON export |
| `app.py` | Mission input, proposal review, human decision and downloads |
| `evaluation/` | Synthetic scenarios, expectations and JSON scorecard |

## Run locally

Use Python 3.11 (the CI version):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Set `HF_TOKEN` in your environment, a local `.env` file, or Streamlit secrets.
Do not commit credentials; `.env` and `.streamlit/secrets.toml` are ignored.
The default model is `Qwen/Qwen2.5-7B-Instruct` through Hugging Face InferenceClient.
Provider access is required for generation. Tests and offline evaluation require no token.

## Walkthrough

1. Describe the mission, resources, constraints, approval rules and success criteria.
2. Generate a proposal. The engine validates it and permits at most two revisions.
3. Review the saved mission inputs, proposal, schema status, deterministic findings,
   revision count and unresolved questions. Detailed JSON and graph data are expandable.
4. Approve only after acknowledgement and passing validation, reject, or request revision
   with notes. Revision requests require editing inputs and generating a new proposal.
5. Download the plan and complete audit JSON before starting another run or ending the session.

Editing form fields alone does not modify the saved proposal being reviewed. New generation
clears the prior decision and acknowledgement. Terminal decisions cannot be overwritten.
Review controls appear after the proposal and findings so the decision follows the evidence.

## Exact checks and limits

- Resource assignments match whole `available_resources` labels after case/whitespace
  normalization. Quantity labels are not split into inferred units; sensors are context
  unless also listed as assignable resources. Capacity and timing are not modeled.
- Constraints must appear in `covered_constraints`, with whole-entry normalized matching.
  This proves representation, **not semantic compliance**. Unknown entries are rejected.
- Each approval rule must appear in `approval_gates`. Since rules are free text, any request
  approval rule conservatively gates every task. High/critical risk also requires approval.
  Sensitive tasks must remain planned or blocked; prose cannot establish actual approval.
- Task IDs must be unique, references must exist, and valid graphs must be acyclic.
  Duplicate IDs or missing references defer sorting/cycle analysis until repaired.
  A topological order is not a schedule or permission to execute.
- Completion criteria must be nonblank and a next action must exist. These checks do not
  establish completeness or quality of a real mission plan.

Missing facts, milestone coverage, scheduling conflicts, gate timing and arbitrary prose
meaning still require qualified review. Human reviewers are not authenticated in this
prototype; fingerprints detect content changes, not identity or caller authorization.

## Failure and review behavior

Initial malformed output or service failure stops without retrying. A schema-valid but
invalid proposal receives up to two revisions (three planner calls total). Each revision
uses the original request, latest proposal and structured feedback. Exhaustion escalates
to `REQUIRES_HUMAN_REVIEW`; malformed revisions or service failures stop early and retain
the last invalid proposal for review. The call budget is not a wall-clock or provider-internal
retry limit. Invalid proposals cannot be approved through the review function.

Passing proposals await human approval or review. Human decisions set `APPROVED`, `REJECTED`
or `REVISION_REQUESTED`; task execution states remain unchanged. Human-requested revision
starts no hidden model call. Safety framing is preserved in prompts, but live-model
obedience and prompt-injection resistance have not been evaluated.

## Audit and storage

Each record includes a run ID, saved request, initial plan, validation history, revisions,
all model-call outcomes and timestamps, pre-decision proposal, final plan/status and human
decision details. Even initial generation failures produce downloadable records. Invalid
input forms do not create planning runs. Prior proposals are deep snapshots.

Credentials and raw provider error/response bodies are excluded. Mission text and review
notes are included as entered; the exporter is not a general redaction service. Storage
is session-local plus user-downloaded JSON. There is no automatic server database,
identity authentication, tamper-evident storage or retention policy.

## Evaluation evidence

```bash
python -m unittest discover -s tests -v
python -m evaluation.run --output evaluation/scorecard.json
```

**25/25 expected scenario outcomes:** 10 success, 5 edge, 7 failure and 3 adversarial.
**32 regression tests** cover planning, review, audit and Streamlit behavior. CI runs both
commands and uploads a scorecard. Invalid proposals are expected to be rejected.

See [coverage and limitations](evaluation/README.md) and the [JSON scorecard](evaluation/scorecard.json).
These are synthetic deterministic checks and mocked model workflows, not live-model quality,
operational safety or measured business outcomes. The adversarial fixtures test rule enforcement
against hostile proposals, not model resistance to hostile instructions.

## Upgrade and deployment status

The repository implements Phases 1–9 of [DESIGN.md](DESIGN.md): typed contracts, structured
planning, graph validation, bounded revisions, human decisions, audit export, offline
evaluation, UI organization and this consolidated portfolio documentation. Historical phase
notes in the design describe the incremental implementation; this README describes current behavior.

The Hugging Face Space has **not** been redeployed during this upgrade. A future deployment
must include every root Python module and `requirements.txt`, followed by a smoke test with
the configured provider. GitHub CI is verification only; it does not deploy the Space.

Production extensions include authenticated review, durable protected audit storage,
structured constraints and scheduling, live-model evaluation with qualified reviewers,
provider timeouts/retry policies, dependency pinning and deployment validation.
