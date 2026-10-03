"""Install the engineering setup for Codex, Claude Code, or both. Preview by default."""
import argparse
import base64
import json
from pathlib import Path
import re
import sys
import time

if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 or newer is required.')

import tomllib

import configure as config
import englib as lib


def decode(value):
    return base64.b64decode(value) if value is not None else None


def remove_instruction_block(current, row):
    text = current.decode('utf-8')
    start, end = config.instruction_region(text)
    remaining = text[:start] + text[end:]
    initial = decode(row['initial_after']).decode('utf-8')
    first_start, first_end = config.instruction_region(initial)
    if remaining == initial[:first_start] + initial[first_end:]:
        return decode(row['original'])
    return remaining.encode('utf-8') if remaining.strip() or row['original'] is not None else None


def restore_hook_settings(current, row):
    original_raw = decode(row['original'])
    original = json.loads(original_raw or b'{}')
    result = json.loads(current)
    expected = json.loads(decode(row['after']))
    marker = (config.ROOT / 'hooks.py').as_posix().lower()
    def owned(handler):
        return marker in handler.get('command', '').replace('\\', '/').lower()
    hooks = result.get('hooks', {})
    for event in expected.get('hooks', {}):
        kept = []
        for entry in hooks.get(event, []):
            remaining = [h for h in entry.get('hooks', []) if not owned(h)]
            if remaining:
                kept.append(dict(entry, hooks=remaining))
            elif not entry.get('hooks'):
                kept.append(entry)
        # Restore any matching hook that existed before this installer owned it.
        for entry in original.get('hooks', {}).get(event, []):
            previous = [h for h in entry.get('hooks', []) if owned(h)]
            if previous:
                kept.append(dict(entry, hooks=previous))
        if kept:
            hooks[event] = kept
        elif event in original.get('hooks', {}):
            hooks[event] = []
        else:
            hooks.pop(event, None)
    if not hooks and 'hooks' not in original:
        result.pop('hooks', None)
    if result == original:
        return original_raw
    return (json.dumps(result, indent=2) + '\n').encode()


def restore_agents_settings(current, row):
    original_raw = decode(row['original'])
    original = tomllib.loads((original_raw or b'').decode('utf-8-sig'))
    old_agents = original.get('agents', {})
    text = current.decode('utf-8-sig')
    header = re.search(r'(?m)^[ \t]*\[agents\][ \t]*(?:#[^\n]*)?\r?$', text)
    if not header:
        raise ValueError('Cannot locate the owned [agents] section; reconcile before uninstall.')
    following = re.search(r'(?m)^[ \t]*\[', text[header.end():])
    end = header.end() + following.start() if following else len(text)
    section = text[header.end():end]
    for key in ('enabled', 'max_concurrent_threads_per_session'):
        pattern = rf'(?m)^[ \t]*{re.escape(key)}[ \t]*=[^\r\n]*(?:\r?\n|$)'
        value = old_agents.get(key)
        replacement = f'{key} = {json.dumps(value)}\n' if key in old_agents else ''
        section, count = re.subn(pattern, replacement, section, count=1)
        if count != 1:
            raise ValueError('Owned agent settings have an unsupported format.')
    section = section.replace(config.BEGIN, '').replace(config.END, '')
    empty = not tomllib.loads('[agents]\n' + section).get('agents')
    text = text[:header.start()] + ('' if empty else text[header.start():header.end()]) + section + text[end:]
    text = re.sub(r'(?m)^' + re.escape(config.BEGIN) + r'\r?\n?', '', text)
    text = re.sub(r'(?m)^' + re.escape(config.END) + r'\r?\n?', '', text)
    if tomllib.loads(text) == original:
        # Preserve newly added comments even when semantic settings match.
        if current == decode(row.get('initial_after')):
            return original_raw
    return text.encode() if text.strip() or original_raw is not None else None


