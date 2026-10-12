---
name: eng-work
description: Choose and carry out an engineering workflow when a coding request spans investigation, planning, implementation, and delivery or needs coordination.
---

Select focused, planned, or program work from uncertainty, risk, and repository boundaries. Local fixes normally need direct implementation and targeted checks, without formal plan documents or subagents.

For planned work establish observable acceptance criteria, inspect relevant instructions/design/code, and keep a short dependency-aware plan. Program work needs repository contracts, revision combinations, and integration ownership. Preserve local edits. Delegate only when permitted and useful, with explicit file ownership and a bounded output contract.

Load only the specialist skill needed at a decision boundary: investigation for unexplained behavior, planning for consequential choices, UI for rendered interaction, migration for compatibility transitions, review for independent assessment. Do not load the whole suite. If another skill is unavailable, perform the necessary work directly.

Carry the work through implementation, meaningful checks, real workflow execution, diagnosis, repair, and retesting. Use `eng-verify` for coverage and evidence; changes affecting UI workflows also need browser verification, including when the change is in the backend. Run the project's critical smoke suite and regression checks selected from the change's impact. The implementing agent remains responsible for verification even without a separate verifier.

When delegation is permitted and useful, give configured fast verification workers explicit steps, expected outcomes, environment, snapshot, and artifact boundaries. Retain coverage decisions, ambiguous or high-risk assessment, and completion with the main agent. Integrate worker findings, fix defects introduced by the work, and have affected checks rerun against the repaired version. Missing worker tools are a routing problem for the lead, not a passing check. Focused checks can run directly without delegation overhead.

Finish only after the authorized outcome and applicable checks are satisfied, or clearly report the exact blocker and unverified behavior. Repeated failure should change the hypothesis; continue while meaningful authorized progress is possible. Report unrelated defects separately rather than silently expanding scope. For long work use task/checkpoint commands in `{{SETUP_ROOT}}/README.md`; focused work can remain in conversation.

For substantial work register `engctl task`, maintain a concise checkpoint with completed work, next steps, decisions, and source references, and use `engctl verify` for command evidence. Before handoff or compaction update the checkpoint explicitly; hooks cannot infer missing state. Resume by reconciling the record with current code and user intent. Receipts prove command outcomes on a snapshot, not semantic correctness. Keep raw conversations and credentials out of state. For denied metadata writes, use authorized host execution or report the limitation; do not fork an empty state store or broaden permissions.

Keep intended behavior and decisions in existing design sources, executed results in delivery evidence, and a VAULT only as a compact current index. Distinguish user decisions, assistant choices, verified observations, and proposals. Mark superseded material and keep current summaries consistent. Never rewrite a requirement merely to match implementation.
