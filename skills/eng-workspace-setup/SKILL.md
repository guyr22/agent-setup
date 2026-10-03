---
name: eng-workspace-setup
description: Set up multi-repository workspace navigation and coordination with ownership, design authority, contracts, revision-aware checks, and per-project instruction boundaries.
---

Read `{{SETUP_ROOT}}/PROJECT-SETUP.md` and `{{SETUP_ROOT}}/templates/workspace-spec.example.json`. Runtime is `{{PYTHON}} {{SETUP_ROOT}}/engctl.py`. Never modify KeepHQ.

Inspect the root and immediate repositories with `project inspect`; locate deeper/external repositories from references rather than unbounded scans. Read workspace instructions, design/delivery repositories, source indexes, contracts, and status. Do not initialize a parent Git repository, add submodules, create remotes, or move repositories.

Build a registry of paths, observed roles, known owners, revisions, contracts/dependency edges, command working directories, and integration checks. Mark unknowns. Reuse existing design repositories and sources of truth. Propose a shared location only where one is needed.

Fill the workspace specification with existing relative paths. The scaffolder rejects references outside the root; handle external repositories separately after scope is established. Run `project draft ROOT --spec SPEC` (add `--update` only for an existing bounded setup), inspect with `config diff DRAFT`, reconcile conflicts, and `project apply DRAFT` under the setup authorization.

Top-level AGENTS.md is a routing map, not all repository instructions combined. Configure per-repository instructions only when requested, using eng-project-setup if available. Add area instructions only for materially different conventions. Link design intent, decisions, implementation, executed evidence, and current knowledge separately.

Validate paths, repository identities, producer/consumer direction, revision combinations, and a representative cross-repository task. Identify integration ownership and delivery order. Worker concurrency is an upper bound. Never execute repository scripts at session start. Report navigation, verified checks, and unresolved authority/infrastructure questions.

Run `project validate ROOT --spec SPEC` after application. Ask only about missing ownership, authority, or integration decisions; do not require the user to fill out the registry. Workspace registries are intentional structured routing; single repositories default to two instruction files.
