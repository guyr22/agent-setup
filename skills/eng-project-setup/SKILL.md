---
name: eng-project-setup
description: Create or adapt repository-specific agent instructions, knowledge navigation, verification commands, and improvement boundaries for a project.
---

Use for requested project setup, not every coding task. Read `C:/Users/guyr2/.codex/agent-setup/README.md` and `C:/Users/guyr2/.codex/agent-setup/templates/project-spec.example.json`. Runtime is `C:/Python313/python.exe C:/Users/guyr2/.codex/agent-setup/engctl.py`. KeepHQ is excluded from writes.

1. Run `project inspect ROOT`. Read existing AGENTS.md/CLAUDE.md, ancestor/area instructions, local changes, build manifests, CI, design/decisions, delivery records, and VAULT/index. Search scoped paths; inspection executes no repository scripts.
2. Establish actual stack, commands, domains, sensitive boundaries, intended behavior sources, and checks. Distinguish observed commands from executed checks. Do not install dependencies or run migrations just for discovery. Reconcile existing setups instead of creating a competing tree.
3. Fill the example specification with inspected facts. Reuse authoritative stores. Keep global policy global; project instructions need local commands/directories, ownership, invariants, and navigation. Add area instructions only where conventions differ materially, checking inheritance.
4. Run `project draft ROOT --spec SPEC`, inspect with `config diff DRAFT`, resolve conflicts/import duplication, then `project apply DRAFT`. Setup authorization covers these reversible files; ask only for material missing decisions. The tool preserves existing text, refuses concurrent drift, backs up originals, and never initializes Git/remotes.
5. Complete requested documentation in the established store, separating product intent, decision provenance/supersession, planned checks, and executed delivery evidence. VAULT is a compact index, not a transcript or duplicate spec. Unknown behavior must remain unknown.
6. Validate paths, command directories, native instruction discovery, relevant decision IDs/supersession, and representative focused/consequential task routing. Use read-only simulation unless coding changes were requested. Separate static validation from live agent evaluation.

Report files, authority map, checks, and unresolved decisions. Do not install project plugins, duplicate global skills, or change global behavior without need and authorization.
