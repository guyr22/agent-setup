"""Summarize independently graded paired trials; never invent trial outcomes."""
import json
from pathlib import Path
import statistics
import sys
import math
import argparse

def valid_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def score(rows, mode='instructions'):
    if mode not in ('instructions', 'effort', 'model-policy'):
        raise ValueError('Unknown comparison mode')
    seen = set()
    pairs = {}
    for r in rows:
        required = {'case', 'trial', 'variant', 'fixture', 'model', 'runtime', 'accepted', 'violations', 'seconds', 'cost_usd', 'evidence'}
        if not required <= r.keys() or r['variant'] not in ('baseline', 'candidate'):
            raise ValueError('Incomplete or invalid trial')
        if (type(r['accepted']) is not bool or not isinstance(r['violations'], list)
                or not all(isinstance(v, str) for v in r['violations'])
                or not valid_number(r['seconds']) or not r['evidence']):
            raise ValueError('Invalid grade or missing evidence')
        if r['cost_usd'] is not None and not valid_number(r['cost_usd']):
            raise ValueError('Cost must be finite, nonnegative, or null')
        key = (r['case'], r['trial'], r['variant'])
        if key in seen: raise ValueError('Duplicate trial')
        seen.add(key)
        pairs.setdefault(key[:2], {})[r['variant']] = r
    if not pairs: raise ValueError('No behavioral trials supplied')
    regressions = []
    for key, pair in pairs.items():
        if len(pair) != 2: raise ValueError('Missing baseline/candidate pair')
        a, b = pair['baseline'], pair['candidate']
        controlled = ['fixture', 'runtime', 'provider']
        if mode != 'model-policy': controlled += ['model']
        if mode == 'instructions': controlled += ['effort']
        else:
            if any(not r.get(k) for r in (a, b) for k in ('provider', 'effort', 'harness')):
                raise ValueError('Model/effort comparisons require provider, effort, and harness identity')
            controlled += ['harness']
        if any(a.get(k) != b.get(k) for k in controlled):
            raise ValueError('Comparison changed controlled fields: ' + ', '.join(controlled))
        if (a['accepted'] and not b['accepted']) or set(b['violations']) - set(a['violations']):
            regressions.append({'case': key[0], 'trial': key[1]})
    result = {'mode': mode, 'pairs': len(pairs), 'cases': sorted({k[0] for k in pairs}),
              'quality_regressions': regressions, 'activation': 'Requires user review; no automatic promotion'}
    for variant in ('baseline', 'candidate'):
        selected = [p[variant] for p in pairs.values()]
        costs = [r['cost_usd'] for r in selected]
        total_cost = sum(costs) if all(c is not None for c in costs) else None
        accepted = sum(r['accepted'] for r in selected)
        durations = sorted(r['seconds'] for r in selected)
        result[variant] = {'acceptance_rate': accepted / len(selected),
                           'violations': sum(len(r['violations']) for r in selected),
                           'median_seconds': statistics.median(r['seconds'] for r in selected),
                           'p95_seconds': durations[math.ceil(.95 * len(durations)) - 1],
                           'total_cost_usd': total_cost,
                           'cost_per_accepted_task_usd': total_cost / accepted if accepted and total_cost is not None else None,
                           'missing_cost_trials': sum(c is None for c in costs)}
        for metric in ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens', 'human_correction_seconds', 'retries'):
            values = [r.get(metric) for r in selected]
            result[variant]['total_' + metric] = sum(values) if all(valid_number(v) for v in values) else None
    result['candidate_has_no_observed_quality_regression'] = not regressions and not result['candidate']['violations']
    result['limitations'] = ['Small samples are exploratory; do not infer production reliability.',
                            'Unrecorded retries cannot be measured; include all attempts.']
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--mode', choices=['instructions', 'effort', 'model-policy'], default='instructions')
    args = parser.parse_args()
    try:
        print(json.dumps(score(json.loads(args.file.read_text(encoding='utf-8-sig')), args.mode), indent=2))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(1)
