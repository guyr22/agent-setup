"""Validate skills, native renders, source syntax, and runtime behavior without model calls."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'state/validation-deps'))
sys.path.insert(0, 'C:/Users/guyr2/.codex/skills/.system/skill-creator/scripts')
from quick_validate import validate_skill
import yaml
import configure

def main():
    problems = []
    for path in sorted((ROOT / 'skills').glob('eng-*')):
        ok, message = validate_skill(path)
        if not ok: problems.append(f'{path.name}: {message}')
    for path in list(ROOT.glob('*.py')) + list((ROOT / 'evals').glob('*.py')):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    rendered = configure.render()
    for name, content in rendered.items():
        if name.endswith('.toml'): tomllib.loads(content)
        elif name.endswith('.json'): json.loads(content)
        elif '/agents/' in name and name.endswith('.md'):
            data = yaml.safe_load(content.split('---', 2)[1])
            if not all(k in data for k in ('name', 'description', 'model')): problems.append('Invalid agent ' + name)
    if problems:
        print('\n'.join(problems)); return 1
    print(f'Validated 14 skill frontmatters and {len(rendered)} native output files.', flush=True)
    return subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT).returncode

if __name__ == '__main__': raise SystemExit(main())
