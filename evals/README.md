# Paired workflow evaluations

`cases.json` contains 24 scenario seeds, including negative triggers. Adapt raw fixtures to the changed capability. A scenario is not a completed evaluation.

For a candidate, copy the maintained source into an isolated directory or branch and retain the baseline revision. Do not deploy either version over an active global installation for a trial. Give each evaluator the same request and raw fixture at the same revision, plus the applicable candidate or baseline skill. Do not show the expected answer to the acting agent. Use isolated allowed output directories and identical model/runtime/budgets. Independent evaluation is appropriate for consequential workflow changes when delegation is authorized; do not spawn an evaluation fleet automatically.

First run deterministic tests: `python -B -m unittest discover -s tests -v`. Then run applicable behavioral scenarios, including negative cases. Grade observable artifacts and actions against the rubric, separately from the acting agent's self-report. Repeat consequential scenarios at least twice. Record:

```json
{"case":"01-local-bug","trial":1,"variant":"baseline","fixture":"fixture commit/hash","model":"actual model","runtime":"actual version","accepted":true,"violations":[],"seconds":42.0,"cost_usd":null,"evidence":"path to inspected result and tool evidence"}
```

Cost must come from measured usage/pricing or remain null. Do not infer quality from token savings alone. Summarize with `python -B evals/score.py results.json`; incomplete pairing is rejected. Report pass rate, violations, wall time, measured cost, and missing coverage. A one-trial result is exploratory, not proof of improvement. Keep risky regressions disqualifying even when average speed improves.

Comparison modes are explicit. Default `--mode instructions` holds model and effort constant. `--mode effort` allows effort to change while holding model constant. `--mode model-policy` allows model/effort changes while holding provider, native runtime, fixture, and harness constant. The latter two require explicit `provider`, `effort`, and `harness` fields. Cross-provider results should be reported separately because the native harnesses differ. Include failures and every attempted launch; missing costs are not zero. The scorer reports regressions, median/p95 time, token totals, and cost per accepted task when costs exist.

`benchmark.py` is an opt-in native CLI harness with a persistent launch ledger and an explicit maximum of 24 calls. It runs at most two calls concurrently. It uses synthetic no-tool tasks: recursive configuration merging without aliases, event outcome normalization (repeated), and a clean review to detect invented findings. Artifacts are independently checked; execution of generated pure functions is restricted and has a five-second process timeout. Prompt, fixture hash, final synthetic artifact, grade, runtime/model/effort, latency, and native token usage are retained. Raw streams and conversations are discarded. An operational failure suppresses further calls for that profile. Claude uses safe mode and disabled tools; Codex uses read-only native sandboxing and retains native rules. Never use a permission or trust bypass for these trials.

Example (requires prior authorization for the calls and installed/authenticated native CLIs):

```powershell
python -B evals/benchmark.py --output state/benchmarks/TRIAL --max-runs 24 --codex C:/path/codex.exe --claude C:/path/claude.exe
```

Run one harness process per output directory. Its ledger is restart-safe, not a multiprocess scheduler. The small fixture set measures bounded reasoning and artifact correctness, not end-to-end repository work, tool operation, UI quality, or long-running recovery. It must not automatically select a global model. For a policy change, add representative project tasks and inspect acceptance, corrections, and total cost under equivalent conditions.

Store the exact diff and report in an inactive proposal. Present both improvements and regressions, applicability, uncertainty, and rollback. Only an actual user approval of the concrete change authorizes activation. This setup intentionally has no scheduled model calls, automatic policy promotion, or permission expansion.
