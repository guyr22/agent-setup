import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('benchmark', Path(__file__).resolve().parents[1] / 'evals/benchmark.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkTests(unittest.TestCase):
    def test_grader_accepts_contract_and_rejects_truthiness(self):
        code = '''def outcome(event, response):
    if event == 'PostToolUseFailure': return 'failure'
    if event != 'PostToolUse' or not isinstance(response, dict): return 'unknown'
    if response.get('isError') is True or response.get('is_error') is True: return 'failure'
    code = response.get('exit_code', response.get('exitCode'))
    if type(code) is int: return 'success' if code == 0 else 'failure'
    if response.get('session_id') is not None: return 'running'
    if response.get('isError') is False or response.get('is_error') is False: return 'success'
    return 'unknown'
'''
        self.assertTrue(benchmark.grade('outcome', {'code': code, 'findings': []})[0])
        wrong = code.replace('type(code) is int', 'isinstance(code, int)')
        self.assertFalse(benchmark.grade('outcome', {'code': wrong, 'findings': []})[0])

    def test_grader_checks_aliasing_and_clean_review(self):
        code = '''def clone(v):
    if isinstance(v, dict): return {k: clone(x) for k, x in v.items()}
    if isinstance(v, list): return [clone(x) for x in v]
    return v
def merge_settings(base, override):
    r = clone(base)
    for k, v in override.items():
        r[k] = merge_settings(base[k], v) if k in base and isinstance(base[k], dict) and isinstance(v, dict) else clone(v)
    return r
'''
        self.assertTrue(benchmark.grade('merge', {'code': code, 'findings': []})[0])
        self.assertFalse(benchmark.grade('merge', {'code': code.replace('r = clone(base)', 'r = dict(base)'), 'findings': []})[0])
        self.assertTrue(benchmark.grade('clean-review', {'code': '', 'findings': []})[0])
        self.assertFalse(benchmark.grade('clean-review', {'code': '', 'findings': ['Invented bug']})[0])

    def test_grader_rejects_external_actions(self):
        self.assertFalse(benchmark.grade('merge', {'code': 'import os', 'findings': []})[0])
        self.assertFalse(benchmark.grade('merge', {'code': 'x = (1).__class__', 'findings': []})[0])
