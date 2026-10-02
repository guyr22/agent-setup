---
name: eng-migrate
description: Execute a broad mechanical refactor, schema or API migration, or compatibility transition with sampled validation, staged rollout, and recovery.
---

Inventory affected producers/consumers and generated code. Establish invariants, compatibility window, deployment order, and recovery. A large replacement is not evidence of semantic equivalence.

Transform a representative sample, inspect the diff, and run discriminating checks. Use bounded, rerunnable codemods when repetition and syntax warrant them. Validate exclusions and already-migrated cases before expanding.

For data changes separate additive schema, backfill, consumer transition, and removal. A migration file does not authorize destructive production execution. Pin cross-repository revision combinations.

Track remaining instances and intentional exceptions. Verify invariants and affected checks, beyond a zero-match search. Report partial coverage and retain recovery instructions until completion is confirmed.
