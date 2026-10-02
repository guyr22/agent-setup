"""Command interface for the engineering configuration and local project evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib
import uuid
import englib as lib
import configure
import projects

def output(value):
    print(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False))

def doctor():
    errors = []
    skills = list((lib.ROOT / 'skills').glob('eng-*/SKILL.md'))
    for p in skills:
        content = p.read_text(encoding='utf-8')
        if not content.startswith(f'---\nname: {p.parent.name}\ndescription: '):
            errors.append('Invalid skill frontmatter: ' + str(p))
    manifest = lib.read_json(lib.STATE / 'deployment.json')
    if manifest:
        for f in manifest['files']:
            p = configure.checked_target(Path(manifest['home']), f['path'])
            if not p.exists() or lib.digest(p.read_bytes()) != f['after_hash']:
                errors.append('Installed drift: ' + f['path'])
    return {'version': lib.POLICY['version'], 'skills': len(skills), 'agents': len(lib.read_json(lib.ROOT / 'roles.json')),
            'installed': bool(manifest), 'errors': errors,
            'hook_trust': 'Not asserted by this tool. Review /hooks in the native clients after installation or hook changes.',
            'behavioral_evaluation': 'Run paired trials and score outcomes; static checks alone do not prove agent behavior.'}

def task_command(a):
    task = lib.get_task(a.session)
    if a.action == 'start':
        if task and task.get('status') == 'active':
            raise ValueError('This session already owns an active task; checkpoint or finish it first.')
        root = lib.writable(a.root)
        task = {'id': uuid.uuid4().hex[:12], 'root': str(root), 'mode': a.mode,
                'objective': a.objective, 'write_roots': [str(lib.writable(p)) for p in (a.write_root or [root])],
                'status': 'active', 'created': time.time(), 'checkpoint': {}, 'receipts': []}
        lib.put_task(a.session, task)
        return task
    if not task:
        raise ValueError('No task is registered for that session.')
    if a.action == 'checkpoint':
        checkpoint = lib.read_json(a.file)
        if not isinstance(checkpoint, dict) or not {'completed', 'next', 'decisions'} <= checkpoint.keys():
            raise ValueError('Checkpoint JSON requires completed, next, decisions; add references and blockers as needed.')
        task['checkpoint'] = checkpoint
        lib.put_task(a.session, task)
    elif a.action == 'finish':
        evidence = evidence_status(task)
        if not evidence['all_current_passed'] and not a.reason:
            raise ValueError('Verification is missing, failed, or stale; provide an honest --reason for the limitation.')
        task.update(status='complete', finished=time.time(), completion_reason=a.reason or 'Current passing command receipts', evidence=evidence)
        lib.put_task(a.session, task)
    return task

def evidence_status(task):
    rows = []
    for r in task['receipts']:
        try:
            current = lib.snapshot(r['root'])
            valid = current['digest'] == r['after']['digest'] and current['head'] == r['after']['head']
        except (ValueError, OSError, subprocess.TimeoutExpired):
            valid = False
        rows.append({'label': r['label'], 'exit_code': r['exit_code'], 'current': valid,
                     'unchanged_during_check': r['before'] == r['after']})
    return {'checks': rows, 'all_current_passed': bool(rows) and all(r['current'] and r['exit_code'] == 0 and r['unchanged_during_check'] for r in rows)}

def verify(a):
    if not 1 <= a.timeout <= 3600:
        raise ValueError('Verification timeout must be between 1 and 3600 seconds.')
    task = lib.get_task(a.session)
    if not task or task['status'] != 'active':
        raise ValueError('Start a substantial task before recording command receipts.')
    root = lib.writable(a.root or task['root'])
    if not any(lib.beneath(root, p) for p in task['write_roots']):
        raise ValueError('Verification root is outside this task.')
    argv = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not argv:
        raise ValueError('Supply a command after --; no shell string is evaluated implicitly.')
    before = lib.snapshot(root)
    started = time.monotonic()
    try:
        code = subprocess.run(argv, cwd=root, timeout=a.timeout).returncode
    except subprocess.TimeoutExpired:
        code = 124
    after = lib.snapshot(root)
    receipt = {'label': a.label, 'root': str(root), 'argv_hash': lib.digest(json.dumps(argv).encode()),
               'before': before, 'after': after, 'exit_code': code,
               'seconds': round(time.monotonic() - started, 3), 'at': time.time()}
    task['receipts'] = [r for r in task['receipts'] if not (r['label'] == a.label and r['root'] == str(root))] + [receipt]
    lib.put_task(a.session, task)
    output(receipt)
    return code

def proposal(a):
    value = lib.read_json(a.file)
    required = {'title', 'observations', 'hypothesis', 'change', 'risks', 'evaluation', 'rollback'}
    if not isinstance(value, dict) or not required <= value.keys():
        raise ValueError('Proposal requires ' + ', '.join(sorted(required)))
    value.update(id=uuid.uuid4().hex[:12], status='proposed', created=time.time(), activation='requires user review')
    dest = lib.STATE / 'proposals' / (value['id'] + '.json')
    lib.save_json(dest, value)
    return {'proposal': str(dest), 'active_config_changed': False}

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='group', required=True)
    sub.add_parser('doctor')
    c = sub.add_parser('config').add_subparsers(dest='action', required=True)
    c.add_parser('build')
    for action in ('diff', 'apply', 'rollback'):
        q = c.add_parser(action)
        q.add_argument('file', type=Path)
        if action != 'diff':
            q.add_argument('--approval-ref', required=True)
    s = sub.add_parser('project').add_subparsers(dest='action', required=True)
    q = s.add_parser('inspect'); q.add_argument('root')
    q = s.add_parser('draft'); q.add_argument('root'); q.add_argument('--spec', required=True)
    q = s.add_parser('apply'); q.add_argument('file')
    t = sub.add_parser('task').add_subparsers(dest='action', required=True)
    for action in ('start', 'show', 'checkpoint', 'finish', 'evidence'):
        q = t.add_parser(action); q.add_argument('--session', required=True)
        if action == 'start':
            q.add_argument('--root', required=True); q.add_argument('--objective', required=True)
            q.add_argument('--mode', choices=['planned', 'program'], default='planned'); q.add_argument('--write-root', action='append')
        if action == 'checkpoint': q.add_argument('--file', required=True)
        if action == 'finish': q.add_argument('--reason')
    v = sub.add_parser('verify'); v.add_argument('--session', required=True); v.add_argument('--root')
    v.add_argument('--label', required=True); v.add_argument('--timeout', type=int, default=lib.POLICY['verification_timeout_seconds'])
    v.add_argument('command', nargs=argparse.REMAINDER)
    f = sub.add_parser('knowledge').add_subparsers(dest='action', required=True)
    q = f.add_parser('add'); q.add_argument('root'); q.add_argument('--file', required=True)
    q = f.add_parser('query'); q.add_argument('root'); q.add_argument('--history', action='store_true')
    q = sub.add_parser('propose'); q.add_argument('file')
    q = sub.add_parser('observations'); q.add_argument('--root', required=True)
    return p

def main():
    # Stable machine-readable output on Windows, including non-Latin project paths.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    a = parser().parse_args()
    if a.group == 'doctor':
        result = doctor(); output(result); return bool(result['errors'])
    if a.group == 'config':
        if a.action == 'build': result = str(configure.build())
        elif a.action == 'diff': result = configure.deployment_diff(a.file)
        elif a.action == 'apply': result = configure.apply(a.file, a.approval_ref)
        else: result = configure.rollback(a.file, a.approval_ref)
    elif a.group == 'project':
        if a.action == 'inspect': result = projects.inspect(a.root)
        elif a.action == 'draft': result = projects.draft(a.root, lib.read_json(a.spec))
        else: result = projects.apply(a.file)
    elif a.group == 'task':
        if a.action == 'evidence':
            task = lib.get_task(a.session)
            if not task: raise ValueError('No registered task')
            result = evidence_status(task)
        else: result = task_command(a)
    elif a.group == 'verify': return verify(a)
    elif a.group == 'knowledge':
        result = lib.fact_add(a.root, lib.read_json(a.file)) if a.action == 'add' else lib.facts(a.root, a.history)
    elif a.group == 'propose': result = proposal(a)
    else:
        with lib.db() as c:
            result = c.execute('SELECT event,tool,outcome,COUNT(*) FROM events WHERE scope=? GROUP BY event,tool,outcome', (lib.scope_id(a.root),)).fetchall()
    output(result)
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)
