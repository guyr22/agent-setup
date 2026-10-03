<!-- eng-project-setup -->
## Shared engineering setup: agent navigation

Maintain a portable Python installer and runtime for Codex and Claude Code.

### Sources of authority

- design: `README.md` — Installation contract, lifecycle and native boundaries
- instructions: `PROJECT-SETUP.md` — Collaborative repository onboarding
- verification: `validate.py` — Native schema and deterministic regression entry point

### Areas and ownership

- `configure.py`: Native render, ownership, preview, application and rollback; owner: maintainer.
- `install.py`: Selective client installation and safe removal; owner: maintainer.
- `tests`: Isolated native-home and runtime fixtures; owner: maintainer.

### Verification

- regression: `["python", "-B", "validate.py"]` in `.` (observed; README.md; validate.py runs the complete deterministic suite).

### Project invariants

- Use the Python standard library for runtime and installer dependencies.
- Tests must use isolated homes/state; never apply a fixture deployment to a real client configuration.
- Preserve unrelated settings, personal instructions, permissions, authentication and native hook trust.
- Changes to installed Python are live hook changes; develop in an inactive checkout and activate only within explicit authorization.
- Keep local.json, local.instructions.md, build outputs and runtime state out of Git.

### Local conventions

- Run targeted tests while iterating and python -B validate.py for delivery.
- Report Windows checks separately from unexecuted macOS/Linux native validation.
- Do not add model calls or automatic update jobs to installation or hooks.

Use this project guidance with more specific area instructions. Requirements and decisions remain in their linked sources.
Preserve local changes; use the narrowest meaningful checks and report what actually ran. Setup does not grant deployment authority.
<!-- /eng-project-setup -->
