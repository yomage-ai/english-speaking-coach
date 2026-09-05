from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
import tempfile
import unittest
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import practice_store as store
import learning_progress as progress
import workspace_config as config

class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'records';store.initialize(self.root);store.rebuild(self.root)
    def event(self,id='OBS-test-001',dimension='use',result='supported',support='model',context='Morning commute',modality='transcript'):
        return {'id':id,'concept_id':'CON-commute','term':'commute','meaning':'通勤','dimension':dimension,'result':result,'support':support,'context':context,'modality':modality,'quote_kind':'utterance','quote':'I commute by train.','note':'Synthetic test evidence only.','expression_ids':[]}
    def session(self,day,events):
        return {'id':'SES-'+day.replace('-','')+'-001','date':day,'title':'Synthetic fixture','summary':'Test only','source_ids':['test:fixture'],'expressions':[],'concept_observations':events}
    def concept(self):return store.build_state(self.root)['concepts'][0]
    def test_explanation_is_not_understanding(self):
        e=self.event(dimension='meaning',result='explained');e['quote_kind']='session_note'
        store.commit(self.root,self.session('2026-09-01',[e]))
        self.assertFalse(self.concept()['dimensions']['meaning']['successful'])
        self.assertEqual(self.concept()['level'],'encountered')
    def test_text_cannot_prove_fluent_reading(self):
        e=self.event(dimension='reading',result='success',support='model')
        with self.assertRaisesRegex(ValueError,'audio'):store.commit(self.root,self.session('2026-09-01',[e]))
        self.assertEqual(list((self.root/'Sessions').glob('*.md')),[])
        e['modality']='audio';store.commit(self.root,self.session('2026-09-01',[e]))
        c=self.concept();self.assertTrue(c['dimensions']['reading']['successful']);self.assertFalse(c['dimensions']['use']['successful']);self.assertNotEqual(c['level'],'stable')
    def test_supplied_sentence_is_not_independent(self):
        e=self.event(result='success')
        with self.assertRaisesRegex(ValueError,'supplied answer'):store.commit(self.root,self.session('2026-09-01',[e]))
    def test_cross_day_context_and_later_difficulty(self):
        first=self.session('2026-09-01',[self.event(result='success',support='none'),self.event(id='OBS-test-002',result='success',support='none',context='Weekend plans')])
        store.commit(self.root,first);self.assertEqual(self.concept()['level'],'independent')
        store.commit(self.root,self.session('2026-09-03',[self.event(id='OBS-test-003',result='success',support='none',context='Weekend plans')]))
        self.assertEqual(self.concept()['level'],'stable')
        store.commit(self.root,self.session('2026-09-04',[self.event(id='OBS-test-004')]))
        c=self.concept();self.assertTrue(c['needs_revisit']);self.assertEqual(c['level'],'supported');self.assertEqual(len(c['events']),4)
    def test_sense_conflict_rejected_before_write(self):
        store.commit(self.root,self.session('2026-09-01',[self.event()]))
        e=self.event(id='OBS-test-002');e['meaning']='another sense'
        with self.assertRaisesRegex(ValueError,'different term or meaning'):store.commit(self.root,self.session('2026-09-03',[e]))
        self.assertFalse((self.root/'Sessions/SES-20260903-001.md').exists())
    def test_same_id_retries_and_conflicts(self):
        s=self.session('2026-09-01',[self.event()]);store.commit(self.root,s);store.commit(self.root,s)
        self.assertEqual(len(self.concept()['events']),1)
        with self.assertRaisesRegex(ValueError,'Conflicting observation'):store.commit(self.root,self.session('2026-09-02',[self.event()]))
    def test_historical_supplement_preserves_original(self):
        s=self.session('2026-09-01',[]);store.commit(self.root,s)
        source=self.root/'Sessions'/f"{s['id']}.md";before=source.read_bytes()
        data={'id':'EVD-20260901-001','session':s['id'],'date':s['date'],'source_ids':['test:fixture'],'reason':'Extracting existing test evidence only','concept_observations':[self.event()]}
        progress.save_evidence(self.root,data);progress.save_evidence(self.root,data);store.rebuild(self.root)
        self.assertEqual(source.read_bytes(),before);self.assertEqual(len(self.concept()['events']),1)
        data['reason']='conflict'
        with self.assertRaisesRegex(ValueError,'Conflicting evidence'):progress.save_evidence(self.root,data)

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.cfg=self.base/'machine/workspace.json';self.skill=self.base/'skill';self.legacy=self.base/'legacy'
    def resolve(self):return config.resolve_workspace(config_path=self.cfg,skill_root=self.skill,legacy_root=self.legacy)
    def test_new_user_default_and_custom_override(self):
        self.assertEqual(Path(self.resolve()['data_root']),self.skill/'data')
        self.cfg.parent.mkdir();self.cfg.write_text(json.dumps({'schema_version':1,'data_root':str(self.base/'custom'),'project_page':None}))
        self.assertEqual(Path(self.resolve()['data_root']),self.base/'custom')
        self.assertFalse((self.base/'custom').exists())
    def test_existing_archive_wins_over_new_default(self):
        self.legacy.mkdir();(self.legacy/'Sessions').mkdir();(self.legacy/'state.json').write_text('{}')
        self.assertEqual(self.resolve()['mode'],'existing-vault')
    def test_copy_migration_preserves_source_and_changes_config_last(self):
        source=self.base/'source';store.initialize(source);store.rebuild(source)
        self.cfg.parent.mkdir();self.cfg.write_text(json.dumps({'schema_version':1,'data_root':str(source),'project_page':None}))
        dest=self.base/'destination';before={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'copy-existing'):config.configure(dest,config_path=self.cfg)
        config.configure(dest,copy_existing=True,config_path=self.cfg)
        self.assertEqual(json.loads(self.cfg.read_text())['data_root'],str(dest))
        for name,digest in before.items():
            self.assertEqual(hashlib.sha256((source/name).read_bytes()).hexdigest(),digest);self.assertEqual(hashlib.sha256((dest/name).read_bytes()).hexdigest(),digest)
    def test_nonempty_destination_and_missing_configured_source_fail_closed(self):
        source=self.base/'source';store.initialize(source);store.rebuild(source)
        self.cfg.parent.mkdir();self.cfg.write_text(json.dumps({'schema_version':1,'data_root':str(source)}))
        dest=self.base/'nonempty';dest.mkdir();(dest/'my-note.md').write_text('keep')
        with self.assertRaisesRegex(ValueError,'not empty'):config.configure(dest,copy_existing=True,config_path=self.cfg)
        self.cfg.write_text(json.dumps({'schema_version':1,'data_root':str(self.base/'missing')}))
        with self.assertRaisesRegex(ValueError,'unavailable'):config.configure(self.base/'new',copy_existing=True,config_path=self.cfg)
        self.assertFalse((self.base/'new').exists())
    def test_embedded_backup_outside_skill(self):
        root=self.skill/'data';store.initialize(root);store.rebuild(root)
        (root/'Live').mkdir();(root/'Live'/'cache.txt').write_text('Synthetic transient transcript')
        with patch.object(config,'SKILL_ROOT',self.skill),patch.object(config,'CONFIG_PATH',self.cfg):
            result=config.backup_embedded_data(root)
        import zipfile
        with zipfile.ZipFile(result) as z:
            self.assertIn('Archive/legacy-v1.md',z.namelist());self.assertIsNone(z.testzip())
            self.assertFalse(any(name.startswith('Live/') for name in z.namelist()))
        self.assertNotIn(self.skill,Path(result).parents)

if __name__=='__main__':unittest.main()
