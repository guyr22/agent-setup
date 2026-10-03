---
name: eng-coordinate
description: Coordinate changes across repositories or independently owned work packages, including contracts, dependency order, integration, and delivery sequencing.
---

Inspect workspace registry, actual repository identities, local changes, revisions, design authority, and delivery state. Never initialize a parent folder merely because it contains repositories. Pin starting revisions in the task record.

Map producer/consumer contracts and dependencies, compatibility windows, and tested revision combinations. Split by independent ownership. When permitted and useful, use at most three concurrent children and no recursive delegation; fewer if the runtime restricts it. Assign isolated checkouts/worktrees where needed and prevent overlapping writes.

Brief each worker with objective, base revision, instructions/design references, allowed files/actions, dependencies, acceptance checks, output format, and time/tool budget. The lead owns integration and reconciles assumptions.

Verify each affected repository and an explicit integration matrix. Keep implemented, verified, merged, deployed, and production-observed states distinct. Prepare delivery/rollback order; execute external actions only within authorization. Checkpoint contracts, owners, revisions, and pending edges using `{{SETUP_ROOT}}/README.md`.
