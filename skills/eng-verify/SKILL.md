---
name: eng-verify
description: Run acceptance-driven verification and track command outcomes, relevant working state, and unresolved coverage for a change.
---

Read repository instructions and CI. Map acceptance criteria to meaningful unit, integration, type/build, browser, manual, or deployment checks. Do not invent commands or treat documented commands as executed.

Distinguish implementation failures from missing infrastructure, flaky behavior, and unrelated baseline failures using evidence. Do not weaken checks to make them pass. Repeat only after relevant changes or new evidence.

For substantial Git tasks use `engctl verify` from `C:/Users/guyr2/.codex/agent-setup/README.md`, with stable labels and explicit arguments. Receipts cover tracked and nonignored untracked content. Ignored dependencies and external services remain outside that fingerprint; record relevant conditions in the checkpoint. Inspect checks that mutate captured files before rerunning.

At delivery use `task evidence` to check currency. Missing, stale, failed, or incomplete checks remain limitations. Command success does not prove acceptance coverage. Focused low-impact work can report direct evidence without registering a task.
