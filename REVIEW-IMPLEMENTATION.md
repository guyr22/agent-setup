# Agent setup review implementation — 2026-10-03

Implemented against baseline `05539768e05b8adbe4ed8bad78df50a3fa2aaa62` in an isolated candidate. User authorization: “implement these”; live evaluation cap: “Broader benchmark: up to 24 isolated model runs.” The selected main model remains unchanged. No project setup, KeepHQ changes, plugin installation, recurring evaluation, or automatic model-policy promotion is part of this release.

| Review item | Result |
| --- | --- |
| R1: native patch shape | Parse `tool_input.command`, including CRLF and move destinations; protected paths are checked before database access. |
| R2: lost concurrent evidence | Transactional task updates merge receipts/checkpoints; in-flight and interrupted checks prevent misleading completion. |
| R3: test builds overwrite staging | Alternate homes require explicit output paths; tests use isolated staging. |
| R4: unknown outcomes/no metrics | Normalize known native outcomes; import final native usage counters and validated task metrics without retaining tool output or conversations. |
| R5: false drift/no runtime identity | Compare only owned settings and hook definitions, fingerprint deployed source, report state readability/writability and duplicate skills. Preserve native sections inserted inside managed markers. |
| R6: unmeasured model choices | Completed 16 Codex trials across four configurations; one Claude launch failed without authentication. No global model change. |
| R7: scorer cannot compare models | Separate instruction, effort, and model-policy comparisons; require controlled fixtures/runtime/provider/harness and report regressions. |
| R8: Claude role differences | Generate explicit effort and require supplied diffs/evidence for restricted read roles. Native inference validation remains blocked by missing Claude login. |
| R9: Windows state access | Separate runtime metadata, explicitly migrate the old database, close connections, avoid per-call WAL changes, and provide actionable diagnostics. This session's native sandbox still prevents writes; authorized host access is required. A narrow ACL experiment did not help and was fully reverted. |
| R10: knowledge-store complexity | Retain the existing simple, scoped store as recommended; no speculative retrieval machinery. |

## Verification and evaluation

`C:/Python313/python.exe -B validate.py` validates 14 skill frontmatters, 53 native outputs, source syntax, and the deterministic regression suite. New cases exercise the actual native patch shape, concurrent success/failure/checkpoint races, interrupted checks, state migration and failures, owned drift, staging isolation, usage sanitization, comparison controls, and grading controls. These are command and fixture results, not proof of production agent quality.

The native benchmark used Codex CLI `0.159.0-alpha.12.1`, read-only sandboxing, ephemeral sessions, identical self-contained prompts, JSON artifacts, and external deterministic graders. Each configuration received recursive configuration merging, event normalization, a clean review, and a repeat of event normalization. All 16 Codex artifacts passed with no observed tool-use violations. Claude Code `2.1.220` produced one failed invocation; `claude auth status` then reported `loggedIn: false`. Further Claude trials were skipped. Total: 17 launch attempts within the authorized cap of 24.

| Configuration | Accepted | Median seconds | Input tokens | Output tokens | Estimated Standard credits, all four trials |
| --- | ---: | ---: | ---: | ---: | ---: |
| Astra xhigh | 4/4 | 20.87 | 70,432 | 1,597 | 19.6043 |
| Astra high | 4/4 | 16.93 | 70,424 | 1,023 | 18.8848 |
| Sol medium | 4/4 | 19.49 | 70,672 | 850 | 3.7461 |
| Luna medium | 4/4 | 10.28 | 67,912 | 638 | 0.1778 |

No cached input tokens were reported. Credit estimates apply published Standard rates to the recorded counters; they are **not billed credits, dollar charges, or a measurement of included subscription-limit consumption**. Actual USD cost remains null. Rates checked on 2026-10-03: Astra 250/25/1250, Sol 50/2.5/250, Luna 2.5/0.25/12.5 credits per million input/cached/output tokens. Speed modes and included subscription usage differ. [Official pricing](https://learn.chatgpt.com/docs/pricing).

The results support trying the existing fast/balanced profiles for bounded tasks. They do not establish that Luna or Sol can replace Astra for architecture, difficult debugging, long-running repository work, security review, or UI validation. System/context overhead dominates these tiny prompts; they do not measure project context management or savings from the runtime fixes. Zero observed failures in four trials is weak reliability evidence. Native CLI overhead and unrandomized order also limit latency conclusions. Requested model IDs were recorded; the Codex final usage stream did not expose a resolved server model revision.

Raw synthetic artifacts, prompt/fixture hashes, native counters, the launch ledger, and paired comparison reports are retained in the candidate's `state/benchmarks/20261003/`. No raw provider streams or user conversations were saved. The final release record links the candidate and source backup. Compare acceptance, corrections, retries, and total task cost on representative project work before changing a global default.

## Design basis

The concrete defects were reproduced locally; the engineering sources informed the design choices rather than serving as proof that this implementation works:

- Ryan Lopopolo, OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/): maintain navigable context and mechanically check the execution environment. This release improves checks and diagnostics rather than expanding the global instruction document.
- Anthropic Engineering, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents): grade observable outcomes, isolate trials, include negative cases, and keep multiple trials. The scorer preserves failures and uncertainty instead of selecting a model from token savings alone.
- Anthropic Applied AI, [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents): retain compact, relevant context and use deliberate handoff/state. The existing progressive context and scoped knowledge design remain intact.
- [Codex hook contract](https://learn.chatgpt.com/docs/hooks), [Claude hook contract](https://code.claude.com/docs/en/hooks), and [Claude subagent contract](https://code.claude.com/docs/en/sub-agents) inform the provider-specific adapters. Local CLI help confirms the installed Claude effort flag, but authenticated role execution remains untested.

## Operation and recovery

Start fresh native sessions to pick up generated role definitions. Hook command definitions and native trust are preserved. Doctor checks installed/source consistency and state access but cannot certify native trust or end-to-end activation merely from file contents.

Native configuration backups and the maintained-source backup are distinct. A generated-file rollback alone cannot roll back Python hook behavior. The source promotion manifest saves exact prior bytes, baseline revision, new hashes, and newly added paths. Inspect for subsequent edits before restoring either source or native files. The legacy database is preserved; do not switch back to it after new work without reconciling newer task state. Do not delete unmanaged duplicate `.agents/skills` copies without resolving their ownership.

The first activation preflight caught an additional preservation defect: native Codex had placed hook-trust sections inside the installer markers, and replacing that whole region would delete them. The release stopped and restored source before native files were changed. The revised merge edits only the two owned agent keys and returns an already-correct configuration unchanged. An exact-layout regression covers both unchanged and modified agent settings while preserving trust.
