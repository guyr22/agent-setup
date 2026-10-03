import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import unittest
from unittest.mock import patch

import test_runtime
import englib as lib
import engctl
import configure
import hooks
from telemetry import hook_outcome, native_usage, validate_metrics
from score import score


class ImprovementTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    tearDown = test_runtime.RuntimeTests.tearDown
    repo = test_runtime.RuntimeTests.repo

    def task(self):
        p = self.repo()
        task = {'id': 'task-one', 'root': str(p), 'status': 'active', 'write_roots': [str(p)],
                'checkpoint': {}, 'receipts': []}
        lib.put_task('fixture', task)
        return task

    def test_codex_native_patch_and_crlf_move_guard(self):
        for command in [f'*** Add File: {self.keep / "x"}\n+x',
                        f'*** Update File: x\r\n*** Move to: {self.keep / "y"}\r\n']:
            r = hooks.respond({'hook_event_name': 'PreToolUse', 'cwd': str(self.root), 'session_id': 'x',
                               'tool_name': 'apply_patch', 'tool_input': {'command': command}})
            self.assertEqual(r['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_protected_path_survives_database_failure(self):
        with patch.object(hooks, 'get_task', side_effect=lib.StateUnavailable('fixture')):
            r = hooks.respond({'hook_event_name': 'PreToolUse', 'cwd': str(self.root), 'session_id': 'x',
                               'tool_name': 'Write', 'tool_input': {'file_path': str(self.keep / 'x')}})
            self.assertEqual(r['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_native_outcomes_and_spoofed_stdout(self):
        def outcome(response, **kw):
            return hook_outcome(dict(hook_event_name='PostToolUse', tool_response=response, **kw))[0]
        self.assertEqual(outcome({'exit_code': 1}), 'failure')
        self.assertEqual(outcome(json.dumps({'exit_code': 0})), 'success')
        self.assertEqual(outcome({'session_id': 9}), 'running')
        self.assertEqual(outcome({'filePath': 'x'}, permission_mode='default'), 'success')
        self.assertEqual(outcome({'filePath': 'x'}, turn_id='t'), 'unknown')
        self.assertEqual(outcome('Chunk ID: x\nWall time: 1\nProcess exited with code 2\nOutput:\nsecret'), 'failure')
        self.assertEqual(outcome('Chunk ID: x\nWall time: 1\nOutput:\nProcess exited with code 0'), 'unknown')
        self.assertEqual(outcome('plain output claims success'), 'unknown')

    def test_session_context_survives_telemetry_outage(self):
        with patch.object(hooks, 'event', side_effect=lib.StateUnavailable('fixture')):
            r = hooks.respond({'hook_event_name': 'SessionStart', 'cwd': str(self.root), 'session_id': 'x'})
        self.assertIn('additionalContext', r['hookSpecificOutput'])

    def test_concurrent_checks_preserve_failure_and_checkpoint(self):
        task = self.task()
        barrier = threading.Barrier(2)
        original_snapshot = lib.snapshot
        def run(argv, **kwargs):
            barrier.wait(timeout=5)
            lib.update_task('fixture', lambda current: dict(current, checkpoint={'kept': True}))
            return subprocess.CompletedProcess(argv, 1 if argv[0] == 'unit' else 0)
        snap = original_snapshot(task['root'])
        with patch.object(engctl.subprocess, 'run', side_effect=run), patch.object(lib, 'snapshot', return_value=snap), patch.object(engctl, 'output'):
            def check(label):
                return engctl.verify(argparse.Namespace(session='fixture', root=None, timeout=10, label=label, command=[label]))
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(check, ['unit', 'types'])), [0, 1])
        saved = lib.get_task('fixture')
        self.assertEqual({r['label'] for r in saved['receipts']}, {'unit', 'types'})
        self.assertEqual(saved['checkpoint'], {'kept': True})
        self.assertFalse(saved['running_checks'])
        self.assertFalse(engctl.evidence_status(saved)['all_current_passed'])

    def test_finish_refuses_running_check(self):
        task = self.task()
        lib.update_task('fixture', lambda current: dict(current, running_checks={'one': {'label': 'test'}}))
        with self.assertRaisesRegex(ValueError, 'still running'):
            engctl.task_command(argparse.Namespace(action='finish', session='fixture', reason='manual'))

    def test_interrupted_check_is_visible(self):
        self.task()
        with patch.object(lib, 'snapshot', side_effect=ValueError('snapshot failed')):
            with self.assertRaises(ValueError):
                engctl.verify(argparse.Namespace(session='fixture', root=None, timeout=10, label='test', command=['unused']))
        task = lib.get_task('fixture')
        self.assertTrue(next(iter(task['running_checks'].values()))['interrupted'])
        self.assertEqual(task['receipts'], [])

    def test_snapshot_once_per_root_at_delivery(self):
        task = self.task(); snap = lib.snapshot(task['root'])
        task['receipts'] = [dict(label=n, root=task['root'], before=snap, after=snap, exit_code=0) for n in ['a', 'b']]
        with patch.object(lib, 'snapshot', return_value=snap) as check:
            self.assertTrue(engctl.evidence_status(task)['all_current_passed'])
            self.assertEqual(check.call_count, 1)

    def test_alternate_build_is_isolated(self):
        home = self.root / 'home'
        staging = lib.ROOT / 'build/deployment.json'
        before = staging.read_bytes() if staging.exists() else None
        with self.assertRaisesRegex(ValueError, 'explicit'):
            configure.build(home)
        destination = self.root / 'staging.json'
        self.assertEqual(configure.build(home, destination), destination)
        self.assertEqual(staging.read_bytes() if staging.exists() else None, before)

    def test_owned_drift_ignores_preferences_and_trust(self):
        expected = b'[agents]\nenabled=true\nmax_concurrent_threads_per_session=3\n'
        row = {'path': '.codex/config.toml', 'after': base64.b64encode(expected).decode()}
        added = b'model="user-choice"\n[hooks.state]\ntrusted_hash="native"\n' + expected
        self.assertTrue(configure.matches_owned(row, added))
        self.assertFalse(configure.matches_owned(row, added.replace(b'=3', b'=9')))

    def test_native_trust_inside_managed_markers_survives_build(self):
        old = ('model="user-choice"\n' + configure.BEGIN + '\n[agents]\nenabled = true\n'
               'max_concurrent_threads_per_session = 3\n\n[hooks.state.native]\ntrusted_hash="native-value"\n'
               + configure.END + '\n')
        self.assertEqual(configure.merge_toml(old), old)
        changed = old.replace('max_concurrent_threads_per_session = 3', 'max_concurrent_threads_per_session = 9')
        self.assertEqual(configure.merge_toml(changed), old)
        missing = old.replace('enabled = true\n', '')
        rendered = configure.merge_toml(missing)
        self.assertIn('trusted_hash="native-value"', rendered)
        self.assertEqual(engctl.tomllib.loads(rendered)['agents']['enabled'], True)

    def test_owned_hooks_detect_removal_preserve_unrelated(self):
        generated = configure.merge_hooks({}, configure.hook_entries('codex'))
        row = {'path': '.codex/hooks.json', 'after': base64.b64encode(json.dumps(generated).encode()).decode()}
        changed = json.loads(json.dumps(generated))
        changed['hooks']['Stop'].append({'hooks': [{'type': 'command', 'command': 'other'}]})
        self.assertTrue(configure.matches_owned(row, json.dumps(changed).encode()))
        changed['hooks']['Stop'].pop(0)
        self.assertFalse(configure.matches_owned(row, json.dumps(changed).encode()))
        self.assertFalse(configure.matches_owned(row, b'{"hooks":{"Stop":null}}'))

    def test_source_change_invalidates_built_plan(self):
        home = self.root / 'home'; plan = configure.build(home, self.root / 'plan.json')
        with patch.object(configure, 'source_hashes', return_value={'changed': 'hash'}):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                configure.apply(plan, 'fixture')
        self.assertFalse((home / '.codex').exists())

    def test_state_migration_preserves_legacy_and_closes_handles(self):
        lib.STATE.mkdir(parents=True)
        old = lib.STATE / 'runtime.sqlite3'
        c = sqlite3.connect(old)
        c.execute('CREATE TABLE tasks(session TEXT PRIMARY KEY,root TEXT,body TEXT)')
        c.execute('INSERT INTO tasks VALUES (?,?,?)', ('old', str(self.root), json.dumps({'root': str(self.root), 'status': 'active'})))
        c.commit(); c.close()
        with self.assertRaisesRegex(lib.StateUnavailable, 'Legacy'):
            lib.get_task('old')
        lib.migrate_state()
        self.assertEqual(lib.get_task('old')['status'], 'active')
        self.assertTrue(old.exists())
        with self.assertRaises(ValueError): lib.migrate_state()
        path = lib.runtime_dir() / 'runtime.sqlite3'
        moved = path.with_suffix('.check'); path.rename(moved); moved.rename(path)

    def test_database_failure_does_not_create_fallback(self):
        with patch.object(lib.sqlite3, 'connect', side_effect=sqlite3.OperationalError('fixture')):
            with self.assertRaisesRegex(lib.StateUnavailable, 'No fallback'):
                lib.get_task('missing')

    def test_doctor_distinguishes_readable_from_writable_state(self):
        self.task()
        with patch.object(engctl, 'probe_state_write', side_effect=PermissionError('fixture')):
            result = engctl.doctor()
        self.assertTrue(result['state']['available'])
        self.assertFalse(result['state']['writable'])
        self.assertTrue(any('host access' in w for w in result['warnings']))

    def test_permission_probe_does_not_retry_denied_access(self):
        with patch.object(Path, 'open', side_effect=PermissionError('fixture')) as opening:
            with self.assertRaises(PermissionError):
                engctl.probe_state_write()
        self.assertEqual(opening.call_count, 1)

    def test_native_usage_retains_only_numbers(self):
        usage = native_usage('codex', [{'type': 'item.completed', 'item': {'text': 'SECRET'}},
                                     {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 3, 'output_tokens': 2}}])
        self.assertEqual(usage['input_tokens'], 10)
        self.assertIsNone(usage['cost_usd'])
        self.assertNotIn('SECRET', json.dumps(usage))
        self.assertEqual(native_usage('claude', [{'type': 'result', 'usage': {'input_tokens': 2}, 'total_cost_usd': .01}])['cost_usd'], .01)
        self.assertEqual(native_usage('claude', [{'type': 'result', 'total_cost_usd': .01}, {'type': 'result', 'total_cost_usd': .02}])['cost_usd'], .03)
        self.assertIsNone(native_usage('claude', [{'type': 'result', 'total_cost_usd': .01}, {'type': 'result'}])['cost_usd'])
        with self.assertRaises(ValueError): validate_metrics({'transcript': 'secret'})
        with self.assertRaises(ValueError): validate_metrics({'cost_usd': -1})

    def test_effort_and_model_comparisons_are_controlled(self):
        row = {'case': 'contract', 'trial': 1, 'variant': 'baseline', 'fixture': 'hash', 'model': 'a',
               'runtime': 'v', 'accepted': True, 'violations': [], 'seconds': 3, 'cost_usd': None,
               'evidence': 'artifact', 'provider': 'codex', 'effort': 'high', 'harness': 'hash'}
        candidate = dict(row, variant='candidate', effort='medium')
        with self.assertRaises(ValueError): score([row, candidate])
        self.assertEqual(score([row, candidate], 'effort')['pairs'], 1)
        candidate['model'] = 'b'
        with self.assertRaises(ValueError): score([row, candidate], 'effort')
        result = score([row, candidate], 'model-policy')
        self.assertIsNone(result['candidate']['cost_per_accepted_task_usd'])
        candidate['accepted'] = False
        self.assertFalse(score([row, candidate], 'model-policy')['candidate_has_no_observed_quality_regression'])
        with self.assertRaises(ValueError): score([row, dict(candidate, seconds=float('nan'))], 'model-policy')

    def test_claude_roles_have_effort_and_evidence_contract(self):
        rendered = configure.render(self.root / 'home')
        reviewer = rendered['.claude/agents/eng-reviewer.md']
        self.assertIn('effort: "high"', reviewer)
        self.assertIn('lead must supply a saved diff', reviewer)
        self.assertIn('Read, Grep, Glob', reviewer)
