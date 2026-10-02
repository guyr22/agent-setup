"""Project setup: read-only discovery, reviewable drafts, non-destructive application."""
import base64
import json
from pathlib import Path
import time
from englib import ROOT, STATE, canonical, beneath, writable, git, digest, read_json, save_json, atomic

MARKER = '<!-- eng-project-setup -->'

def inspect(root):
    root = canonical(root)
    names = ['AGENTS.md', 'CLAUDE.md', 'VAULT.md', 'README.md', 'package.json', 'pyproject.toml',
             'go.mod', 'Cargo.toml', 'Makefile', 'WORKSPACE.json', '.agent/project.json']
    found = [n for n in names if (root / n).is_file()]
    children = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and not p.is_symlink() and (p / '.git').exists():
            try:
                revision = git(p, 'rev-parse', 'HEAD').decode().strip()
            except ValueError:
                revision = 'unborn'
            children.append({'path': p.name, 'revision': revision})
    return {'root': str(root), 'is_git': (root / '.git').exists(), 'entrypoints': found,
            'repositories': children, 'next': 'Read existing instructions, design and delivery sources; inspect CI for actual commands. No project scripts were executed.'}

def local_ref(root, name, must_exist=True):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Source references must be nonempty relative paths.')
    p = Path(name)
    target = canonical(root / p)
    if p.is_absolute() or not beneath(target, root):
        raise ValueError('Reference must remain inside this project/workspace: ' + name)
    if must_exist and not target.exists():
        raise ValueError('Referenced authority is missing: ' + name)
    return name.replace('\\', '/')

