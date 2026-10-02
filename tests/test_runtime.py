import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import englib as lib
import configure
import engctl
import hooks
import projects
sys.path.insert(0, str(lib.ROOT / 'evals'))
from score import score


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = lib.ROOT / '.test-output' / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.original_state = lib.STATE
        self.original_protected = list(lib.POLICY['protected_roots'])
        lib.STATE = configure.STATE = projects.STATE = self.root / 'state'
        self.keep = self.root / 'KeepHQ'
        self.keep.mkdir()
        lib.POLICY['protected_roots'].append(str(self.keep))

    def tearDown(self):
        lib.STATE = configure.STATE = projects.STATE = self.original_state
        lib.POLICY['protected_roots'] = self.original_protected
        # Isolated artifacts intentionally retained for inspection; no recursive cleanup.

    def repo(self, name='repo'):
        p = self.root / name
        p.mkdir()
        subprocess.run(['git', 'init', '-q', str(p)], check=True)
        (p / 'code.txt').write_text('first', encoding='utf-8')
        return p

    def spec(self, kind='project'):
        return {'kind': kind, 'name': 'Fixture', 'summary': 'Fixture application', 'sources': [], 'commands': []}

    def test_protected_descendant_and_case(self):
        with self.assertRaises(ValueError): lib.atomic(self.keep / 'x', 'no')
        with self.assertRaises(ValueError): lib.atomic(self.keep / '..' / 'KeepHQ' / 'x', 'no')
        self.assertEqual(list(self.keep.iterdir()), [])

    def test_protected_junction(self):
        link = self.root / 'alias'
        if sys.platform == 'win32':
            r = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                 f"New-Item -ItemType Junction -Path '{link}' -Target '{self.keep}' | Out-Null"], capture_output=True)
            self.assertEqual(r.returncode, 0)
        else: link.symlink_to(self.keep, target_is_directory=True)
        with self.assertRaises(ValueError): lib.atomic(link / 'x', 'no')

    def test_snapshot_detects_untracked_and_deleted(self):
        p = self.repo(); first = lib.snapshot(p)
        (p / 'new.txt').write_text('new')
        self.assertNotEqual(first['digest'], lib.snapshot(p)['digest'])
        subprocess.run(['git', '-C', str(p), 'add', '.'], check=True)
        before = lib.snapshot(p)
        (p / 'code.txt').unlink()
        self.assertNotEqual(before['digest'], lib.snapshot(p)['digest'])

    def test_snapshot_rejects_non_git(self):
        with self.assertRaises(ValueError): lib.snapshot(self.root)

    def test_facts_scope_staleness_supersession(self):
        p = self.repo(); other = self.repo('other')
        fact = {'id': 'F1', 'claim': 'Fixture contains first', 'source': 'code.txt',
                'kind': 'verified-observation', 'verification': 'Read the file contents.'}
        lib.fact_add(p, fact)
        self.assertEqual(len(lib.facts(p)), 1)
        self.assertEqual(lib.facts(other), [])
        lib.fact_add(p, dict(fact, id='F2', supersedes='F1'))
        self.assertEqual([f['id'] for f in lib.facts(p)], ['F2'])
        self.assertEqual(len(lib.facts(p, True)), 2)
        (p / 'code.txt').write_text('changed')
        self.assertEqual(lib.facts(p), [])
        with self.assertRaises(ValueError): lib.fact_add(p, fact)

    def test_facts_reject_policy_escape_and_protected(self):
        p = self.repo()
        fact = {'id': 'F1', 'claim': 'claim', 'source': 'code.txt', 'kind': 'user-decision', 'verification': 'read'}
        with self.assertRaises(ValueError): lib.fact_add(p, fact)
        with self.assertRaises(ValueError): lib.fact_add(p, dict(fact, kind='verified-observation', source='../outside'))
        with self.assertRaises(ValueError): lib.fact_add(self.keep, fact)

    def test_hooks_metadata_not_content(self):
        data = {'hook_event_name': 'PostToolUse', 'cwd': str(self.root), 'session_id': 's',
                'tool_name': 'Bash', 'tool_input': {'command': 'SECRET-TEXT'},
                'tool_response': {'exit_code': 1, 'output': 'SECRET-TEXT'}}
        hooks.respond(data)
        with lib.db() as c:
            rows = c.execute('SELECT * FROM events').fetchall()
        self.assertNotIn('SECRET-TEXT', repr(rows))
        self.assertEqual(rows[0][-1], 'failure')

    def test_hooks_protected_edit_and_patch_move(self):
        for value in [{'file_path': str(self.keep / 'a')}, {'patch': f'*** Update File: a\n*** Move to: {self.keep / "b"}\n'}]:
            result = hooks.respond({'hook_event_name': 'PreToolUse', 'cwd': str(self.root), 'session_id': 's', 'tool_name': 'apply_patch', 'tool_input': value})
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_hook_scope_and_stop_do_not_loop(self):
        p = self.repo()
        lib.put_task('s', {'root': str(p), 'status': 'active', 'write_roots': [str(p)]})
        result = hooks.respond({'hook_event_name': 'PreToolUse', 'cwd': str(p), 'session_id': 's', 'tool_name': 'Write', 'tool_input': {'file_path': '../outside'}})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
        result = hooks.respond({'hook_event_name': 'Stop', 'cwd': str(p), 'session_id': 's'})
        self.assertNotIn('decision', result)
        self.assertEqual(hooks.respond({'hook_event_name': 'Interrupt', 'cwd': str(p), 'session_id': 's'}), {})

    def test_protected_hooks_no_database(self):
        hooks.respond({'hook_event_name': 'SessionStart', 'cwd': str(self.keep), 'session_id': 's'})
        self.assertFalse(lib.STATE.exists())

    def test_events_concurrent(self):
        lib.db().close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda n: lib.event(str(n), self.root, 'Stop'), range(24)))
        with lib.db() as c: count = c.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        self.assertEqual(count, 24)

    def test_project_preserves_existing_and_reuses_vault(self):
        p = self.repo(); (p / 'AGENTS.md').write_text('Original instructions\n')
        (p / 'VAULT.md').write_text('Existing facts\n')
        spec = self.spec(); spec['sources'] = [{'role': 'vault', 'path': 'VAULT.md'}]
        draft = projects.draft(p, spec)
        self.assertEqual((p / 'AGENTS.md').read_text(), 'Original instructions\n')
        projects.apply(draft)
        self.assertTrue((p / 'AGENTS.md').read_text().startswith('Original instructions'))
        self.assertEqual((p / 'VAULT.md').read_text(), 'Existing facts\n')
        self.assertEqual((p / 'CLAUDE.md').read_text(), '@AGENTS.md\n')
        with self.assertRaises(ValueError): projects.draft(p, spec)

    def test_project_drift_preflight(self):
        p = self.repo(); draft = projects.draft(p, self.spec())
        (p / 'AGENTS.md').write_text('Concurrent change')
        with self.assertRaises(ValueError): projects.apply(draft)
        self.assertFalse((p / '.agent/project.json').exists())

    def test_project_escape_and_missing_source(self):
        p = self.repo(); spec = self.spec()
        for path in ('../outside', 'missing.md'):
            spec['sources'] = [{'role': 'design', 'path': path}]
            with self.assertRaises(ValueError): projects.draft(p, spec)
        with self.assertRaises(ValueError): projects.draft(self.keep, self.spec())

    def test_workspace_no_parent_git(self):
        p = self.root / 'workspace'; p.mkdir()
        repo = p / 'service'; repo.mkdir(); subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        spec = self.spec('workspace'); spec['repositories'] = [{'path': 'service', 'role': 'api'}]
        draft = projects.draft(p, spec); projects.apply(draft)
        self.assertFalse((p / '.git').exists())
        self.assertEqual(json.loads((p / 'WORKSPACE.json').read_text())['repositories'][0]['revision'], 'unborn')

    def test_config_merge_preserves_preferences(self):
        old = {'theme': 'dark', 'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'existing'}]}]}}
        merged = configure.merge_hooks(old, configure.hook_entries('claude'))
        twice = configure.merge_hooks(merged, configure.hook_entries('claude'))
        self.assertEqual(merged, twice)
        self.assertEqual(merged['theme'], 'dark')
        self.assertEqual(len(merged['hooks']['Stop']), 2)
        toml = 'model = "existing"\n[features]\njs_repl = false\n'
        self.assertEqual(configure.merge_toml(configure.merge_toml(toml)), configure.merge_toml(toml))

    def test_config_apply_rollback_and_drift(self):
        home = self.root / 'home'; (home / '.claude').mkdir(parents=True)
        original = b'{"theme":"dark"}\n'; (home / '.claude/settings.json').write_bytes(original)
        plan = configure.build(home); release = configure.apply(plan, 'test fixture authorization')
        self.assertTrue((home / '.codex/skills/eng-project-setup/SKILL.md').exists())
        configure.rollback(release, 'test fixture rollback')
        self.assertFalse((home / '.codex/AGENTS.md').exists())
        self.assertEqual((home / '.claude/settings.json').read_bytes(), original)
        plan = configure.build(home)
        (home / '.claude/settings.json').write_text('{"theme":"light"}')
        with self.assertRaises(ValueError): configure.apply(plan, 'test fixture')
        self.assertFalse((home / '.codex/AGENTS.md').exists())

    def test_config_unmanaged_collision(self):
        home = self.root / 'home'; (home / '.codex').mkdir(parents=True)
        (home / '.codex/AGENTS.md').write_text('user-owned instructions')
        with self.assertRaises(ValueError): configure.build(home)
        with self.assertRaises(ValueError): configure.checked_target(home, '../KeepHQ/file')

    def test_evidence_currency(self):
        p = self.repo(); before = lib.snapshot(p)
        task = {'receipts': [{'label': 'test', 'root': str(p), 'before': before, 'after': before, 'exit_code': 0}]}
        self.assertTrue(engctl.evidence_status(task)['all_current_passed'])
        (p / 'code.txt').write_text('changed')
        self.assertFalse(engctl.evidence_status(task)['all_current_passed'])
        self.assertFalse(engctl.evidence_status({'receipts': []})['all_current_passed'])

    def test_proposal_does_not_activate(self):
        p = self.root / 'proposal.json'
        lib.save_json(p, {k: 'fixture' for k in ('title', 'observations', 'hypothesis', 'change', 'risks', 'evaluation', 'rollback')})
        result = engctl.proposal(argparse.Namespace(file=p))
        self.assertFalse(result['active_config_changed'])
        self.assertEqual(lib.read_json(result['proposal'])['status'], 'proposed')

    def test_hook_command_runs_in_powershell(self):
        command = configure.hook_entries('codex')['SessionStart'][0]['hooks'][0]['command']
        payload = {'hook_event_name': 'SessionStart', 'cwd': str(self.keep), 'session_id': 'fixture-native-shell'}
        # KeepHQ no-op prevents fixture process from writing global state.
        payload['cwd'] = lib.POLICY['protected_roots'][0]
        r = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), '')
        self.assertEqual(r.stderr.strip(), '')

    def test_invalid_hook_input_fails_open(self):
        r = subprocess.run([sys.executable, '-B', str(lib.ROOT / 'hooks.py')], input='{broken',
                           capture_output=True, text=True, timeout=5)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, '')
        self.assertNotIn('{broken', r.stderr)

    def test_paired_evaluation_requires_matching_trials(self):
        row = {'case': 'local', 'trial': 1, 'variant': 'baseline', 'fixture': 'hash', 'model': 'same',
               'runtime': 'same', 'accepted': True, 'violations': [], 'seconds': 3, 'cost_usd': None, 'evidence': 'artifact'}
        with self.assertRaises(ValueError): score([row])
        with self.assertRaises(ValueError): score([row, dict(row, variant='candidate', fixture='different')])
        result = score([row, dict(row, variant='candidate', seconds=2)])
        self.assertIsNone(result['candidate']['total_cost_usd'])
        self.assertEqual(result['candidate']['median_seconds'], 2)

    def test_cli_unicode_project_path(self):
        p = self.root / '\u05e4\u05e8\u05d5\u05d9\u05e7\u05d8'; p.mkdir()
        r = subprocess.run([sys.executable, '-B', str(lib.ROOT / 'engctl.py'), 'project', 'inspect', str(p)],
                           capture_output=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.decode('utf-8'))['root'], str(p))


if __name__ == '__main__': unittest.main()
