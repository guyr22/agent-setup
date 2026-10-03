import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import unittest
from unittest.mock import patch

import test_runtime
import configure
import englib as lib
import install


class InstallerTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    tearDown = test_runtime.RuntimeTests.tearDown

    def build(self, home, selected=None, name='plan.json'):
        return configure.build(home, self.root/name, providers=selected)

    def apply(self, home, selected=None):
        return configure.apply(self.build(home, selected), 'authorized fixture')

    def test_claude_only_ignores_broken_codex_config(self):
        home=self.root/'home'; (home/'.codex').mkdir(parents=True)
        bad=home/'.codex/config.toml'; bad.write_text('malformed TOML {')
        self.apply(home, {'claude'})
        self.assertTrue((home/'.claude/skills/eng-project-setup/SKILL.md').is_file())
        self.assertFalse((home/'.agents').exists())
        self.assertFalse((home/'.codex/AGENTS.md').exists())
        self.assertEqual(bad.read_text(),'malformed TOML {')
        self.assertEqual(lib.read_json(configure.STATE/'deployment.json')['providers'], ['claude'])

    def test_existing_instruction_text_survives_install_update_uninstall(self):
        home=self.root/'home'; (home/'.codex').mkdir(parents=True)
        p=home/'.codex/AGENTS.md'; original=b'\xef\xbb\xbfPersonal rule\r\n'
        p.write_bytes(original)
        self.apply(home, {'codex'})
        self.assertTrue(p.read_bytes().startswith(original))
        p.write_bytes(p.read_bytes()+b'\r\nNew personal rule\r\n')
        self.apply(home, {'codex'})
        self.assertEqual(p.read_text(encoding='utf-8-sig').count(configure.INSTRUCTION_BEGIN),1)
        configure.apply(install.uninstall_plan({'codex'},self.root/'uninstall.json'),'fixture')
        self.assertTrue(p.read_bytes().startswith(original))
        self.assertIn(b'New personal rule',p.read_bytes())
        self.assertNotIn(configure.INSTRUCTION_BEGIN.encode(),p.read_bytes())
        self.assertEqual(lib.read_json(configure.STATE/'deployment.json')['files'],[])

    def test_repeated_updates_preserve_first_install_baseline(self):
        home=self.root/'home'; (home/'.claude').mkdir(parents=True)
        settings=home/'.claude/settings.json'; original=b'{"theme":"dark"}\r\n';settings.write_bytes(original)
        self.apply(home)
        before={p: p.read_bytes() for p in home.rglob('*') if p.is_file()}
        self.apply(home)
        self.assertEqual(before,{p:p.read_bytes() for p in home.rglob('*') if p.is_file()})
        self.apply(home)
        configure.apply(install.uninstall_plan(output=self.root/'uninstall.json'),'fixture')
        self.assertEqual(settings.read_bytes(),original)
        self.assertEqual([p for p in home.rglob('*') if p.is_file()],[settings])
        # Empty native directories are harmless and deliberately not recursively deleted.
        self.apply(home)
        self.assertTrue((home/'.codex/AGENTS.md').is_file())

    def test_uninstall_preserves_later_native_preferences_and_hooks(self):
        home=self.root/'home'; self.apply(home)
        settings=home/'.claude/settings.json'
        value=json.loads(settings.read_text());value['theme']='user-new-theme'
        extra={'hooks':[{'type':'command','command':'user-helper'}]}
        value['hooks']['Stop'].append(extra);settings.write_text(json.dumps(value))
        toml=home/'.codex/config.toml'
        toml.write_text('model = "user-chosen"\n'+toml.read_text().replace(configure.END,'[hooks.trust]\nkeep = true\n'+configure.END))
        self.apply(home)  # Updating must not turn later preferences into removable setup content.
        configure.apply(install.uninstall_plan(output=self.root/'uninstall.json'),'fixture')
        self.assertEqual(json.loads(settings.read_text()),{'theme':'user-new-theme','hooks':{'Stop':[extra]}})
        remaining=tomllib.loads(toml.read_text())
        self.assertEqual(remaining,{'model':'user-chosen','hooks':{'trust':{'keep':True}}})
        self.assertNotIn(configure.BEGIN,toml.read_text())

    def test_partial_install_and_rollback_do_not_touch_other_client_drift(self):
        home=self.root/'home';self.apply(home,{'codex'})
        changed=home/'.codex/agents/eng-reviewer.toml';changed.write_text('user edit')
        release=self.apply(home,{'claude'})
        self.assertEqual(changed.read_text(),'user edit')
        m=lib.read_json(configure.STATE/'deployment.json')
        self.assertEqual(set(m['providers']),{'codex','claude'})
        row=next(x for x in m['files'] if x['path']=='.codex/agents/eng-reviewer.toml')
        self.assertFalse(configure.matches_owned(row,changed.read_bytes()))
        configure.rollback(release,'fixture')
        self.assertEqual(changed.read_text(),'user edit')
        self.assertFalse((home/'.claude/CLAUDE.md').exists())

    def test_partial_uninstall_retains_other_client_and_supports_reinstall(self):
        home=self.root/'home';self.apply(home)
        claude={p:p.read_bytes() for p in (home/'.claude').rglob('*') if p.is_file()}
        configure.apply(install.uninstall_plan({'codex'},self.root/'uninstall.json'),'fixture')
        self.assertEqual(claude,{p:p.read_bytes() for p in (home/'.claude').rglob('*') if p.is_file()})
        self.assertEqual(lib.read_json(configure.STATE/'deployment.json')['providers'],['claude'])
        self.apply(home,{'codex'})
        self.assertEqual(set(lib.read_json(configure.STATE/'deployment.json')['providers']),{'codex','claude'})

    def test_changed_managed_content_blocks_update_and_uninstall(self):
        home=self.root/'home';self.apply(home)
        p=home/'.codex/AGENTS.md'
        p.write_text(p.read_text().replace('Working agreement','User changed managed policy'))
        before={p:p.read_bytes() for p in home.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'local edits'):self.build(home)
        with self.assertRaisesRegex(ValueError,'Owned content changed'):install.uninstall_plan(output=self.root/'uninstall.json')
        self.assertEqual(before,{p:p.read_bytes() for p in home.rglob('*') if p.is_file()})

    def test_stale_installation_plan_cannot_drop_new_client_ownership(self):
        home=self.root/'home';self.apply(home,{'codex'})
        stale=self.build(home,{'codex'},'stale.json')
        self.apply(home,{'claude'})
        with self.assertRaisesRegex(ValueError,'Installation state changed'):
            configure.apply(stale,'fixture')
        self.assertEqual(set(lib.read_json(configure.STATE/'deployment.json')['providers']),{'codex','claude'})

    def test_uninstall_rollback_restores_installation_and_native_files(self):
        home=self.root/'home';self.apply(home)
        before={p:p.read_bytes() for p in home.rglob('*') if p.is_file()}
        release=configure.apply(install.uninstall_plan(output=self.root/'uninstall.json'),'fixture')
        self.assertFalse(lib.read_json(configure.STATE/'deployment.json')['files'])
        configure.rollback(release,'fixture')
        self.assertEqual(before,{p:p.read_bytes() for p in home.rglob('*') if p.is_file()})
        self.assertTrue(lib.read_json(configure.STATE/'deployment.json')['files'])

    def test_failed_write_reverts_prior_mutations(self):
        home=self.root/'home';plan=self.build(home)
        actual=configure.atomic
        def fail(path,data):
            if Path(path)==home/'.codex/agents/eng-architect.toml':
                raise OSError('fixture write failure')
            return actual(path,data)
        with patch.object(configure,'atomic',side_effect=fail),self.assertRaises(OSError):
            configure.apply(plan,'fixture')
        self.assertFalse([p for p in home.rglob('*') if p.is_file()])
        self.assertFalse((configure.STATE/'deployment.json').exists())

    def test_cli_clean_checkout_preview_install_update_uninstall(self):
        # No personal overrides or production deployment state enter this fixture.
        checkout=self.root/'checkout with spaces';checkout.mkdir()
        for path in list(lib.ROOT.glob('*.py'))+list(lib.ROOT.glob('*.json'))+list(lib.ROOT.glob('*.md')):
            if path.name in {'local.json','local.instructions.md'}:continue
            shutil.copy2(path,checkout/path.name)
        shutil.copytree(lib.ROOT/'skills',checkout/'skills')
        shutil.copytree(lib.ROOT/'templates',checkout/'templates')
        shutil.copytree(lib.ROOT/'evals',checkout/'evals',ignore=shutil.ignore_patterns('__pycache__'))
        home=self.root/'new user'
        def cli(*args):
            result=subprocess.run([sys.executable,'-B',str(checkout/'install.py'),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        cli('install','--target','both','--home',home)
        self.assertFalse(home.exists())
        cli('install','--target','both','--home',home,'--apply')
        self.assertNotIn('guyr2', (home/'.codex/AGENTS.md').read_text().split('Shared tooling')[0])
        self.assertNotIn('KeepHQ',(home/'.codex/AGENTS.md').read_text())
        self.assertTrue(json.loads(cli('status'))['installed'])
        cli('update','--apply')
        cli('uninstall','--apply')
        self.assertFalse(json.loads(cli('status'))['installed'])
        self.assertFalse([p for p in home.rglob('*') if p.is_file()])

    def test_local_model_overrides_do_not_change_main_model(self):
        home=self.root/'home';(home/'.codex').mkdir(parents=True)
        p=home/'.codex/config.toml';p.write_text('model = "personal-main"\n')
        with patch.object(configure,'LOCAL',{'profiles':{'fast':{'codex_model':'custom-fast','claude_model':'haiku','effort':'low'}}}):
            rendered=configure.render(home)
        self.assertEqual(tomllib.loads(rendered['.codex/config.toml'])['model'],'personal-main')
        self.assertEqual(tomllib.loads(rendered['.codex/eng-fast.config.toml'])['model'],'custom-fast')

    def test_owned_hook_edit_is_not_silently_overwritten_on_update(self):
        home=self.root/'home';self.apply(home)
        p=home/'.claude/settings.json';settings=json.loads(p.read_text())
        settings['hooks']['Stop'][0]['hooks'][0]['timeout']=90
        p.write_text(json.dumps(settings)); before=p.read_bytes()
        with self.assertRaisesRegex(ValueError,'local edits'):
            self.build(home)
        self.assertEqual(p.read_bytes(),before)

    def test_windows_interpreter_shell_metacharacters_are_rejected(self):
        if sys.platform != 'win32': self.skipTest('Windows quoting contract')
        with patch.object(configure.sys,'executable','C:/Tools&Other/python.exe'):
            with self.assertRaisesRegex(ValueError,'shell-safe'):
                configure.hook_entries('codex')
