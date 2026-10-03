"""Opt-in, bounded native-CLI microbenchmark. No automatic model-policy changes.

Only synthetic prompts, final artifacts, external grades, and usage metadata are
saved. Run stdout/stderr and conversations are never retained. Each invocation
consumes one slot before launch; restarting does not reset the budget.
"""
from __future__ import annotations
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from telemetry import native_usage

PROFILES = {
    'codex-astra-xhigh': ('codex', 'gpt-6-astra', 'xhigh'),
    'codex-astra-high': ('codex', 'gpt-6-astra', 'high'),
    'codex-sol-medium': ('codex', 'gpt-6.1-sol', 'medium'),
    'codex-luna-medium': ('codex', 'gpt-6-luna', 'medium'),
    'claude-opus-high': ('claude', 'opus', 'high'),
    'claude-sonnet-medium': ('claude', 'sonnet', 'medium'),
}
CASES = {
    'merge': '''Implement merge_settings(base, override) in Python. Inputs are nested JSON-like dictionaries. Return a NEW dictionary. Merge recursively only where both values are dictionaries. Otherwise the override replaces the base value, including False, 0, None, empty lists, and empty dictionaries when the base value is not a dictionary. Preserve base keys absent in override. No mutable dictionary or list in the result may alias either input, including unchanged branches or replacement lists. Do not mutate inputs. No imports; implement any helpers yourself.''',
    'outcome': '''Implement outcome(event, response) in Python. Return one of success/failure/running/unknown. PostToolUseFailure is always failure. Any event other than PostToolUse is unknown. For PostToolUse, non-dictionary responses are unknown. For dictionaries: (1) isError or is_error exactly True means failure; (2) exit_code, or exitCode only if exit_code is absent, is authoritative ONLY when its type is exactly int, excluding bool; zero means success, other integers failure; (3) a non-null session_id means running; (4) isError or is_error exactly False means success; (5) otherwise unknown. Do not parse stdout, stringify objects, or infer from truthiness. No imports.''',
    'clean-review': '''Review this Python function only against the stated contract. Report actionable correctness defects, if any, in findings. No stylistic suggestions or hypothetical requirements. Contract: accept only exact integers (booleans excluded) in inclusive range 0..100; return default for all other Python values. Default may be any value and must be returned unchanged. Source:
def parse_limit(value, default=10):
    if type(value) is int and 0 <= value <= 100:
        return value
    return default
Return an empty code string. Each finding must name an actual contract violation.''',
}
TRIALS = [('merge', 1), ('outcome', 1), ('clean-review', 1), ('outcome', 2)]
SCHEMA = {'type': 'object', 'properties': {'code': {'type': 'string'}, 'findings': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['code', 'findings'], 'additionalProperties': False}
HARNESS = 'synthetic-no-tools-v1'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def grade(case, artifact):
    if not isinstance(artifact, dict) or set(artifact) != {'code', 'findings'}:
        return False, ['invalid artifact shape']
    if not isinstance(artifact['code'], str) or not isinstance(artifact['findings'], list):
        return False, ['invalid artifact types']
    if artifact['findings']:
        return False, ['unexpected correctness finding']
    if case == 'clean-review':
        return artifact['code'] == '', [] if artifact['code'] == '' else ['unexpected code change']
    # Execution has no filesystem/network/process builtins. Reject dynamic escape
    # constructs and all attribute access except these ordinary container methods.
    allowed_methods = {'get', 'items', 'keys', 'values', 'copy', 'append', 'extend'}
    allowed_builtins = {'dict': dict, 'list': list, 'tuple': tuple, 'int': int, 'str': str,
                        'bool': bool, 'float': float, 'type': type, 'isinstance': isinstance,
                        'len': len, 'range': range, 'enumerate': enumerate, 'set': set}
    try:
        tree = ast.parse(artifact['code'])
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Global, ast.Nonlocal)):
                raise ValueError('unsupported execution construct')
            if isinstance(node, ast.Attribute) and node.attr not in allowed_methods:
                raise ValueError('unsupported attribute')
            if isinstance(node, ast.Name) and node.id.startswith('__'):
                raise ValueError('unsupported name')
        scope = {'__builtins__': allowed_builtins}
        exec(compile(tree, '<synthetic-answer>', 'exec'), scope)
        if case == 'merge':
            f = scope['merge_settings']
            base = {'a': {'x': [1, {'z': 3}], 'b': True}, 'untouched': [{'k': [2]}], 'n': 9, 'list': [1], 'v': 4}
            override = {'a': {'b': False, 'zero': 0}, 'n': None, 'list': [], 'v': {}}
            before = json.dumps([base, override], sort_keys=True)
            result = f(base, override)
            assert result == {'a': {'x': [1, {'z': 3}], 'b': False, 'zero': 0}, 'untouched': [{'k': [2]}], 'n': None, 'list': [], 'v': {}}
            assert json.dumps([base, override], sort_keys=True) == before
            def ids(value):
                found = {id(value)} if isinstance(value, (dict, list)) else set()
                for v in (value.values() if isinstance(value, dict) else value if isinstance(value, list) else []):
                    found.update(ids(v))
                return found
            assert not ids(result) & (ids(base) | ids(override))
            assert f({'x': {'a': 1}}, {'x': {}}) == {'x': {'a': 1}}
            assert f({}, {'x': [False, {'a': [None]}]}) == {'x': [False, {'a': [None]}]}
        else:
            f = scope['outcome']
            checks = [('PostToolUseFailure', None, 'failure'), ('PreToolUse', {'exit_code': 0}, 'unknown'),
                      ('PostToolUse', 'exit_code: 0', 'unknown'), ('PostToolUse', {'isError': True, 'exit_code': 0}, 'failure'),
                      ('PostToolUse', {'is_error': True}, 'failure'), ('PostToolUse', {'exit_code': 2}, 'failure'),
                      ('PostToolUse', {'exitCode': 0}, 'success'), ('PostToolUse', {'exit_code': False}, 'unknown'),
                      ('PostToolUse', {'exit_code': None, 'exitCode': 0}, 'unknown'),
                      ('PostToolUse', {'exit_code': '0'}, 'unknown'), ('PostToolUse', {'exit_code': 0.0}, 'unknown'),
                      ('PostToolUse', {'session_id': 0, 'isError': False}, 'running'),
                      ('PostToolUse', {'session_id': None}, 'unknown'), ('PostToolUse', {'is_error': False}, 'success'),
                      ('PostToolUse', {'isError': 0}, 'unknown'), ('PostToolUse', {'stdout': 'success'}, 'unknown'),
                      ('PostToolUse', {'exit_code': 0, 'session_id': 'x'}, 'success')]
            for event, response, expected in checks:
                assert f(event, response) == expected, repr((event, response))
        return True, []
    except Exception as exc:
        return False, [type(exc).__name__ + ': ' + str(exc)[:180]]


