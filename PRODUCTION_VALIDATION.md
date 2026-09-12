# Live Production Validation

Date: 2026-09-12

This note records a deliberate manual end-to-end validation of Agent 02 in its deployed Hugging Face Space after the inference and request-contract upgrades.

## Environment

- Deployment: Hugging Face Space published from the GitHub `main` branch
- Runtime path: Hugging Face Inference Providers through the OpenAI-compatible router
- Configured model: `Qwen/Qwen3.8-27B:ovhcloud`
- Planning depth used: Standard
- Scenario: the application's default synthetic missing-hiker search-and-rescue mission

## Observed result

The deployed application completed live structured inference successfully. The provider returned a complete response, the response parsed into the `MissionPlan` Pydantic schema, request-owned constraints and approval rules were attached by application code, and the deterministic planning workflow completed without the earlier contract-copy failures.

This manual check confirms that the deployed runtime can exercise the intended production path:

```text
MissionRequest
→ live model proposal
→ native JSON-schema response
→ Pydantic validation
→ application-owned request policy attachment
→ plan graph + deterministic validation
→ bounded planning workflow
→ human-review stage
```

The validation was performed through the deployed user interface rather than only through mocked tests or offline fixtures.

## What this establishes

This result provides evidence that, for the tested default Standard scenario and runtime configuration:

- Hugging Face authentication and provider routing worked;
- the configured model returned a complete bounded structured response;
- provider-native JSON schema guidance and application Pydantic validation were compatible;
- request-owned policy metadata avoided false validation failures caused by model paraphrasing;
- the deployed application reached the human-review portion of the workflow instead of failing at inference transport, truncation, or deterministic contract representation.

## What this does not establish

A successful manual production check is not a broad model-quality benchmark and does not establish operational search-and-rescue safety. It does not prove:

- reliability across arbitrary missions or repeated runs;
- semantic correctness of free-text constraints;
- resistance to every prompt-injection attempt;
- real-world resource feasibility, scheduling, navigation, aviation compliance, or responder safety;
- measured business outcomes such as time savings, cost savings, or incident-performance improvement.

Qualified human review remains required. The application remains an educational advisory prototype with no connected actuators.

## Engineering lesson

The production debugging sequence reinforced the portfolio pattern:

> **LLMs reason. Code preserves contracts. Validators enforce invariants. Humans authorize.**

The final architecture does not depend on the model to reproduce policy strings exactly. The model proposes the plan; application code preserves authoritative request metadata; deterministic validation checks the machine-readable contract; bounded replanning handles repairable failures; and human review remains the authorization boundary.

## Next evidence layer

The next evaluation step is a small controlled live-model benchmark measuring repeated-run behavior, including schema success, first-pass deterministic validation, bounded replan success, resource hallucination, unresolved-question behavior, latency, and human usefulness scoring. Live benchmarking should remain separate from normal CI so routine commits do not incur provider cost or become dependent on external service availability.