def draft(root, spec):
    root = writable(root)
    for key in ('name', 'summary', 'kind', 'sources', 'commands'):
        if key not in spec:
            raise ValueError('Project specification is missing ' + key)
    if spec['kind'] not in ('project', 'workspace'):
        raise ValueError('kind must be project or workspace')
    if MARKER in (root / 'AGENTS.md').read_text(encoding='utf-8') if (root / 'AGENTS.md').exists() else False:
        raise ValueError('An installed setup exists. Inspect and update it deliberately instead of appending another copy.')
    for source in spec['sources']:
        if source.get('role') not in ('instructions', 'design', 'decisions', 'delivery', 'verification', 'vault'):
            raise ValueError('Unknown source role')
        local_ref(root, source['path'])
    for command in spec['commands']:
        if not isinstance(command.get('argv'), list) or not command['argv'] or not all(isinstance(a, str) for a in command['argv']):
            raise ValueError('Commands use explicit argv arrays; they are documentation, not startup actions.')
        local_ref(root, command.get('cwd', '.'))
        if command.get('status') not in ('observed', 'verified') or not command.get('evidence'):
            raise ValueError('Commands require observed/verified status and evidence reference.')
    if spec['kind'] == 'workspace':
        if not spec.get('repositories'):
            raise ValueError('A workspace requires an inspected repository registry.')
        for repo in spec['repositories']:
            local_ref(root, repo['path'])
            if not (root / repo['path'] / '.git').exists():
                raise ValueError('Registry contains a non-Git directory: ' + repo['path'])
            if not repo.get('role'):
                raise ValueError('Each repository requires its observed role.')
            try:
                repo['revision'] = git(root / repo['path'], 'rev-parse', 'HEAD').decode().strip()
            except ValueError:
                repo['revision'] = 'unborn'
    files = {}
    config_path = 'WORKSPACE.json' if spec['kind'] == 'workspace' else '.agent/project.json'
    if (root / config_path).exists():
        raise ValueError('Existing registry must be reconciled, not overwritten: ' + config_path)
    spec = dict(spec, schema_version=1, authority='assistant-selected', created_at=time.time())
    files[config_path] = json.dumps(spec, indent=2) + '\n'
    lines = [MARKER, f'## {spec["name"]}: agent navigation', '', spec['summary'], '',
             f'Project registry: `{config_path}`. Load only the sources relevant to the current task.', '',
             '### Sources of authority', '']
    for source in spec['sources']:
        lines.append(f'- {source["role"]}: `{source["path"]}` — {source.get("description", "existing authority")}')
    if not spec['sources']:
        lines.append('No existing design authority was identified. Treat undocumented behavior as observed, not a product decision.')
    lines += ['', '### Verification', '']
    for command in spec['commands']:
        lines.append(f'- {command.get("name", "check")}: `{json.dumps(command["argv"])}` in `{command.get("cwd", ".")}` ({command["status"]}; {command["evidence"]}).')
    if not spec['commands']:
        lines.append('No verification command has been established. Discover or implement appropriate checks before claiming verified delivery.')
    lines += ['', '### Working rules', '',
              'Use focused work for local changes; plan consequential work; coordinate cross-repository contracts explicitly.',
              'Follow more specific area instructions. Preserve local changes. Keep worker write areas separate.',
              'Design describes intended behavior; delivery records describe implementation and executed evidence.',
              'The VAULT is a compact current index. Preserve decision provenance and supersession; do not duplicate specifications.',
              'Automatically update only verified observations. Propose changes to workflow, permissions, or product decisions for review.',
              'Before final delivery run the checks required by the affected repository and report limitations.', '']
    existing = (root / 'AGENTS.md').read_text(encoding='utf-8-sig') if (root / 'AGENTS.md').exists() else ''
    files['AGENTS.md'] = existing.rstrip() + ('\n\n' if existing else '') + '\n'.join(lines)
    claude = (root / 'CLAUDE.md').read_text(encoding='utf-8-sig') if (root / 'CLAUDE.md').exists() else ''
    if '@AGENTS.md' not in claude:
        files['CLAUDE.md'] = claude.rstrip() + ('\n\n' if claude else '') + '@AGENTS.md\n'
    if not any(s['role'] == 'vault' for s in spec['sources']) and not (root / 'VAULT.md').exists():
        files['VAULT.md'] = ('# Current project knowledge\n\nThis is a navigation index, not a transcript.\n\n'
                             f'Project sources and commands: `{config_path}`.\n\n'
                             'Add only verified observations with source/revision, date, and revalidation trigger. '
                             'Link to design decisions and delivery evidence; do not copy them here. '
                             'Keep superseded history out of the active index. No facts have been verified by this scaffold.\n')
    rows = []
    for name, content in files.items():
        target = writable(root / name)
        if not beneath(target, root):
            raise ValueError('Scaffold target escapes project')
        before = target.read_bytes() if target.exists() else None
        after = content.encode('utf-8')
        rows.append({'path': name, 'before_hash': digest(before) if before is not None else None,
                     'after_hash': digest(after), 'before': base64.b64encode(before).decode() if before is not None else None,
                     'after': base64.b64encode(after).decode()})
    plan = {'root': str(root), 'files': rows, 'created': time.time(), 'kind': spec['kind']}
    path = STATE / 'project-drafts' / (digest(str(root).encode())[:16] + '.json')
    save_json(path, plan)
    return str(path)

def apply(plan):
    m = read_json(plan)
    root = writable(m['root'])
    allowed = {'AGENTS.md', 'CLAUDE.md', 'VAULT.md', '.agent/project.json', 'WORKSPACE.json'}
    for row in m['files']:
        target = writable(root / row['path'])
        if row['path'] not in allowed or not beneath(target, root):
            raise ValueError('Unexpected scaffold target')
        raw = target.read_bytes() if target.exists() else None
        if (digest(raw) if raw is not None else None) != row['before_hash']:
            raise ValueError('Project changed since draft; regenerate: ' + row['path'])
        if digest(base64.b64decode(row['after'])) != row['after_hash']:
            raise ValueError('Draft content hash mismatch')
    backup = STATE / 'project-backups' / (digest(str(root).encode())[:16] + '-' + str(time.time_ns()) + '.json')
    save_json(backup, m)
    written = []
    try:
        for row in m['files']:
            atomic(root / row['path'], base64.b64decode(row['after']))
            written.append(row)
    except Exception:
        for row in reversed(written):
            if row['before'] is None:
                writable(root / row['path']).unlink()
            else:
                atomic(root / row['path'], base64.b64decode(row['before']))
        raise
    return {'written': [r['path'] for r in written], 'backup': str(backup)}