def run_one(executable, runtime, profile, case, trial, directory, timeout):
    provider, model, effort = PROFILES[profile]
    prompt = ('This is an isolated synthetic assessment. Use no tools, files, network, or delegation. '
              'All necessary information is in this message. Return ONLY a JSON object with code (string) and findings (array of strings). '
              'For implementation tasks findings must be empty. Do not include markdown fences.\n\n' + CASES[case])
    fixture = hashlib.sha256(prompt.encode()).hexdigest()
    item = {'case': case, 'trial': trial, 'profile': profile, 'provider': provider, 'model': model,
            'effort': effort, 'runtime': runtime, 'harness': HARNESS, 'fixture': fixture,
            'accepted': False, 'violations': [], 'retries': 0, 'cost_usd': None, 'credits': None}
    directory.mkdir()
    save(directory / 'prompt.json', {'prompt': prompt, 'schema': SCHEMA})
    schema = directory / 'schema.json'; save(schema, SCHEMA)
    if provider == 'codex':
        cmd = [executable, '--no-daemon', 'exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check',
               '-s', 'read-only', '-m', model, '-c', f'model_reasoning_effort="{effort}"',
               '--json', '--output-schema', str(schema), '-C', str(directory), '-']
    else:
        cmd = [executable, '--print', '--safe-mode', '--no-session-persistence', '--tools', '',
               '--permission-mode', 'dontAsk', '--model', model, '--effort', effort,
               '--output-format', 'json', '--max-budget-usd', '3']
    start = time.monotonic()
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace',
                           cwd=directory, timeout=timeout)
        item['exit_code'] = p.returncode
        rows = []
        for line in p.stdout.splitlines():
            try: rows.append(json.loads(line))
            except ValueError: pass
        usage = native_usage(provider, rows)
        item.update({k: v for k, v in usage.items() if k != 'model'})
        item['resolved_model'] = usage.get('model')
        if provider == 'codex':
            messages = [r['item']['text'] for r in rows if r.get('type') == 'item.completed' and r.get('item', {}).get('type') == 'agent_message']
            tools_used = [r for r in rows if r.get('type') == 'item.started' and r.get('item', {}).get('type') in ('command_execution', 'mcp_tool_call', 'web_search', 'file_change')]
            if tools_used: item['violations'].append('tool used in no-tools assessment')
            final = messages[-1] if messages else ''
        else:
            results = [r for r in rows if r.get('type') == 'result']
            final = results[-1].get('result', '') if results else ''
        if p.returncode:
            item['failure'] = 'native CLI failed; no transcript retained'
            # Only classify known operational errors, never save raw stderr.
            low = (p.stdout + p.stderr).lower()
            for label, terms in [('authentication', ['not logged in', 'authentication', 'invalid api key', '/login']),
                                 ('unavailable-model', ['not supported', 'model not found', 'does not exist']),
                                 ('usage-limit', ['usage limit', 'rate limit', 'quota']), ('network', ['connection', 'network', 'timed out'])]:
                if any(t in low for t in terms): item['failure'] = label; break
        else:
            cleaned = final.strip()
            if cleaned.startswith('```'):
                cleaned = '\n'.join(cleaned.splitlines()[1:-1])
            try:
                artifact = json.loads(cleaned)
                save(directory / 'artifact.json', artifact)
                # Grade in a separate process to bound infinite loops/recursion.
                g = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), 'grade', case, str(directory / 'artifact.json')],
                                   capture_output=True, text=True, timeout=5)
                passed, failures = json.loads(g.stdout)
                item['accepted'] = passed and not item['violations']
                item['grade_failures'] = failures
            except (ValueError, subprocess.TimeoutExpired):
                item['grade_failures'] = ['invalid JSON artifact or grader timeout']
    except subprocess.TimeoutExpired:
        item['failure'] = 'native CLI timeout; usage unknown'
    finally:
        item['seconds'] = round(time.monotonic() - start, 3)
        item['evidence'] = str(directory / 'result.json')
        save(directory / 'result.json', item)
    return item


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'grade':
        print(json.dumps(grade(sys.argv[2], json.loads(Path(sys.argv[3]).read_text(encoding='utf-8')))))
        return
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--codex', required=True); p.add_argument('--claude', required=True)
    p.add_argument('--max-runs', type=int, required=True, choices=range(1, 25))
    p.add_argument('--profiles', nargs='+', choices=list(PROFILES), default=list(PROFILES))
    p.add_argument('--timeout', type=int, default=180)
    a = p.parse_args()
    a.output = a.output.resolve(); a.output.mkdir(parents=True, exist_ok=True)
    ledger = a.output / 'launches.json'
    launches = json.loads(ledger.read_text()) if ledger.exists() else []
    versions = {provider: subprocess.check_output([exe, '--version'], text=True).strip()
                for provider, exe in [('codex', a.codex), ('claude', a.claude)]}
    # At most two isolated native invocations concurrently. No agent may delegate.
    for case, trial in TRIALS:
        work = []
        for profile in a.profiles:
            key = f'{profile}-{case}-{trial}'
            if any(x['id'] == key for x in launches): continue
            # Avoid repeated calls when a provider/profile has an operational failure.
            prior = list(a.output.glob(profile + '-*/result.json'))
            if any(json.loads(f.read_text()).get('failure') for f in prior): continue
            if len(launches) >= a.max_runs: break
            launches.append({'id': key, 'at': time.time()}); save(ledger, launches)
            provider = PROFILES[profile][0]
            work.append((getattr(a, provider), versions[provider], profile, case, trial, a.output / key, a.timeout))
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_one, *args) for args in work]
            for f in as_completed(futures):
                r = f.result()
                print(json.dumps({k: r.get(k) for k in ('profile', 'case', 'trial', 'accepted', 'seconds', 'failure', 'grade_failures', 'input_tokens', 'output_tokens', 'cost_usd')}), flush=True)
    rows = [json.loads(f.read_text()) for f in sorted(a.output.glob('*/result.json'))]
    save(a.output / 'results.json', rows)
    summary = {}
    for profile in a.profiles:
        group = [r for r in rows if r['profile'] == profile]
        costs = [r['cost_usd'] for r in group]
        summary[profile] = {'runs': len(group), 'accepted': sum(r['accepted'] for r in group),
                            'median_seconds': statistics.median(r['seconds'] for r in group) if group else None,
                            'total_cost_usd': sum(costs) if group and all(c is not None for c in costs) else None}
    save(a.output / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
