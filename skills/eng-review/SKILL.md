---
name: eng-review
description: Review a concrete code change against requirements and surrounding behavior, returning actionable correctness findings with evidence and severity.
---

Establish scope, base revision, requirements, and conventions. Inspect the diff and necessary callers/contracts/tests. Prioritize regressions, correctness, omitted criteria, and compatibility.

Each finding needs a reachable failure scenario, impact, evidence, and precise location. Mark uncertainty and how to resolve it. Do not manufacture quotas, repeat resolved findings, or substitute speculative hardening for a bug. Style matters when an applicable convention or concrete maintenance issue supports it.

Use security review for a relevant changed trust boundary. Independent review helps consequential changes; routine tiny fixes need not spawn a reviewer. Respect read-only scope unless edits are authorized. State actual checks and coverage gaps. If no actionable findings are supported, say so without asserting zero risk.
