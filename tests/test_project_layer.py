import base64
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_runtime
import englib as lib
import projects
import configure


class ProjectLayerTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    tearDown = test_runtime.RuntimeTests.tearDown
    repo = test_runtime.RuntimeTests.repo
    spec = test_runtime.RuntimeTests.spec

    def test_minimal_setup_is_portable_and_carries_project_constraints(self):
        root = self.repo(); spec = self.spec()
        spec.update(domains=[{'path': '.', 'responsibility': 'API', 'owner': 'team'}],
                    invariants=['Preserve stable identifiers'], conventions=['Follow existing formatting'],
                    open_questions=['Which spec governs retries?'])
        draft = projects.draft(root, spec)
        self.assertEqual({r['path'] for r in lib.read_json(draft)['files']}, {'AGENTS.md','CLAUDE.md'})
        projects.apply(draft)
        text = (root/'AGENTS.md').read_text()
        self.assertIn('Preserve stable identifiers', text)
        self.assertIn('Which spec governs retries?', text)
        self.assertNotIn(str(lib.ROOT), text)
        self.assertNotIn('engctl', text)
        self.assertFalse(projects.validate(root, spec)['errors'])
        self.assertFalse((root/'VAULT.md').exists())
        self.assertFalse((root/'.agent').exists())

    def test_update_preserves_surrounding_text_and_claude_once(self):
        root = self.repo(); spec = self.spec()
        (root/'AGENTS.md').write_text('User preface\n')
        (root/'CLAUDE.md').write_text('Claude preference\n')
        projects.apply(projects.draft(root, spec))
        original = (root/'AGENTS.md').read_text() + '\nManual follow-up\n'
        (root/'AGENTS.md').write_text(original)
        spec['summary'] = 'Updated purpose'
        projects.apply(projects.draft(root, spec, update=True))
        result = (root/'AGENTS.md').read_text()
        self.assertTrue(result.startswith('User preface\n'))
        self.assertTrue(result.endswith('\nManual follow-up\n'))
        self.assertEqual(result.count(projects.MARKER),1)
        self.assertIn('Updated purpose',result)
        self.assertEqual((root/'CLAUDE.md').read_text().count('@AGENTS.md'),1)
        self.assertTrue((root/'CLAUDE.md').read_text().startswith('Claude preference'))

    def test_legacy_and_unmanaged_registry_are_preserved(self):
        root = self.repo(); text = projects.MARKER+'\nLegacy body\nUser tail\n'
        (root/'AGENTS.md').write_text(text)
        with self.assertRaisesRegex(ValueError,'Legacy'):
            projects.draft(root,self.spec(),update=True)
        self.assertEqual((root/'AGENTS.md').read_text(),text)
        (root/'AGENTS.md').unlink(); (root/'.agent').mkdir()
        (root/'.agent/project.json').write_text('{"custom": true}')
        with self.assertRaisesRegex(ValueError,'registry'):
            projects.draft(root,self.spec())

    def test_registry_single_authority_optional_vault_and_update(self):
        root = self.repo(); spec = self.spec()
        spec.update(registry=True,create_vault=True,commands=[{'name':'check','argv':['python','-m','unittest'], 'cwd':'.','status':'observed','evidence':'README command'}])
        projects.apply(projects.draft(root,spec))
        self.assertTrue((root/'VAULT.md').exists())
        self.assertNotIn('unittest',(root/'AGENTS.md').read_text())
        registry=lib.read_json(root/'.agent/project.json'); registry['custom_note']='preserve'
        lib.save_json(root/'.agent/project.json',registry)
        spec['summary']='Revised'
        projects.apply(projects.draft(root,spec,update=True))
        self.assertEqual(lib.read_json(root/'.agent/project.json')['custom_note'],'preserve')
        self.assertFalse(projects.validate(root)['errors'])

    def test_import_examples_are_not_active_and_validation_finds_stale_source(self):
        root = self.repo(); spec = self.spec()
        (root/'CLAUDE.md').write_text('```text\n@AGENTS.md\n```\n')
        (root/'design.md').write_text('Requirements')
        spec['sources']=[{'role':'design','path':'design.md'}]
        projects.apply(projects.draft(root,spec))
        self.assertTrue(projects.imports_agents((root/'CLAUDE.md').read_text()))
        (root/'design.md').unlink()
        self.assertTrue(projects.validate(root,spec)['errors'])

    def test_canonical_skills_resolve_install_paths(self):
        rendered=configure.render(self.root/'home')
        self.assertIn('.agents/skills/eng-project-setup/SKILL.md', rendered)
        self.assertFalse(any(k.startswith('.codex/skills/') for k in rendered))
        for value in rendered.values():
            self.assertNotIn('{{SETUP_ROOT}}', value)
            self.assertNotIn('{{PYTHON}}', value)
        self.assertIn(str(lib.ROOT).replace('\\','/'),rendered['.agents/skills/eng-project-setup/SKILL.md'])

    def test_skill_reconciliation_and_retirement_roll_back_exactly(self):
        home=self.root/'home'; old='.codex/skills/eng-project-setup/SKILL.md'
        new='.agents/skills/eng-project-setup/SKILL.md'
        for name,content in ((old,b'legacy'),(new,b'local variation')):
            path=home/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(content)
        lib.save_json(configure.STATE/'deployment.json', {'home':str(home), 'files':[{'path':old,'after_hash':lib.digest(b'legacy')}]})
        with self.assertRaisesRegex(ValueError,'unmanaged'):
            configure.build(home,self.root/'plan.json')
        with self.assertRaisesRegex(ValueError,'changed'):
            configure.build(home,self.root/'plan.json',{new:'wrong'})
        plan=configure.build(home,self.root/'plan.json',{new:lib.digest(b'local variation')})
        release=configure.apply(plan,'fixture')
        self.assertFalse((home/old).exists())
        self.assertTrue((home/new).is_file())
        configure.rollback(release,'fixture')
        self.assertEqual((home/old).read_bytes(),b'legacy')
        self.assertEqual((home/new).read_bytes(),b'local variation')

    def test_owned_skill_drift_requires_reconciliation(self):
        home=self.root/'home'; plan=configure.build(home,self.root/'plan.json'); configure.apply(plan,'fixture')
        skill=home/'.agents/skills/eng-project-setup/SKILL.md'; skill.write_text('User edit')
        with self.assertRaisesRegex(ValueError,'local edits'):
            configure.build(home,self.root/'next.json')

    def test_empty_unmanaged_registry_and_bad_spec_fail_before_drafting(self):
        root = self.repo(); (root/'.agent').mkdir()
        registry = root/'.agent/project.json'; registry.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'registry'):
            projects.draft(root, dict(self.spec(), registry=True))
        self.assertEqual(registry.read_text(), '{}')
        for change in ({'sources': ['bad']}, {'commands': {}}, {'domains': [None]},
                       {'summary': projects.END_MARKER}, {'commands': [{'argv':['check'], 'cwd':'code.txt', 'status':'observed','evidence':'fixture'}]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                projects.prepare_spec(root, dict(self.spec(), **change))
        self.assertFalse((root/'AGENTS.md').exists())

    def test_crlf_bom_and_fenced_imports_are_preserved(self):
        root = self.repo(); agents = root/'AGENTS.md'; claude = root/'CLAUDE.md'
        prefix = b'\xef\xbb\xbfUser rules\r\n'
        agents.write_bytes(prefix); claude.write_bytes(b'\xef\xbb\xbf@AGENTS.md\r\n')
        projects.apply(projects.draft(root, self.spec()))
        agents.write_bytes(agents.read_bytes() + b'\r\nManual tail\r\n')
        projects.apply(projects.draft(root, dict(self.spec(), summary='New summary'), update=True))
        self.assertTrue(agents.read_bytes().startswith(prefix))
        self.assertTrue(agents.read_bytes().endswith(b'\r\nManual tail\r\n'))
        self.assertEqual(claude.read_bytes(), b'\xef\xbb\xbf@AGENTS.md\r\n')
        self.assertFalse(projects.imports_agents('~~~text\n@AGENTS.md\n~~~\n'))
        self.assertFalse(projects.imports_agents('```text\n@AGENTS.md\n'))

    def test_rollback_restores_deployment_record_and_rejects_old_release(self):
        home = self.root/'home'
        first = configure.apply(configure.build(home,self.root/'first.json'), 'fixture')
        first_manifest = (lib.STATE/'deployment.json').read_bytes()
        second = configure.apply(configure.build(home,self.root/'second.json'), 'fixture')
        with self.assertRaisesRegex(ValueError, 'current deployment'):
            configure.rollback(first, 'fixture')
        configure.rollback(second, 'fixture')
        self.assertEqual((lib.STATE/'deployment.json').read_bytes(), first_manifest)
        configure.rollback(first, 'fixture')
        self.assertFalse((lib.STATE/'deployment.json').exists())
