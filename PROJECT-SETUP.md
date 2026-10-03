# Set up a project with your agent

In a project chat, say:

> Set up this repository for Codex and Claude Code. Inspect what is already here, ask me only about missing goals or constraints, and create the smallest useful project setup.

Or name the directory in that request. Codex can explicitly invoke `$eng-project-setup`; Claude Code uses `/eng-project-setup`. To configure several repositories, use `eng-workspace-setup` and identify their common workspace. To update later, say:

> Update this project's agent setup for the current code and CI. Preserve our existing instructions and decisions, and explain any questions you need me to resolve.

The agent handles discovery, the specification, and the commands. You supply intent and consequential decisions that the repository does not establish. You do not need to write a configuration file yourself. Configured protected roots remain excluded unless you explicitly change those boundaries.

## How the collaboration works

1. **Inspect.** Read existing instructions, relevant documentation, code layout, CI/scripts, and local changes. Identify the authoritative sources for requirements, architecture, decisions, and delivery evidence. Inspection does not run project scripts.
2. **Resolve missing intent.** Summarize the findings. Ask only about material gaps or conflicts, such as which of two specifications is authoritative. Record unanswered questions explicitly and continue independent setup work. Do not invent business rules, owners, verification results, or deployment targets.
3. **Prepare and apply.** Show the proposed files and choices. A request to set up the project authorizes reversible instruction changes. A request only to review or propose a plan does not authorize applying it. Preserve existing instructions, personal overrides, and work in progress.
4. **Verify.** Validate references/imports and run the narrow appropriate project checks within authorization. Mark commands `observed` until actually executed. Report missing infrastructure or decisions without claiming completion of unverified behavior.

## Files and scope

The default is `AGENTS.md` plus an `@AGENTS.md` import in `CLAUDE.md`. They use repository-relative references, require no personal runtime to understand, and contain project purpose, areas/owners, local conventions, invariants, commands, and questions only as relevant. Existing documents remain authoritative. Preserve manual text outside the generated markers.

Set `registry: true` only when a tool or a larger project benefits from `.agent/project.json`. In that mode the registry is the single navigation/command index; AGENTS points to it rather than duplicating it. Set `create_vault: true` only when reusable observations need a new index and none already exists. Both default to false. Reuse existing design/delivery/knowledge documents. Do not create a directory tree of empty placeholders.

Workspace mode deliberately writes `WORKSPACE.json` with repositories, roles, owners, revisions, contracts, and delivery order. The workspace instructions route to individual repositories; they do not repeat every repository's rules. External repositories need separately established scope. Do not initialize a parent Git repository or configure children merely because they were discovered.

Global preferences, generic skills, roles, model profiles, and runtime stay global. Add project-specific skills, roles, native settings, or hooks only for a demonstrated need and within authorization. Do not put personal absolute paths, credentials, machine trust, or subscription details into shared project files. Commit shared instructions through the project's normal delivery workflow; setup alone does not authorize a push or deployment.

## Agent command reference

The installed skill supplies the resolved Python and runtime paths. Source templates contain `{{SETUP_ROOT}}` and `{{PYTHON}}`; `config build` resolves them at installation. The following commands are arguments to `engctl.py`, not a request for the user to operate the CLI:

```text
project inspect ROOT
project draft ROOT --spec SPEC.json
config diff DRAFT.json
project apply DRAFT.json
project validate ROOT --spec SPEC.json
```

Prepare SPEC in the task's local output area. It is intake data; a minimal project need not commit it. Use `templates/project-spec.example.json` or `templates/workspace-spec.example.json` as a schema example, replacing all placeholders with inspected facts. Required fields are `kind` (`project` or `workspace`), `name`, `summary`, `sources`, and `commands`. Empty lists are valid when the corresponding information is unknown.

- `sources`: objects with `role` (`instructions`, `design`, `decisions`, `delivery`, `verification`, `vault`), existing relative `path`, and optional `description`.
- `commands`: `name`, an `argv` string array, relative `cwd`, `status` (`observed` or `verified`), and an `evidence` reference. Setup documents these; it does not execute them automatically. Keep CI/scripts authoritative for the actual procedure.
- `domains`: optional objects with existing relative `path`, `responsibility`, and known `owner` (otherwise `unknown`).
- `invariants`, `conventions`, `open_questions`: optional lists of concise strings. Link detailed requirements to their existing authority and distinguish unresolved intent from facts.
- `registry`, `create_vault`: optional booleans, false for new single-repository setups unless deliberately chosen.
- Workspace inputs also include `repositories` with existing Git-directory `path`, observed `role`, and optional `owner`; `contracts` and `delivery_order` can document coordination. The draft records inspected revisions, not proof that the repositories work together.

## Updating safely

Reinspect the repository and reconcile the specification with current decisions and CI. Use `project draft ROOT --spec SPEC.json --update` for a bounded generated block. Review the diff and apply as above. Updates preserve text before/after that block and existing Claude instructions; they do not append another copy. Read existing managed registries before updating them so user-added fields remain intact. Disabling an existing registry requires explicit reconciliation, not silent abandonment of its authority.

Legacy setups without a closing marker deliberately stop automatic replacement. Inspect and back up the file, identify the exact setup-owned region, and make the smallest authorized edit to establish its boundary. Do not truncate text after the opening marker. An unmanaged registry is also preserved pending reconciliation.

Drafts and exact project-file backups live under the shared runtime's local `state/` directory. Apply refuses concurrent drift. For recovery, compare the backup against current files and restore only unchanged setup edits; preserve subsequent work. The runtime is a convenience for the local agent, not a required dependency for teammates reading the generated project guidance.

## Maintain as the project changes

Update commands when CI/scripts change and boundaries when architecture or requirements change. Store verified, reusable observations with source/revision and revalidation triggers. Keep detailed workflow instructions in skills loaded on demand. A small task should still proceed directly; substantial work can use the shared task/evidence runtime. Evaluate model choices separately from instruction changes and do not infer equivalent production quality from the small synthetic model benchmark.
