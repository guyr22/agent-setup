# Shared engineering setup

Maintained source for Guy's Codex and Claude Code configuration. Version 1.1.0.

This installation adds 14 skills, eight specialized roles, four Codex launch profiles, native hook definitions, and a standard-library Python runtime for project scaffolding, task evidence, project facts, and inactive improvement proposals. Existing managed plugins, auth, user preferences, and chats are preserved. No project has been configured by the installation. KeepHQ is protected from setup/runtime writes.

## Using the skills

Start a new chat/session after installation. Use ordinary requests for automatic selection, `$eng-project-setup` in Codex, or `/eng-project-setup` in Claude Code. For example:

> Use eng-project-setup to configure this repository. Reuse its existing design and delivery documentation.

> Use eng-workspace-setup to configure this multi-repository workspace, including its design repository and per-repository instructions.

The project skill inspects first, creates a reviewable draft, preserves existing instructions, and applies only within the requested project. It does not initialize parent repositories, install plugins, or invent verified commands. The workspace skill establishes repository routing, contract ownership, revision combinations, and integration responsibilities.

Focused fixes stay lightweight. Planned changes add criteria/checkpoints where useful. Program changes add explicit repository dependencies and integration evidence. Three children is the maximum, not a default team size. Native runtime limits may be stricter. Role tool restrictions are real where supported; verifier shell use remains governed by the native sandbox and task authorization.

## Native files and models

- Source: `C:/Users/guyr2/.codex/agent-setup`.
- Codex: `~/.codex/AGENTS.md`, `skills/eng-*`, `agents/eng-*.toml`, `hooks.json`, `eng-*.config.toml`.
- Claude: `~/.claude/CLAUDE.md`, `skills/eng-*`, `agents/eng-*.md`, hooks merged into `settings.json`.
- No third-party plugin installation or extra MCP server is required.

The user's selected main model stays unchanged. Optional Codex CLI profiles: `codex -p eng-fast`, `codex -p eng-balanced`, `codex -p eng-deep`, `codex -p eng-review`. Current mappings are in `profiles.json`; use the native model picker for desktop main chats. Claude equivalents are `claude --model haiku`, `--model sonnet`, and `--model opus`; review uses Sonnet with an independent review brief. Mapper roles use fast models, implementation uses balanced, and consequential architecture/security review uses deep. Verify availability before future model changes. These choices are a policy starting point, not a measured cost/quality claim.

Review native `/hooks` after installation or hook changes. **Codex skips untrusted hook definitions until you approve their exact definitions in `/hooks`.** This installer never edits trust state. Claude loads personal hook settings; inspect `/hooks` to verify they are loaded. Client restart/new sessions may be necessary. The local doctor reports file drift, not a claim that native hooks fired.

Hooks make no network/model calls, execute no project scripts, and do not parse transcripts. SessionStart supplies a short configuration/session pointer. PreToolUse checks explicit structured edit paths against KeepHQ and registered task write roots. PostToolUse stores event/tool/outcome metadata only. Compaction, interrupt, and session end record lifecycle metadata while existing checkpoints persist. Stop gives an advisory notice for an active task; it never loops or restarts work. Shell commands and unsupported tools are not covered by structured edit guards. Telemetry fails open; native sandbox/permissions remain authoritative.

## Runtime commands

Python 3.11+ is required. This host uses `C:/Python313/python.exe`. In PowerShell:

```powershell
$eng = 'C:/Users/guyr2/.codex/agent-setup/engctl.py'
python -B $eng doctor
python -B $eng project inspect 'C:/path/to/project'
python -B $eng project draft 'C:/path/to/project' --spec 'C:/path/to/inspected-spec.json'
python -B $eng config diff 'C:/path/to/generated-draft.json'
python -B $eng project apply 'C:/path/to/generated-draft.json'
```

Specification examples live in `templates/`. Replace their example content with inspected facts; they are not installed into projects automatically. Existing design/delivery/VAULT paths are reused. Existing instructions are preserved and extended; the acting agent must reconcile semantic contradictions before application. Backups are stored centrally. No source-writing operation is run by discovery.

For a substantial task, use the session ID supplied by SessionStart, or a unique explicit session key if hooks are inactive. Register task scope, then record checkpoints and checks:

```powershell
python -B $eng task start --session SESSION --root 'C:/repo' --objective 'Concrete outcome' --mode planned
python -B $eng task checkpoint --session SESSION --file 'C:/checkpoint.json'
python -B $eng verify --session SESSION --label unit --timeout 600 -- python -m unittest discover
python -B $eng task evidence --session SESSION
python -B $eng task finish --session SESSION
```

Checkpoint JSON requires `completed`, `next`, and `decisions`; add blockers, source references, revision/contract information, and environment facts as needed. Use repeated `--write-root` arguments for explicitly allowed worker/repository areas. Program tasks can record checks with `verify --root C:/workspace/repository` per repository. Scope roots for tool calls must account for the actual native tool working directory; a hook is a backstop, not the ownership plan itself.

Receipts fingerprint the exact Git root's tracked and nonignored untracked content, including uncommitted edits, deletions, and submodule contents. Ignored dependencies, remote services, and generated ignored files are outside this boundary. Record material conditions separately. A modifying check yields unstable evidence until inspected and rerun. Checks stream output to the terminal; the database stores command hashes, labels, outcomes, duration, and fingerprints, not raw arguments/output. Use a nonsecret descriptive label and keep exact command evidence in the project delivery record. For an incomplete/manual verification, `task finish --reason 'Honest limitation or manual evidence reference'` records the limitation; it does not convert it to passing evidence.