def uninstall_plan(providers=None, output=None):
    previous = lib.read_json(config.STATE / 'deployment.json', {})
    if not previous.get('files'):
        raise ValueError('Nothing is installed from this checkout.')
    if previous.get('installer_schema') != 1:
        raise ValueError('This deployment predates the installer; use its saved release rollback and source recovery instructions.')
    home = lib.canonical(previous['home'])
    installed = {config.provider_for(r['path']) for r in previous['files']}
    selected = config.selected_providers(providers or installed)
    if not selected <= installed:
        raise ValueError('A selected client is not installed from this checkout.')
    rows = []
    for prior in previous['files']:
        if config.provider_for(prior['path']) not in selected:
            rows.append(dict(prior, retained=True))
            continue
        target = config.checked_target(home, prior['path'])
        current = target.read_bytes() if target.exists() else None
        if prior['after'] is None:
            if current is not None:
                raise ValueError('Retired file was recreated; reconcile first: ' + prior['path'])
        elif current is None or not config.matches_owned(prior, current):
            raise ValueError('Owned content changed; uninstall will not overwrite it: ' + prior['path'])
        if 'original' not in prior:
            raise ValueError('Missing pre-install baseline; reconcile release history.')
        if current is None:
            after = decode(prior['original'])
        elif prior['path'] in config.INSTRUCTION_FILES:
            after = remove_instruction_block(current, prior)
        elif prior['path'] in {'.codex/hooks.json', '.claude/settings.json'}:
            after = restore_hook_settings(current, prior)
        elif prior['path'] == '.codex/config.toml':
            after = restore_agents_settings(current, prior)
        else:
            after = decode(prior['original'])
        rows.append({'path':prior['path'], 'before':base64.b64encode(current).decode() if current is not None else None,
                     'after':base64.b64encode(after).decode() if after is not None else None,
                     'before_hash':lib.digest(current) if current is not None else None,
                     'after_hash':lib.digest(after) if after is not None else None, 'managed':False})
    plan = {'version':lib.POLICY['version'], 'installer_schema':1, 'operation':'uninstall',
            'home':str(home), 'providers':sorted(installed-selected), 'created':time.time(),
            'source_hashes':config.source_hashes(),
            'base_deployment_hash':lib.digest((config.STATE/'deployment.json').read_bytes()), 'files':rows}
    path = Path(output) if output else config.ROOT/'build/uninstall.json'
    lib.save_json(path, plan)
    return path


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    actions = p.add_subparsers(dest='action', required=True)
    for action in ('install', 'update', 'uninstall'):
        q = actions.add_parser(action, help=action + ' selected clients; default is a preview')
        q.add_argument('--target', choices=['codex', 'claude', 'both'])
        q.add_argument('--home', type=Path, help='Native user home; never a project directory')
        q.add_argument('--apply', action='store_true', help='Apply the displayed changes with local backups')
        q.add_argument('--output', type=Path, help='Save the reviewed deployment plan here')
        q.add_argument('--reconcile', type=Path, help='Reviewed relative target -> current SHA256 mapping')
    actions.add_parser('status')
    q = actions.add_parser('rollback', help='Preview or restore one release, refusing later drift')
    q.add_argument('release', type=Path)
    q.add_argument('--apply', action='store_true')
    return p


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    args = parser().parse_args()
    previous = lib.read_json(config.STATE/'deployment.json', {})
    if args.action == 'status':
        installed = bool(previous.get('files'))
        errors = []
        if installed:
            for row in previous['files']:
                p = config.checked_target(Path(previous['home']), row['path'])
                raw = p.read_bytes() if p.exists() else None
                if (row['after'] is None and raw is not None) or (row['after'] is not None and (raw is None or not config.matches_owned(row, raw))):
                    errors.append(row['path'])
        print(json.dumps({'version':lib.POLICY['version'],'source':str(config.ROOT),'installed':installed,
                          'home':previous.get('home'),'providers':previous.get('providers',[]),'drift':errors}, indent=2))
        return bool(errors)
    if args.action == 'rollback':
        release = lib.read_json(args.release)
        print(f"Restore release {release['release_id']} under {release['home']}.")
        if args.apply:
            print(json.dumps(config.rollback(args.release, 'Explicit installer rollback --apply invocation'), indent=2))
        else:
            print('Preview only. Repeat with --apply to restore exact prior files; later drift is refused.')
        return 0
    installed = {config.provider_for(r['path']) for r in previous.get('files', [])}
    if args.action in ('update', 'uninstall') and not installed:
        raise ValueError('Nothing is installed from this checkout. Use install first.')
    selected = {'codex','claude'} if args.target == 'both' else {args.target} if args.target else installed or {'codex','claude'}
    home = lib.canonical(args.home or previous.get('home') or config.HOME)
    if args.action == 'uninstall':
        if home != lib.canonical(previous['home']):
            raise ValueError('Uninstall must target the recorded installation home.')
        if args.reconcile:
            raise ValueError('Uninstall never accepts forced ownership reconciliation.')
        plan = uninstall_plan(selected, args.output)
    else:
        output = args.output or config.ROOT/'build/deployment.json'
        plan = config.build(home, output, lib.read_json(args.reconcile) if args.reconcile else None, selected)
    print(config.deployment_diff(plan) or 'No native file changes.')
    print('Plan: ' + str(plan))
    if args.apply:
        release = config.apply(plan, 'Explicit installer ' + args.action + ' --apply invocation')
        print('Applied. Recovery release: ' + release)
        if args.action != 'uninstall':
            print('Start fresh sessions. Review changed hooks in native /hooks; the installer never changes hook trust or authentication.')
    else:
        print('Preview only; native files are unchanged. Repeat with --apply to install these changes.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
