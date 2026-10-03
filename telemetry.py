"""Normalize known native envelopes; retain metrics, never transcripts or stdout."""
import json
import math
import re


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def hook_outcome(payload):
    provider = 'codex' if 'turn_id' in payload else 'claude' if 'permission_mode' in payload else 'unknown'
    duration = payload.get('duration_ms')
    duration = duration if number(duration) else None
    if payload.get('hook_event_name') == 'PostToolUseFailure':
        return 'failure', provider, duration
    if payload.get('hook_event_name') != 'PostToolUse':
        return 'unknown', provider, duration
    response = payload.get('tool_response')
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except ValueError:
            # Codex's shell envelope precedes Output:. Never scan command stdout
            # for an exit marker that an arbitrary program could print.
            header = response.partition('\nOutput:')[0]
            match = re.search(r'^Process exited with code (-?\d+)\s*$', header, re.M)
            if header.startswith('Chunk ID:') and match and '\nWall time:' in header:
                return ('success' if int(match[1]) == 0 else 'failure'), provider, duration
            return ('success' if provider == 'claude' else 'unknown'), provider, duration
    if isinstance(response, dict):
        if response.get('isError') is True or response.get('is_error') is True:
            return 'failure', provider, duration
        for key in ('exit_code', 'exitCode'):
            if type(response.get(key)) is int:
                return ('success' if response[key] == 0 else 'failure'), provider, duration
        if response.get('session_id') is not None:
            return 'running', provider, duration
        if response.get('isError') is False or response.get('is_error') is False:
            return 'success', provider, duration
    # Claude separates failed calls into PostToolUseFailure. Codex also sends
    # nonzero commands through PostToolUse, so this default is provider-specific.
    return ('success' if provider == 'claude' else 'unknown'), provider, duration


NUMERIC_METRICS = {'seconds', 'human_correction_seconds', 'retries', 'defects',
                   'input_tokens', 'cached_input_tokens', 'cache_write_tokens',
                   'output_tokens', 'reasoning_tokens', 'cost_usd', 'credits'}
TEXT_METRICS = {'provider', 'model', 'effort', 'runtime', 'usage_source', 'evidence'}
BOOL_METRICS = {'accepted', 'first_pass_accepted'}


def validate_metrics(value):
    if not isinstance(value, dict) or set(value) - NUMERIC_METRICS - TEXT_METRICS - BOOL_METRICS:
        raise ValueError('Metrics contain unsupported fields; do not submit raw logs or conversations.')
    for key, val in value.items():
        if val is None:
            continue
        if key in NUMERIC_METRICS and not number(val):
            raise ValueError('Metric must be a finite nonnegative number: ' + key)
        if key in BOOL_METRICS and type(val) is not bool:
            raise ValueError('Metric must be boolean or null: ' + key)
        if key in TEXT_METRICS and (not isinstance(val, str) or not 1 <= len(val) <= 500):
            raise ValueError('Metric text must be a short nonempty reference: ' + key)
    if any(value.get(k) is not None for k in ('cost_usd', 'credits')) and not value.get('usage_source'):
        raise ValueError('Measured cost requires its usage source; unknown cost must remain null.')
    return dict(value)


def native_usage(provider, rows):
    """Read only final usage objects from an explicitly supplied native stream."""
    if provider not in ('codex', 'claude') or not isinstance(rows, list):
        raise ValueError('Usage requires a supported provider and a list of native events.')
    found = []
    models = set()
    costs = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if provider == 'codex' and row.get('type') == 'turn.completed' and isinstance(row.get('usage'), dict):
            found.append(row['usage'])
        elif provider == 'claude' and row.get('type') == 'result':
            if isinstance(row.get('usage'), dict):
                found.append(row['usage'])
            costs.append(row.get('total_cost_usd'))
            if isinstance(row.get('modelUsage'), dict):
                models.update(row['modelUsage'].keys())
    cost = sum(costs) if costs and all(number(c) for c in costs) else None
    result = {'provider': provider, 'cost_usd': cost, 'credits': None,
              'usage_source': provider + ' native final usage', 'model': ','.join(sorted(models)) or None}
    mapping = {'input_tokens': 'input_tokens', 'output_tokens': 'output_tokens',
               'cached_input_tokens': 'cached_input_tokens' if provider == 'codex' else 'cache_read_input_tokens',
               'cache_write_tokens': 'cache_creation_input_tokens', 'reasoning_tokens': 'reasoning_tokens'}
    for key, native in mapping.items():
        values = [r.get(native) for r in found]
        result[key] = sum(values) if values and all(number(v) for v in values) else None
    return result
