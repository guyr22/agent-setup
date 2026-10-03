---
name: eng-project-setup
description: Collaboratively create or update a repository's Codex and Claude setup from its code, documentation, and the user's goals; use when asked to onboard or configure a specific project.
---

Read `{{SETUP_ROOT}}/PROJECT-SETUP.md` for the intake, schema, commands, and update rules. Runtime: `{{PYTHON}} {{SETUP_ROOT}}/engctl.py`. Respect the configured protected roots.

Inspect the requested repository before interviewing the user: existing AGENTS.md/CLAUDE.md, local changes, README, CI/scripts, architecture, requirements, decisions, and knowledge indexes. Read relevant area guidance. Inspection does not execute project scripts or install dependencies. If no root can be inferred, ask for the project path before touching a repository.

Explain what you learned and ask only for missing decisions that materially change the setup: intended outcome, non-negotiable constraints, or conflicting sources of authority. Do not make the user fill out JSON or repeat facts discoverable locally. Continue independent work while answers are pending. A request for a plan or review alone does not authorize application.

Prepare the specification yourself with observed or user-confirmed facts and clearly labeled open questions. Default to AGENTS.md plus a CLAUDE.md import. Reuse existing design and delivery documents; registry and a new VAULT are opt-in only when they solve an actual need. Keep project instructions portable, concise, and useful without this personal runtime. Put detailed intent in its authoritative document and link it.

Show the proposed files and the consequential choices. For a setup request, reversible project instructions are already authorized; do not add a redundant approval gate. Draft, inspect the diff, then apply. Use --update only for an existing bounded managed block. Preserve surrounding instructions and existing Claude text. If legacy markers or an unmanaged registry make ownership ambiguous, reconcile the exact region before replacing it; never guess where user text ends.

Validate references and native imports, run appropriate already-authorized project checks, and distinguish documented commands from executed results. Do not widen permissions, configure deployment, install plugins, or duplicate global skills as a side effect. Give the user the resulting entry points, checks, unresolved decisions, and an example request for future updates. Scope any ongoing work to the project they named.
