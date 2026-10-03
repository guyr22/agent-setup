"""Shared local runtime; stdlib only. No network, credentials, or transcript access."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
from contextlib import contextmanager, closing

ROOT = Path(__file__).resolve().parent
POLICY = json.loads((ROOT / 'policy.json').read_text(encoding='utf-8'))
LOCAL_PATH = Path(os.environ.get('ENG_SETUP_LOCAL_CONFIG') or ROOT / 'local.json').expanduser()
if not LOCAL_PATH.is_absolute():
    raise ValueError('ENG_SETUP_LOCAL_CONFIG must be an absolute path so hooks cannot select project-local policy.')
LOCAL = json.loads(LOCAL_PATH.read_text(encoding='utf-8-sig')) if LOCAL_PATH.exists() else {}
if not isinstance(LOCAL, dict) or set(LOCAL) - {'protected_roots', 'profiles'}:
    raise ValueError('local.json supports only protected_roots and profiles.')
if 'protected_roots' in LOCAL:
    roots = LOCAL['protected_roots']
    if not isinstance(roots, list) or not all(isinstance(p, str) and Path(p).expanduser().is_absolute() for p in roots):
        raise ValueError('protected_roots must be absolute paths.')
    POLICY['protected_roots'] = [str(Path(p).expanduser().resolve()) for p in roots]

STATE = ROOT / 'state'

def canonical(path):
    return Path(path).expanduser().resolve()

def beneath(path, parent):
    return canonical(path).is_relative_to(canonical(parent))

def protected(path):
    return any(beneath(path, p) for p in POLICY['protected_roots'])

def writable(path):
    p = canonical(path)
    if protected(p):
        raise ValueError(f'Protected by user instruction: {p}')
    return p

def digest(data):
    return hashlib.sha256(data).hexdigest()

def scope_id(path):
    return digest(os.path.normcase(str(canonical(path))).encode())[:24]

def read_json(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8-sig')) if Path(path).exists() else default

def atomic(path, data):
    path = writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data if isinstance(data, bytes) else data.encode('utf-8')
    fd, temp = tempfile.mkstemp(prefix='.eng-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def save_json(path, value):
    atomic(path, json.dumps(value, indent=2, ensure_ascii=False) + '\n')

class StateUnavailable(RuntimeError):
    """Actionable state-access failure, without exposing stored content."""


def runtime_dir():
    return writable(os.environ.get('ENG_SETUP_STATE_DIR') or STATE / 'runtime')


@contextmanager
def db():
    # Runtime metadata is separate from deployment backups. Do not change ACLs,
    # silently fork state, or toggle the shared journal mode on every hook call.
    c = None
    try:
        directory = runtime_dir()
        if (STATE / 'runtime.sqlite3').exists() and not (directory / 'runtime.sqlite3').exists():
            raise StateUnavailable('Legacy state exists. Run engctl state migrate with host access before using this runtime; no empty replacement was created.')
        directory.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(directory / 'runtime.sqlite3', timeout=1.0)
        c.executescript('''
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY, at REAL, scope TEXT, session TEXT, event TEXT, tool TEXT, outcome TEXT);
    CREATE TABLE IF NOT EXISTS event_details (
      event_id INTEGER PRIMARY KEY, provider TEXT, duration_ms REAL);
    CREATE TABLE IF NOT EXISTS tasks (
      session TEXT PRIMARY KEY, root TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS facts (
      scope TEXT, id TEXT, body TEXT, PRIMARY KEY(scope,id));
    ''')
        yield c
        c.commit()
    except (sqlite3.Error, OSError) as exc:
        if c:
            c.rollback()
        raise StateUnavailable(
            'Runtime state is unavailable. Check access to the metadata directory '
            f'{runtime_dir()}; use the same ENG_SETUP_STATE_DIR for CLI and hooks. '
            'No fallback database was created. Native permissions remain authoritative.'
        ) from exc
    finally:
        if c:
            c.close()


def migrate_state():
    """Explicit one-time copy; never replace an existing metadata database."""
    source = STATE / 'runtime.sqlite3'
    target = runtime_dir() / 'runtime.sqlite3'
    if target.exists():
        raise ValueError('Runtime database already exists; refusing to replace it.')
    if not source.is_file():
        raise ValueError('No legacy runtime database exists.')
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.migrating')
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as old:
            with closing(sqlite3.connect(temp)) as new:
                old.backup(new)
                new.execute('PRAGMA journal_mode=DELETE')
        os.replace(temp, target)
    except Exception:
        if temp.exists():
            temp.unlink()
        raise
    return {'source': str(source), 'target': str(target), 'legacy_preserved': True}

def git(root, *args, timeout=10):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError('Git command failed: ' + ' '.join(args[:2]))
    return result.stdout

def snapshot(root):
    """Tracked and nonignored untracked content; no command output stored."""
    root = canonical(root)
    try:
        top = canonical(git(root, 'rev-parse', '--show-toplevel').decode().strip())
        if top != root:
            raise ValueError('Use the exact repository root for verification receipts.')
    except (ValueError, FileNotFoundError):
        raise ValueError('Verification receipts require a Git repository; report manual evidence for other folders.')
    names = sorted(set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')) - {b''})
    if len(names) > POLICY['max_snapshot_files']:
        raise ValueError('Snapshot file budget exceeded; use a narrower repository root.')
    h = hashlib.sha256()
    total = 0
    for name in names:
        relative = os.fsdecode(name)
        path = root / relative
        h.update(name + b'\0')
        if path.is_symlink():
            h.update(b'LINK:' + os.fsencode(os.readlink(path)))
            if not beneath(path, root) or not path.is_file():
                raise ValueError('Snapshot cannot certify an external or directory symlink; use explicit manual evidence.')
            total += path.stat().st_size
            if total > POLICY['max_snapshot_bytes']:
                raise ValueError('Snapshot byte budget exceeded; evidence was not recorded.')
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
        elif not path.exists():
            h.update(b'MISSING')
        elif path.is_file():
            if not beneath(path, root):
                raise ValueError('Snapshot path escapes repository through a junction.')
            total += path.stat().st_size
            if total > POLICY['max_snapshot_bytes']:
                raise ValueError('Snapshot byte budget exceeded; evidence was not recorded.')
            h.update(str(path.stat().st_mode & 0o111).encode())
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(chunk)
        elif path.is_dir():
            h.update(snapshot(path)['digest'].encode())
        h.update(b'\0')
    try:
        head = git(root, 'rev-parse', 'HEAD').decode().strip()
    except ValueError:
        head = 'unborn'
    return {'digest': h.hexdigest(), 'head': head, 'files': len(names), 'bytes': total,
            'coverage': 'tracked + nonignored untracked; ignored dependencies and external services excluded'}

def get_task(session):
    with db() as c:
        row = c.execute('SELECT body FROM tasks WHERE session=?', (session,)).fetchone()
    return json.loads(row[0]) if row else None

def put_task(session, task):
    writable(task['root'])
    with db() as c:
        c.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?)', (session, task['root'], json.dumps(task)))


def update_task(session, change, expected_id=None):
    """Mutate the latest task in a single writer transaction; never stale-replace."""
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT body FROM tasks WHERE session=?', (session,)).fetchone()
        task = json.loads(row[0]) if row else None
        if expected_id is not None and (not task or task.get('id') != expected_id):
            raise ValueError('Task changed while the operation was running.')
        updated = change(task)
        writable(updated['root'])
        c.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?)',
                  (session, updated['root'], json.dumps(updated)))
    return updated

def event(session, root, name, tool='', outcome='unknown', provider='unknown', duration_ms=None):
    if protected(root):
        return
    with db() as c:
        cursor = c.execute('INSERT INTO events(at,scope,session,event,tool,outcome) VALUES (?,?,?,?,?,?)',
                  (time.time(), scope_id(root), digest(session.encode())[:24], name[:40], tool[:80], outcome[:24]))
        c.execute('INSERT INTO event_details VALUES (?,?,?)', (cursor.lastrowid, provider, duration_ms))
        if name == 'SessionStart':
            c.execute('DELETE FROM events WHERE at < ?', (time.time() - POLICY['event_retention_days'] * 86400,))
            c.execute('DELETE FROM event_details WHERE event_id NOT IN (SELECT id FROM events)')

def fact_add(root, item):
    root = writable(root)
    required = {'id', 'claim', 'source', 'kind', 'verification'}
    if not required <= item.keys():
        raise ValueError('Fact requires id, claim, source, kind, verification.')
    if item['kind'] != 'verified-observation':
        raise ValueError('Automatic memory accepts verified-observation only; decisions/proposals belong in their own records.')
    if not item['verification'].strip() or len(item['claim']) > 2000:
        raise ValueError('Supply concise claim and semantic verification explanation.')
    source = canonical(root / item['source'])
    if not beneath(source, root) or not source.is_file():
        raise ValueError('Fact source must be an existing file inside this project.')
    if any(s.lower() in {'.env', 'auth.json', 'credentials', 'id_rsa', 'id_ed25519'} for s in source.parts):
        raise ValueError('Secret-bearing files are not knowledge sources.')
    item = dict(item, source=str(source.relative_to(root)), source_hash=digest(source.read_bytes()),
                verified_at=time.time(), status='active')
    try:
        item['revision'] = git(root, 'rev-parse', 'HEAD').decode().strip()
    except ValueError:
        item['revision'] = None
    with db() as c:
        existing = c.execute('SELECT body FROM facts WHERE scope=? AND id=?', (scope_id(root), item['id'])).fetchone()
        if existing:
            raise ValueError('Fact ID already exists; use a new ID with supersedes to retain history.')
        previous = item.get('supersedes')
        if previous:
            row = c.execute('SELECT body FROM facts WHERE scope=? AND id=?', (scope_id(root), previous)).fetchone()
            if not row or json.loads(row[0])['status'] != 'active':
                raise ValueError('supersedes must name an active fact in this project.')
            old = dict(json.loads(row[0]), status='superseded', superseded_by=item['id'])
            c.execute('UPDATE facts SET body=? WHERE scope=? AND id=?', (json.dumps(old), scope_id(root), previous))
        c.execute('INSERT INTO facts VALUES (?,?,?)', (scope_id(root), item['id'], json.dumps(item)))
    return item

def facts(root, history=False):
    root = canonical(root)
    if protected(root):
        return []
    with db() as c:
        rows = c.execute('SELECT body FROM facts WHERE scope=?', (scope_id(root),)).fetchall()
    result = []
    for row in rows:
        item = json.loads(row[0])
        path = root / item['source']
        if item['status'] == 'active':
            valid = (beneath(path, root) and path.is_file() and digest(path.read_bytes()) == item['source_hash']
                     and time.time() - item['verified_at'] < POLICY['fact_max_age_days'] * 86400)
            if not valid:
                item['status'] = 'stale'
        if history or item['status'] == 'active':
            result.append(item)
    return result
