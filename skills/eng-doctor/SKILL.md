---
name: eng-doctor
description: Diagnose missing skills, configuration drift, hook activation, model availability, or failures in the shared Codex and Claude Code setup.
---

Run `{{PYTHON}} {{SETUP_ROOT}}/engctl.py doctor`. Read the setup README for recovery. Compare source, rendered native files, and deployment record; preserve unmanaged settings and preferences.

Check native client versions/schemas before changes and model availability before retries. Inspect `/hooks`; Codex requires trust for exact hook definitions. Never forge trust or bypass it. New sessions may be needed to load changes.

Use metadata for diagnosis; do not read auth files or full transcripts just to troubleshoot configuration. Run relevant deterministic runtime tests. Prepare drift-aware diffs/backups before repair. Existing authorization governs routine repairs; new behavior or permissions requires review.

Report installed versus executed versus unverified states. Hooks supplement native permissions and cannot secure arbitrary shell commands.
