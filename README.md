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
→ attach trusted request policy metadata
→ dependency graph + deterministic validation
    FAIL → latest proposal + feedback → at most 2 revisions
    PASS → human review
→ approve / reject / request revision → PlanningRunRecord JSON
```

The model is responsible for planning judgment; application code owns exact request-policy
strings and validation invariants. This avoids spending model capacity on clerical copying
and prevents harmless paraphrases from weakening an exact policy contract.

The engine is independent of Streamlit. It can support future orchestration, logistics,
incident-response and multi-agent decomposition work, while this interface remains a
search-and-rescue demonstration.

| Module | Responsibility |
| --- | --- |
| `models.py` | Request, plan, validation, state and audit contracts |
| `model_adapter.py` | Provider-neutral JSON chat contract plus OpenAI-compatible Hugging Face runtime adapter |
| `planner.py` | Structured plan prompting, schema/mission identity checks, trusted request-policy attachment and Markdown rendering |
| `plan_graph.py` | Unique IDs, existing dependencies, cycles and topological order |
| `validator.py` | Deterministic resource, completion, approval, constraint-representation and next-action checks |
| `planning_engine.py` | Up to two revisions after the initial proposal; stop on success or escalate |
| `approval.py` | Human decisions with revalidation and changed-proposal detection |
| `audit.py` | Review-linked snapshots, configured model identity and complete JSON export |
| `app.py` | Mission input, proposal review, human decision and downloads |
| `evaluation/` | Synthetic scenarios, expectations and JSON scorecard |

## Inference runtime

Live generation follows the same portfolio convention as the newer agents: the planning
layer depends on a small provider-neutral `JsonChatModel` interface, while the production
adapter calls **Hugging Face Inference Providers through its OpenAI-compatible API**.
Provider credentials and model selection are runtime configuration rather than planning logic.

Runtime configuration:

```text
HF_TOKEN=<secret>
MODEL_ID=Qwen/Qwen3.8-27B:ovhcloud
HF_BASE_URL=https://router.huggingface.co/v1
```

`HF_BASE_URL` defaults to the Hugging Face router when omitted. `HF_TOKEN` and `MODEL_ID`
are required for live inference. The adapter uses a bounded request timeout and converts
known authentication, permission, billing, rate-limit and provider failures into fixed
public messages rather than exposing raw provider responses or credentials.

The model remains a **proposal layer**. Exact request constraints and request approval rules
are attached by application code after schema validation; deterministic graph and policy
validation, bounded retry count, approval state transitions and audit behavior also remain
application-owned.

## Run locally

Use Python 3.11 (the CI version):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Edit the local `.env` with your own `HF_TOKEN` and desired `MODEL_ID`. Do not commit
credentials; `.env` and `.streamlit/secrets.toml` are ignored. Provider access is required
for live generation. Tests and offline evaluation require no token or network model call.

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
- Request constraints are copied by application code into `covered_constraints` after the
  model response passes schema validation. The validator then checks exact whole-entry
  representation. This proves representation, **not semantic compliance**; free-text
  compliance still requires human review.
- Request approval rules are copied by application code into `approval_gates` rather than
  relying on model paraphrases. Since rules are free text, any request approval rule
  conservatively gates every task. If no request approval rules exist, model-proposed gates
  are retained for risk-driven approval needs. High/critical risk also requires approval.
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

Initial malformed output, configuration failure or service failure stops without silently
accepting a plan. A schema-valid but invalid proposal receives up to two revisions (three
planner calls total). Each revision uses the original request, latest proposal and structured
feedback. Exhaustion escalates to `REQUIRES_HUMAN_REVIEW`; malformed revisions or service
failures stop early and retain the last invalid proposal for review. The call budget is not
a wall-clock or provider-internal retry limit. Invalid proposals cannot be approved through
the review function.

Passing proposals await human approval or review. Human decisions set `APPROVED`, `REJECTED`
or `REVISION_REQUESTED`; task execution states remain unchanged. Human-requested revision
starts no hidden model call. Safety framing is preserved in prompts, but live-model
obedience and prompt-injection resistance have not yet been benchmarked.

## Audit and storage

Each record includes a run ID, saved request, configured model identifier, initial plan,
validation history, revisions, all model-call outcomes and timestamps, pre-decision proposal,
final plan/status and human decision details. Even initial generation failures produce
downloadable records. Invalid input forms do not create planning runs. Prior proposals are
deep snapshots.

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
**43/43 regression tests** currently pass, covering planning, review, audit, Streamlit
behavior, provider-neutral inference configuration, injected-model behavior and trusted
request-policy attachment. CI runs both commands and uploads a scorecard. Invalid proposals
are expected to be rejected.

See [coverage and limitations](evaluation/README.md) and the [JSON scorecard](evaluation/scorecard.json).
These are synthetic deterministic checks and mocked model workflows, not live-model quality,
operational safety or measured business outcomes. The adversarial fixtures test rule enforcement
against hostile proposals, not model resistance to hostile instructions.

## Deployment

GitHub is the source of truth. The GitHub Actions workflow runs the regression suite and
offline evaluation first; successful pushes to `main` then publish the tested application
files to the existing Hugging Face Space. Pull requests do not deploy and do not receive
the deployment secret.

The Hugging Face runtime must provide:

- `HF_TOKEN` as a secret with Inference Providers access;
- `MODEL_ID` as a runtime variable;
- optional `HF_BASE_URL` (the adapter defaults to `https://router.huggingface.co/v1`).

The deployment preserves the Space Dockerfile, metadata, runtime secrets and unrelated
Space files.

## Deliberate live inference smoke test

Live inference is intentionally excluded from normal CI so commits do not spend provider
credits or depend on network availability. After a runtime/model change, run one explicit
end-to-end check:

```bash
python scripts/live_smoke_test.py
```

The repository also includes a manual GitHub Actions workflow named **Live inference smoke**.
From the Actions tab, run it deliberately and supply the model identifier. The workflow uses
the repository `HF_TOKEN` secret, calls the configured Hugging Face router, exercises one
synthetic mission through structured generation plus bounded validation/replanning, and
fails if the final proposal does not pass deterministic validation.

A passing smoke test demonstrates provider connectivity and contract compatibility. It does
**not** establish operational search-and-rescue safety or broad model quality.

## Upgrade status and next evidence

The repository implements the planned typed contracts, structured planning, graph validation,
bounded revisions, human decisions, audit export, offline evaluation, UI organization and
GitHub-to-Hugging-Face deployment. Inference is separated from planning through the reusable
model adapter described above.

The next evidence layer is a small **live-model benchmark** measuring schema success, first-pass
validation, replan success, resource hallucination, unresolved-question behavior and qualified
human usefulness scoring. Production extensions also include authenticated review, durable
protected audit storage, structured constraints and scheduling, provider retry policy,
fully locked dependency artifacts and deployment health monitoring.
