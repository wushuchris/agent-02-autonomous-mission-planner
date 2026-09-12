# Phase 7 evaluation

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python -m evaluation.run --output evaluation/scorecard.json
```

The CLI exits nonzero when any expected outcome differs. A rejected invalid proposal
counts as a passing evaluation case. The committed scorecard is a reproducible snapshot,
not a live-model benchmark. CI runs both commands and uploads a fresh scorecard.

## Current evidence

| Package | Expected outcomes met |
| --- | --- |
| Success proposals | 10 / 10 |
| Edge proposals | 5 / 5 |
| Failure proposals | 7 / 7 |
| Adversarial proposals | 3 / 3 |
| Regression tests, including workflow, UI and model-adapter behavior | 40 / 40 |

These are synthetic inputs and proposed plans exercising distinct structures/policies,
not sampled model generations. Scenario fixtures are in `cases.py`; `run.py` reports
schema status, deterministic validity, errors, warnings and expectation agreement per
case. A regression test intentionally substitutes an always-valid validator to verify
that the scorecard detects incorrect behavior.

## Design dimension coverage

| Dimension | Evidence and practical limit |
| --- | --- |
| Schema validity | Missing next action; planner regression tests reject malformed JSON and changed mission IDs. |
| Task completeness | Blank completion criteria; only field completeness is assessed. |
| Dependencies | Chains, joins, parallel nodes, duplicate IDs, missing references and cycles. |
| Constraints | Exact normalized representation and wording mismatch; semantic adherence is not evaluated. |
| Resources | Membership, normalization and supplied resources; simultaneous capacity conflicts are not mechanically detectable. |
| Milestones | Presence fixture only; coverage and quality need a human rubric or richer contract. |
| Human approval | Missing gates, high risk, hostile execution status; transition tests cover acknowledgement, invalid approval, stale content and terminal decisions. |
| Unresolved information | Warning for explicit unresolved weather; detection of omitted facts is not measured. |
| Safe failure | Mocked schema/provider failures and invalid-plan escalation in workflow/UI tests. |
| Replanning | Mocked success on either revision, latest feedback propagation and two-revision exhaustion in `test_replanning.py`. |
| Audit completeness | JSON roundtrip, snapshots, failed calls, credentials/error exclusion and review linkage in `test_audit.py`. |
| Inference boundary | Runtime configuration, HTTPS enforcement, empty-response failure, sanitized service messages and provider-neutral client injection in `test_model_adapter.py`. |

The workflow/UI/model-adapter dimensions are asserted by unittest, not counted as
additional proposal fixtures in the JSON scorecard. See test output for their individual results.

## Adversarial scope

Fixtures place hostile instructions in mission text or approval-gate text and supply
proposals that claim approval, invent resources or claim execution without approval.
Deterministic rules still reject them. Prompt tests verify that safety instructions and
untrusted-data framing remain present; they do not measure model obedience.

No network, model token or live inference is needed. These results do not prove search
and rescue feasibility, operational safety, factual accuracy, semantic constraint
compliance or live-model prompt-injection resistance. A future live evaluation should
sample model outputs and use qualified human scoring for these unmeasured dimensions.
