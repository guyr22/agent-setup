---
name: eng-deliver
description: Prepare a completed change for handoff, commit, pull request, or authorized release with current evidence and clear delivery status.
---

Reconcile the final diff with the request, local user changes, and acceptance criteria. Use `task evidence` for registered tasks. Resolve material findings or identify limitations.

Confirm that affected real workflows, required project checks, and critical smoke/regression checks were exercised on the final implementation. Include browser evidence for affected UI workflows, even when only backend code changed. Review worker evidence and ensure defects introduced by the work were repaired and failed checks plus affected regressions were rerun. Route unresolved repairable failures back to implementation; do not treat a worker's pass summary or passing unit tests as proof of end-to-end coverage. If blocked, distinguish implemented work from verified behavior and identify the exact remaining checks.

Update existing delivery records with implementation and executed evidence. Keep design intent, implementation, verification, merge, deployment, and production observation separate. Do not rewrite requirements to match what shipped.

Describe the concrete problem, resulting behavior, verification, and material limits. Cross-repository delivery needs order and compatibility details. Commit, open/attach PRs, merge, deploy, or message others only as authorized. Preparation alone does not authorize those actions.

Close registered work with `task finish` from `{{SETUP_ROOT}}/README.md`; provide an honest reason for incomplete evidence. Preserve verified project observations and propose workflow improvements without activating them.