## Knowledge and improvement

```powershell
python -B $eng knowledge add 'C:/repo' --file 'C:/fact.json'
python -B $eng knowledge query 'C:/repo'
python -B $eng knowledge query 'C:/repo' --history
python -B $eng observations --root 'C:/repo'
python -B $eng propose 'C:/proposal.json'
```

A fact requires `id`, `claim`, `source` (relative project file), `kind` = `verified-observation`, and `verification` (how its meaning was checked). Optional `supersedes` points to an active fact in the same scope. Runtime hashes prove source currency, **not the truth of the claim**. Changed sources and facts older than 30 days are excluded from active retrieval pending revalidation. Use new IDs to retain history. Existing design decisions remain authoritative. The compact project VAULT points to current sources and gotchas; it should not duplicate a decision log or grow into a session transcript.

A proposal requires `title`, `observations`, `hypothesis`, `change`, `risks`, `evaluation`, and `rollback`. It is stored inactive. See `evals/README.md` for 24 scenario seeds and a paired-trial scorer. No live evaluation outcomes are implied by the existence of the scenarios. No autonomous config activation or scheduled evaluation is installed.

State is local under `state/` and excluded from source Git. Runtime metadata lives in `state/runtime/runtime.sqlite3`; deployment backups and proposals remain separate. For a 1.0 installation, run `python -B $eng state migrate` once with host access before activation. This copies and preserves the legacy database and refuses to overwrite an existing destination. Use one consistent `ENG_SETUP_STATE_DIR` for CLI and hooks if relocating metadata. A state-access failure never silently creates a fallback database. Events retain metadata for 30 days, pruned at session start. Tasks/facts/proposals/backups persist until deliberately cleaned up. Do not put secrets or raw conversations in user-supplied records. Do not automatically query unrelated project scopes.

On Windows, only the runtime metadata directory needs write access. Native sandbox restrictions can still block it even when an ordinary directory ACL grants access. Doctor distinguishes readable state from writable state. When writes are unavailable, run state-changing commands with authorized host access; do not create an empty fallback database or broaden sandbox permissions. The runtime never changes permissions. Structured protection of KeepHQ runs before database access, including native `apply_patch` command payloads.

Concurrent verification and checkpoints merge inside database transactions. In-flight checks prevent task completion. Interrupted checks remain visible: inspect their state, then use `task abandon-check --session SESSION --check-id ID --reason 'Explanation'` before recording replacement evidence. Abandoning a check never marks it passed. Delivery fingerprints each repository once per inspection.

For usage measurement, `usage --provider codex|claude --file native-events.jsonl` extracts final usage counters only. Save its output and attach selected, supported fields with `task metrics --session SESSION --file metrics.json`. Supported metrics include tokens/cache tokens, latency, retries, acceptance, defects, human correction time, and cost with a source reference. Missing counters and costs remain null. Claude's native USD figure is provider-reported API-equivalent usage, not proof of a subscription charge. Hooks never read transcripts or start model calls. Known native outcome envelopes produce success/failure/running metadata; unsupported formats stay unknown.

Doctor checks setup-owned keys and hooks independently of your model choices, preferences, and native trust state. It also checks deployed runtime source hashes, metadata access, and duplicate skill discovery directories. Unmanaged duplicate skills are reported, not removed automatically. Claude read-only roles keep their restricted tools; the lead supplies saved diffs and command/browser evidence. Each generated Claude role now declares its effort explicitly.

## Change, deploy, recover

Edit maintained source in an isolated candidate for behavior changes, run relevant tests and behavioral trials, then present the exact diff for user review. Do not edit generated native files independently. Keep the active release stable during tasks.

```powershell
python -B -m unittest discover -s tests -v
python -B $eng config build
python -B $eng config diff 'C:/Users/guyr2/.codex/agent-setup/build/deployment.json'
# Only after actual approval of that concrete configuration change:
python -B $eng config apply 'C:/Users/guyr2/.codex/agent-setup/build/deployment.json' --approval-ref 'User approval reference'
python -B $eng doctor
# If authorized and needed:
python -B $eng config rollback 'C:/path/to/release.json' --approval-ref 'User rollback request'
```

Build refuses unmanaged instruction collisions. Apply preflights target hashes, saves exact prior bytes, and reverts completed writes if a normal write fails. A process/power interruption can leave a partial installation; use the saved release manifest to inspect and repair before another apply. Rollback refuses later file drift. Native config merges preserve unrelated settings/hooks. Release manifests include merged settings backups, so keep state local and out of commits.

The hook dispatcher runs the Python files in this maintained directory. Therefore, **editing runtime Python or policy.json here changes live hook behavior** once hooks are trusted. Develop candidates in a separate checkout and promote them only after review, between tasks. The deployment rollback restores generated native files; a runtime-code rollback additionally requires restoring the reviewed source revision from this directory's Git history. Inspect local changes first and preserve unrelated work. Do not claim a native-file rollback alone has rolled back Python behavior.

The activation approval reference is an audit trail, not an authentication mechanism. Runtime permissions and the user's actual instructions still govern who may apply changes. The initial implementation is authorized by the user's request to implement this setup; future behavior changes require their review.

## Reference documentation

Provider schemas checked on 2026-10-02 against [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex hooks](https://learn.chatgpt.com/docs/hooks), [Claude hooks](https://code.claude.com/docs/en/hooks), and [Claude subagents](https://code.claude.com/docs/en/sub-agents). Host versions at implementation: Codex 0.159.0-alpha.12.1 and Claude Code 2.1.220. Recheck schemas when upgrading; do not infer a feature works merely because the latest documentation describes it.
