---
name: eng-coordinate
description: Coordinate changes across repositories or independently owned work packages, including contracts, dependency order, integration, and delivery sequencing.
---

Inspect workspace registry, actual repository identities, local changes, revisions, design authority, and delivery state. Never initialize a parent folder merely because it contains repositories. Pin starting revisions in the task record.

Map producer/consumer contracts and dependencies, compatibility windows, and tested revision combinations. Split by independent ownership. When permitted and useful, use at most three concurrent children and no recursive delegation; fewer if the runtime restricts it. Assign isolated checkouts/worktrees where needed and prevent overlapping writes.

Brief each worker with objective, base revision, instructions/design references, allowed files/actions, dependencies, acceptance checks, output format, and time/tool budget. The lead owns integration and reconciles assumptions.

For well-defined verification, prefer the configured fast verifier or UI validator when it has the required tools. Supply the tested snapshot, environment/startup procedure, steps, expected results, artifact location, and permitted test data/actions. Schedule execution against a stable implementation and isolate concurrent test data; avoid racing source edits or shared service resets. Workers report findings to the lead and do not fix application files. The lead owns coverage and diagnosis, routes repairs to the implementer, and requests failed checks and affected regressions again after repair. Escalate ambiguous or high-risk assessment to the main agent; missing worker tools require reassignment or direct execution, not inferred success.

Verify each affected repository and an explicit integration matrix. Keep implemented, verified, merged, deployed, and production-observed states distinct. Prepare delivery/rollback order; execute external actions only within authorization. Checkpoint contracts, owners, revisions, and pending edges using `{{SETUP_ROOT}}/README.md`.
