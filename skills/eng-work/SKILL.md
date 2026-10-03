---
name: eng-work
description: Choose and carry out an engineering workflow when a coding request spans investigation, planning, implementation, and delivery or needs coordination.
---

Select focused, planned, or program work from uncertainty, risk, and repository boundaries. Local fixes normally need direct implementation and targeted checks, without formal plan documents or subagents.

For planned work establish observable acceptance criteria, inspect relevant instructions/design/code, and keep a short dependency-aware plan. Program work needs repository contracts, revision combinations, and integration ownership. Preserve local edits. Delegate only when permitted and useful, with explicit file ownership and a bounded output contract.

Load only the specialist skill needed at a decision boundary: investigation for unexplained behavior, planning for consequential choices, UI for rendered interaction, migration for compatibility transitions, review for independent assessment. Do not load the whole suite. If another skill is unavailable, perform the necessary work directly.

Finish the authorized outcome, verify acceptance criteria, and state evidence and limitations. Repeated failure should change the hypothesis. For long work use task/checkpoint commands in `{{SETUP_ROOT}}/README.md`; focused work can remain in conversation.

For substantial work register `engctl task`, maintain a concise checkpoint with completed work, next steps, decisions, and source references, and use `engctl verify` for command evidence. Before handoff or compaction update the checkpoint explicitly; hooks cannot infer missing state. Resume by reconciling the record with current code and user intent. Receipts prove command outcomes on a snapshot, not semantic correctness. Keep raw conversations and credentials out of state. For denied metadata writes, use authorized host execution or report the limitation; do not fork an empty state store or broaden permissions.

Keep intended behavior and decisions in existing design sources, executed results in delivery evidence, and a VAULT only as a compact current index. Distinguish user decisions, assistant choices, verified observations, and proposals. Mark superseded material and keep current summaries consistent. Never rewrite a requirement merely to match implementation.
