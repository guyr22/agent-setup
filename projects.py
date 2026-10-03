"""Project setup: read-only discovery, reviewable drafts, non-destructive application."""
import base64
import json
from pathlib import Path
import re
import time
from englib import ROOT, STATE, canonical, beneath, writable, git, digest, read_json, save_json, atomic

MARKER = '<!-- eng-project-setup -->'
END_MARKER = '<!-- /eng-project-setup -->'

def inspect(root):
    root = canonical(root)
    names = ['AGENTS.md', 'CLAUDE.md', 'VAULT.md', 'README.md', 'package.json', 'pyproject.toml',
             'go.mod', 'Cargo.toml', 'Makefile', 'WORKSPACE.json', '.agent/project.json']
    found = [n for n in names if (root / n).is_file()]
    instructions = (root / 'AGENTS.md').read_text(encoding='utf-8-sig') if 'AGENTS.md' in found else ''
    children = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and not p.is_symlink() and (p / '.git').exists():
            try:
                revision = git(p, 'rev-parse', 'HEAD').decode().strip()
            except ValueError:
                revision = 'unborn'
            children.append({'path': p.name, 'revision': revision})
    return {'root': str(root), 'is_git': (root / '.git').exists(), 'entrypoints': found,
            'setup': 'managed' if END_MARKER in instructions else 'legacy-needs-reconciliation' if MARKER in instructions else 'unmanaged',
            'default_outputs': ['AGENTS.md', 'CLAUDE.md'],
            'intake': ['Read existing sources first. Ask only about missing goals, non-negotiable constraints, or authority conflicts.',
                       'Use the existing documentation structure. Registry and new knowledge index are opt-in.',
                       'Use project draft --update for an existing bounded setup; preserve everything outside its markers.'],
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

def prepare_spec(root, spec):
    if not isinstance(spec, dict):
        raise ValueError('Project specification must be an object.')
    for key in ('name', 'summary', 'kind', 'sources', 'commands'):
        if key not in spec:
            raise ValueError('Project specification is missing ' + key)
    if spec['kind'] not in ('project', 'workspace'):
        raise ValueError('kind must be project or workspace')
    spec = json.loads(json.dumps(spec))
    if MARKER in json.dumps(spec) or END_MARKER in json.dumps(spec):
        raise ValueError('Project content must not contain setup ownership markers.')
    for key in ('name', 'summary'):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise ValueError('Project name and summary must be nonempty strings.')
    for key in ('registry', 'create_vault'):
        if key in spec and type(spec[key]) is not bool:
            raise ValueError(key + ' must be boolean.')
    for key in ('invariants', 'conventions', 'open_questions'):
        if not isinstance(spec.get(key, []), list) or not all(isinstance(x, str) for x in spec.get(key, [])):
            raise ValueError(key + ' must contain concise strings.')
    for key in ('sources', 'commands', 'domains', 'repositories'):
        if not isinstance(spec.get(key, []), list) or not all(isinstance(x, dict) for x in spec.get(key, [])):
            raise ValueError(key + ' must contain objects.')
    for source in spec['sources']:
        if source.get('role') not in ('instructions', 'design', 'decisions', 'delivery', 'verification', 'vault'):
            raise ValueError('Unknown source role')
        source['path'] = local_ref(root, source.get('path'))
    for command in spec['commands']:
        if not isinstance(command.get('argv'), list) or not command['argv'] or not all(isinstance(a, str) for a in command['argv']):
            raise ValueError('Commands use explicit argv arrays; they are documentation, not startup actions.')
        command['cwd'] = local_ref(root, command.get('cwd', '.'))
        if not (root / command.get('cwd', '.')).is_dir():
            raise ValueError('Command cwd must be a directory.')
        if command.get('status') not in ('observed', 'verified') or not command.get('evidence'):
            raise ValueError('Commands require observed/verified status and evidence reference.')
    for domain in spec.get('domains', []):
        domain['path'] = local_ref(root, domain.get('path'))
        if not domain.get('responsibility'):
            raise ValueError('Domains require an observed responsibility.')
    if spec['kind'] == 'workspace':
        if not spec.get('repositories'):
            raise ValueError('A workspace requires an inspected repository registry.')
        for repo in spec['repositories']:
            repo['path'] = local_ref(root, repo.get('path'))
            if not (root / repo['path'] / '.git').exists():
                raise ValueError('Registry contains a non-Git directory: ' + repo['path'])
            if not repo.get('role'):
                raise ValueError('Each repository requires its observed role.')
            try:
                repo['revision'] = git(root / repo['path'], 'rev-parse', 'HEAD').decode().strip()
            except ValueError:
                repo['revision'] = 'unborn'
    return spec


def instruction_block(text):
    if text.count(MARKER) != 1 or text.count(END_MARKER) != 1 or text.index(END_MARKER) < text.index(MARKER):
        raise ValueError('Legacy or ambiguous instruction markers: reconcile the exact owned region before updating; no text was replaced.')
    return text.index(MARKER), text.index(END_MARKER) + len(END_MARKER)


def imports_agents(text):
    # A mention inside a fenced example is not an active Claude import.
    fence = None
    for line in text.lstrip('\ufeff').splitlines():
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            token = match[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[match.end():].strip():
                fence = None
        elif fence is None and re.fullmatch(r'\s*@(?:\./)?AGENTS\.md\s*', line):
            return True
    return False


def draft(root, spec, update=False):
    root = writable(root)
    spec = prepare_spec(root, spec)
    existing = (root / 'AGENTS.md').read_bytes().decode('utf-8') if (root / 'AGENTS.md').exists() else ''
    if MARKER in existing:
        if not update:
            raise ValueError('An installed setup exists. Inspect it and use --update with a reconciled specification.')
        start, end = instruction_block(existing)
    elif update:
        raise ValueError('No managed instruction block exists; inspect existing text and draft initial setup without --update.')
    elif END_MARKER in existing:
        raise ValueError('Ambiguous instruction markers require reconciliation before drafting.')
    files = {}
    config_path = 'WORKSPACE.json' if spec['kind'] == 'workspace' else '.agent/project.json'
    registry_exists = (root / config_path).exists()
    old_registry = read_json(root / config_path, {})
    registry = spec['kind'] == 'workspace' or spec.get('registry', registry_exists)
    if registry_exists:
        if not isinstance(old_registry, dict) or not registry or not update or old_registry.get('generator') != 'eng-project-setup':
            raise ValueError('Existing registry must be reconciled, not overwritten or silently retired: ' + config_path)
    if registry:
        stored = dict(old_registry, **spec)
        stored.update(schema_version=2, generator='eng-project-setup', authority='assistant-selected', updated_at=time.time())
        files[config_path] = json.dumps(stored, indent=2) + '\n'
    lines = [MARKER, f'## {spec["name"]}: agent navigation', '', spec['summary'], '']
    if registry:
        lines += [f'Read `{config_path}` for the authoritative navigation index, commands, boundaries, and open questions.',
                  'Load only the referenced sources relevant to the task. Commands are documented, not executed by setup.']
    else:
        lines += ['### Sources of authority', '']
        for source in spec['sources']:
            lines.append(f'- {source["role"]}: `{source["path"]}` — {source.get("description", "existing authority")}')
        if not spec['sources']:
            lines.append('No design authority has been identified. Ask about missing intent; do not infer requirements from implementation.')
        if spec.get('domains'):
            lines += ['', '### Areas and ownership', '']
            for area in spec['domains']:
                lines.append(f'- `{area["path"]}`: {area["responsibility"]}; owner: {area.get("owner", "unknown")}.')
        lines += ['', '### Verification', '']
        for command in spec['commands']:
            lines.append(f'- {command.get("name", "check")}: `{json.dumps(command["argv"])}` in `{command.get("cwd", ".")}` ({command["status"]}; {command["evidence"]}).')
        if not spec['commands']:
            lines.append('No verification command has been established. Discover appropriate checks before claiming verified delivery.')
        for field, title in [('invariants', 'Project invariants'), ('conventions', 'Local conventions'), ('open_questions', 'Open questions')]:
            if spec.get(field):
                lines += ['', '### ' + title, ''] + ['- ' + text for text in spec[field]]
    lines += ['', 'Use this project guidance with more specific area instructions. Requirements and decisions remain in their linked sources.',
              'Preserve local changes; use the narrowest meaningful checks and report what actually ran. Setup does not grant deployment authority.',
              END_MARKER]
    block = '\n'.join(lines)
    files['AGENTS.md'] = existing[:start] + block + existing[end:] if update else existing + ('\n\n' if existing and not existing.endswith('\n\n') else '') + block + '\n'
    claude = (root / 'CLAUDE.md').read_bytes().decode('utf-8') if (root / 'CLAUDE.md').exists() else ''
    if not imports_agents(claude):
        files['CLAUDE.md'] = claude + ('\n\n' if claude and not claude.endswith('\n\n') else '') + '@AGENTS.md\n'
    if spec.get('create_vault', False) and not any(s['role'] == 'vault' for s in spec['sources']) and not (root / 'VAULT.md').exists():
        files['VAULT.md'] = ('# Current project knowledge\n\nThis is a navigation index, not a transcript.\n\n'
                             'Project sources and commands: `AGENTS.md`.\n\n'
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


def validate(root, spec=None):
    root = canonical(root)
    errors = []
    warnings = []
    try:
        agents = (root / 'AGENTS.md').read_text(encoding='utf-8-sig')
        instruction_block(agents)
        claude = (root / 'CLAUDE.md').read_text(encoding='utf-8-sig')
        if not imports_agents(claude): errors.append('CLAUDE.md has no active @AGENTS.md import.')
    except (ValueError, OSError) as exc:
        errors.append(str(exc))
    if spec is None:
        for name in ('.agent/project.json', 'WORKSPACE.json'):
            try:
                value = read_json(root / name, {})
            except (ValueError, OSError) as exc:
                errors.append(str(exc)); continue
            if isinstance(value, dict) and value.get('generator') == 'eng-project-setup':
                spec = value; break
    if spec is None:
        warnings.append('Pass --spec to validate source references and command directories for a minimal setup.')
    else:
        try:
            checked = prepare_spec(root, spec)
            if not checked['commands']: warnings.append('No project verification commands are established.')
            if checked.get('open_questions'): warnings.append('Project intent still has documented open questions.')
        except (ValueError, KeyError, TypeError, OSError) as exc:
            errors.append(str(exc))
    return {'root': str(root), 'errors': errors, 'warnings': warnings, 'commands_executed': False,
            'coverage': 'Instruction block/import plus provided registry/spec references; native client loading and command success require separate checks.'}

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
