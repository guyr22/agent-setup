"""Summarize independently graded paired trials; never invent trial outcomes."""
import json
from pathlib import Path
import statistics
import sys

def score(rows):
    seen = set()
    pairs = {}
    for r in rows:
        required = {'case', 'trial', 'variant', 'fixture', 'model', 'runtime', 'accepted', 'violations', 'seconds', 'cost_usd', 'evidence'}
        if not required <= r.keys() or r['variant'] not in ('baseline', 'candidate'):
            raise ValueError('Incomplete or invalid trial')
        if type(r['accepted']) is not bool or not isinstance(r['violations'], list) or r['seconds'] < 0 or not r['evidence']:
            raise ValueError('Invalid grade or missing evidence')
        key = (r['case'], r['trial'], r['variant'])
        if key in seen: raise ValueError('Duplicate trial')
        seen.add(key)
        pairs.setdefault(key[:2], {})[r['variant']] = r
    if not pairs: raise ValueError('No behavioral trials supplied')
    for pair in pairs.values():
        if len(pair) != 2: raise ValueError('Missing baseline/candidate pair')
        if any(pair['baseline'][k] != pair['candidate'][k] for k in ('fixture', 'model', 'runtime')):
            raise ValueError('Baseline/candidate fixture, model, and runtime must match')
    result = {'pairs': len(pairs), 'cases': sorted({k[0] for k in pairs}), 'activation': 'Requires user review; no automatic promotion'}
    for variant in ('baseline', 'candidate'):
        selected = [p[variant] for p in pairs.values()]
        costs = [r['cost_usd'] for r in selected]
        result[variant] = {'acceptance_rate': sum(r['accepted'] for r in selected) / len(selected),
                           'violations': sum(len(r['violations']) for r in selected),
                           'median_seconds': statistics.median(r['seconds'] for r in selected),
                           'total_cost_usd': sum(costs) if all(c is not None for c in costs) else None}
    return result

if __name__ == '__main__':
    try:
        print(json.dumps(score(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))), indent=2))
    except (ValueError, IndexError) as exc:
        print(str(exc), file=sys.stderr); raise SystemExit(1)
