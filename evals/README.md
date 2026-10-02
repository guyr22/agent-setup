# Paired workflow evaluations

`cases.json` contains 24 scenario seeds, including negative triggers. Adapt raw fixtures to the changed capability. A scenario is not a completed evaluation.

For a candidate, copy the maintained source into an isolated directory or branch and retain the baseline revision. Do not deploy either version over an active global installation for a trial. Give each evaluator the same request and raw fixture at the same revision, plus the applicable candidate or baseline skill. Do not show the expected answer to the acting agent. Use isolated allowed output directories and identical model/runtime/budgets. Independent evaluation is appropriate for consequential workflow changes when delegation is authorized; do not spawn an evaluation fleet automatically.

First run deterministic tests: `python -B -m unittest discover -s tests -v`. Then run applicable behavioral scenarios, including negative cases. Grade observable artifacts and actions against the rubric, separately from the acting agent's self-report. Repeat consequential scenarios at least twice. Record:

```json
{"case":"01-local-bug","trial":1,"variant":"baseline","fixture":"fixture commit/hash","model":"actual model","runtime":"actual version","accepted":true,"violations":[],"seconds":42.0,"cost_usd":null,"evidence":"path to inspected result and tool evidence"}
```

Cost must come from measured usage/pricing or remain null. Do not infer quality from token savings alone. Summarize with `python -B evals/score.py results.json`; incomplete pairing is rejected. Report pass rate, violations, wall time, measured cost, and missing coverage. A one-trial result is exploratory, not proof of improvement. Keep risky regressions disqualifying even when average speed improves.

Store the exact diff and report in an inactive proposal. Present both improvements and regressions, applicability, uncertainty, and rollback. Only an actual user approval of the concrete change authorizes activation. This setup intentionally has no scheduled model calls, automatic policy promotion, or permission expansion.
