---
name: eng-verify
description: Run acceptance-driven verification and track command outcomes, relevant working state, and unresolved coverage for a change.
---

Read repository instructions and CI. Map acceptance criteria to meaningful unit, integration, type/build, browser, manual, or deployment checks. Do not invent commands or treat documented commands as executed.

Use the project's verification procedure to start required services, confirm readiness, and prepare an isolated test session and data. Verify the current implementation through its actual browser, API, CLI, or worker entry points. When a change affects UI workflows, including through backend behavior, open the browser and exercise affected user journeys and relevant backend effects. Run the project's critical smoke suite plus regression checks selected from the change's impact; broaden coverage for shared components or contracts. A successful build or screenshot alone does not establish working behavior.

When delegation is permitted and useful, prefer the configured fast verifier for repeatable commands and explicit smoke or browser steps. The lead specifies steps/assertions, environment, snapshot, allowed actions, output area, and budget, then inspects the returned evidence. Keep coverage design, ambiguous failures, exploratory assessment, and high-risk judgment with the main agent. Report missing tools to the lead for execution or reassignment; never substitute inferred results. Direct execution is appropriate when delegation costs more than the check.

Record each check's expected and observed outcome, tested snapshot and environment, commands or interaction steps, and relevant artifact references. Distinguish implementation failures from missing infrastructure, flaky behavior, and unrelated baseline failures using evidence. Reproduce and diagnose failures; the implementing agent fixes defects introduced by the work, then reruns failed checks and affected regression checks against the repaired version. A verification-only worker returns findings to the lead without editing application source. Do not weaken checks, discard failed attempts, or retry unchanged failures until one passes. Repeated failure requires a new hypothesis; unrelated defects remain separately reported unless authorized for repair.

Resolve routine environment issues within task authorization and continue other useful checks when one is blocked. If execution requires unavailable access, an external change, or a user decision, report the exact blocker and unverified behavior. Use isolated test data and authorized environments; testing does not authorize production writes or external side effects. Clean up only services and data created for this task, preserving existing sessions.

For substantial Git tasks use `engctl verify` from `{{SETUP_ROOT}}/README.md`, with stable labels and explicit arguments. Receipts cover tracked and nonignored untracked content. Ignored dependencies and external services remain outside that fingerprint; record relevant conditions in the checkpoint. Inspect checks that mutate captured files before rerunning.

At delivery use `task evidence` to check currency. Missing, stale, failed, or incomplete checks remain limitations. Command success does not prove acceptance coverage. Focused low-impact work can report direct evidence without registering a task.
