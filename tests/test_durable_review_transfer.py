"""Real temporary archives and interrupted-job checks; no microphone or model calls."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import practice_store as store
from archive_transfer import backup_bytes, inspect_backup, restore_backup, adopt_existing, move_archive, counts
from review_worker import ReviewWorker, enqueue, quality_check, worker_lock
from practice_runtime import review_status, set_review_stage, review_file
from library_server import LibraryServer, Handler
import test_review_pipeline as fixtures
THREAD,VOICE=fixtures.THREAD,fixtures.VOICE

class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.root=self.base/'old'
        store.initialize(self.root);store.rebuild(self.root)
        self.config=self.base/'machine/workspace.json'
        store.write_json(self.config,{'schema_version':1,'data_root':str(self.root),'project_page':None})
        self.page=self.base/'project.md';self.page.write_text('# Private learning goal\nA fictional project.')
        (self.root/'Notes').mkdir();(self.root/'Notes/custom.md').write_text('User notes must survive.')
        self.before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_full_roundtrip_preserves_notes_profile_context_and_old_directory(self):
        blob,manifest=backup_bytes(self.root,self.page)
        self.assertTrue(manifest['includes_project_page']);self.assertFalse(manifest['includes_live'])
        target=self.base/'restored'
        result=restore_backup(blob,target,self.config)
        cfg=json.loads(self.config.read_text())
        self.assertEqual(cfg['data_root'],str(target))
        self.assertEqual(Path(cfg['project_page']).read_bytes(),self.page.read_bytes())
        self.assertEqual(counts(target),counts(self.root))
        for name,value in self.before.items():
            self.assertEqual((self.root/name).read_bytes(),value)
            if name not in {'dashboard.html','state.json','INDEX.md'}:
                self.assertEqual((target/name).read_bytes(),value)
        self.assertTrue(list((self.config.parent/'location-history').glob('*.json')))
        self.assertEqual(result['status'],'restored')

    def test_restore_refuses_nonempty_and_corrupted_zip_and_traversal(self):
        blob,_=backup_bytes(self.root)
        with self.assertRaisesRegex(ValueError,'空目录'):restore_backup(blob,self.root,self.config)
        for name,payload in [('data/profile.json',b'{}'),('../outside.txt',b'oops')]:
            with zipfile.ZipFile(io.BytesIO(blob)) as old:
                parts={n:old.read(n) for n in old.namelist()}
            parts[name]=payload
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as z:
                for n,b in parts.items():z.writestr(n,b)
            with self.assertRaises(ValueError):restore_backup(out.getvalue(),self.base/'bad',self.config)
            self.assertFalse((self.base/'bad').exists())
        self.assertEqual(json.loads(self.config.read_text())['data_root'],str(self.root))

    def test_adopt_existing_when_old_drive_is_missing_and_no_merge(self):
        other=self.base/'copied';store.initialize(other);store.rebuild(other)
        store.write_json(self.config,{'schema_version':1,'data_root':str(self.base/'missing-drive'),'project_page':None})
        result=adopt_existing(other,self.config)
        self.assertEqual(result['status'],'adopted')
        self.assertEqual(json.loads(self.config.read_text())['data_root'],str(other))
        self.assertFalse((self.base/'missing-drive').exists())

    def test_move_preserves_external_context_and_rejects_nested_destination(self):
        result=move_archive(self.root,self.base/'new',self.page,self.config)
        self.assertEqual(result['source_retained'],str(self.root))
        self.assertEqual(Path(result['configuration']['project_page']).read_bytes(),self.page.read_bytes())
        with self.assertRaises(ValueError):move_archive(self.root,self.root/'inside',config_path=self.config)

    def test_backup_does_not_follow_external_symlinks(self):
        (self.root/'external').symlink_to(self.page)
        with self.assertRaisesRegex(ValueError,'符号链接'):backup_bytes(self.root)

    def test_restored_runtime_never_auto_calls_an_old_machine_source(self):
        set_review_stage(self.root,THREAD,VOICE,'queued',auto_review=True,source='/old/machine/private.jsonl')
        blob,_=backup_bytes(self.root)
        # Simulate recovering on a new computer with the old drive absent.
        store.write_json(self.config,{'schema_version':1,'data_root':str(self.base/'missing'),'project_page':None})
        restore_backup(blob,self.base/'restored',self.config)
        job=review_status(self.base/'restored',THREAD,VOICE)
        self.assertFalse(job['auto_review']);self.assertEqual(job['status'],'error')
        self.assertNotIn('source',job)

    def test_server_switches_root_and_restarts_from_machine_config(self):
        server=LibraryServer(('127.0.0.1',0),self.root,workspace=True,config_path=self.config,background=False)
        self.addCleanup(server.server_close)
        target=self.base/'new'
        preview=server.storage.preview({'action':'move','destination':str(target)})
        self.assertEqual(json.loads(self.config.read_text())['data_root'],str(self.root))
        server.storage.apply({'plan':preview['plan']})
        self.assertEqual(server.archive.root,target)
        from workspace_config import resolve_workspace
        restarted=LibraryServer(('127.0.0.1',0),Path(resolve_workspace(config_path=self.config)['data_root']),workspace=True,background=False)
        self.addCleanup(restarted.server_close)
        self.assertEqual(restarted.archive.query('/api/identity',{})['data_root'],str(target))
        self.assertEqual(restarted.archive.query('/api/overview',{})['counts']['sessions'],0)

    def test_preview_detects_intervening_source_change(self):
        server=LibraryServer(('127.0.0.1',0),self.root,workspace=True,config_path=self.config,background=False)
        self.addCleanup(server.server_close)
        plan=server.storage.preview({'action':'move','destination':str(self.base/'new')})
        (self.root/'Notes/custom.md').write_text('New note')
        with self.assertRaisesRegex(ValueError,'源档案已改变'):server.storage.apply({'plan':plan['plan']})
        self.assertFalse((self.base/'new').exists())

class WorkerTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.ReviewPipelineTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.root,self.source,self.draft=fixture.root,fixture.source,deepcopy(fixture.draft)
        self.draft['concept_observations']=[{'term':'discount','meaning':'折扣','dimension':'use','result':'needs_help','support':'none','quote':'折扣怎么说','note':'Learner requested wording.','source_turn_ids':['u4'],'expression_indices':[4]}]
        self.draft['word_checks']=[{'segment_id':'u'+str(i),'needs_word_help':i==4,
            'reason':'Explicit word request' if i==4 else 'No separate word request','concept_indices':[0] if i==4 else []} for i in range(6)]
        self.draft['reading_omissions']={str(i):'Fictional simple-phrase fixture; quality is tested separately.' for i in range(5)}
        self.calls=[]
        draft,calls=self.draft,self.calls
        class Client:
            def generate(self,payload,feedback=None):
                calls.append(payload);return deepcopy(draft),.01
            def close(self):pass
        self.worker=ReviewWorker(self.root,factory=Client)

    def test_auto_end_saves_without_parent_chat_and_duplicate_does_not_call_model(self):
        set_review_stage(self.root,THREAD,VOICE,'practicing',auto_review=True,source=str(self.source))
        self.assertTrue(self.worker.tick())
        self.assertEqual(review_status(self.root,THREAD,VOICE)['status'],'saved')
        self.assertEqual(len(self.calls),1)
        self.assertFalse(self.worker.tick())
        self.assertEqual(enqueue(self.root,THREAD,VOICE,self.source)['status'],'saved')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(store.build_state(self.root)['sessions']),1)

    def test_active_voice_does_not_generate_or_save(self):
        self.source.write_text('\n'.join(self.source.read_text().splitlines()[:-1])+'\n')
        set_review_stage(self.root,THREAD,VOICE,'practicing',auto_review=True,source=str(self.source))
        self.assertFalse(self.worker.tick())
        self.assertEqual(self.calls,[])
        self.assertEqual(store.build_state(self.root)['sessions'],[])

    def test_saved_draft_resumes_after_process_death_without_model_call(self):
        enqueue(self.root,THREAD,VOICE,self.source)
        path=review_file(self.root,THREAD,VOICE).with_suffix('.draft')
        store.write_json(path,self.draft)
        set_review_stage(self.root,THREAD,VOICE,'checking')
        self.worker.tick()
        self.assertEqual(self.calls,[]);self.assertFalse(path.exists())
        self.assertEqual(review_status(self.root,THREAD,VOICE)['status'],'saved')

    def test_two_workers_cannot_generate_same_job(self):
        enqueue(self.root,THREAD,VOICE,self.source)
        with worker_lock(self.root) as owned:
            self.assertTrue(owned)
            self.assertFalse(self.worker.tick())
        self.assertEqual(self.calls,[])
        self.worker.tick();self.assertEqual(len(self.calls),1)

    def test_word_help_is_not_satisfied_by_sentence_coverage_alone(self):
        from recover_voice import snapshot_voice
        snapshot=snapshot_voice(self.source,THREAD,VOICE)
        quality_check(self.draft,snapshot)
        bad=deepcopy(self.draft);bad['word_checks'][4]['concept_indices']=[]
        with self.assertRaisesRegex(ValueError,'concept observation'):quality_check(bad,snapshot)
        bad=deepcopy(self.draft);bad['reading_omissions']={}
        with self.assertRaisesRegex(ValueError,'reading guidance'):quality_check(bad,snapshot)

    def test_bad_draft_is_preserved_and_error_requires_explicit_retry(self):
        enqueue(self.root,THREAD,VOICE,self.source)
        self.draft['word_checks'][4]['concept_indices']=[]
        self.worker.tick()
        self.assertEqual(review_status(self.root,THREAD,VOICE)['status'],'error')
        self.assertTrue(review_file(self.root,THREAD,VOICE).with_suffix('.draft').exists())
        before=len(self.calls);self.worker.tick();self.assertEqual(len(self.calls),before)
        self.assertEqual(enqueue(self.root,THREAD,VOICE,self.source,retry=True)['status'],'queued')

if __name__=='__main__':unittest.main()


class FirstUseAndGuideTests(unittest.TestCase):
    def test_pristine_text_resume_initializes_external_default_without_folder_dialog(self):
        import os,subprocess
        with tempfile.TemporaryDirectory() as tmp:
            env={**os.environ,'CODEX_HOME':str(Path(tmp).resolve())}
            result=subprocess.run([sys.executable,str(Path(store.__file__)),'resume','--compact'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            config=json.loads((Path(tmp)/'english-speaking-coach/workspace.json').read_text())
            self.assertEqual(Path(config['data_root']),Path(tmp).resolve()/'english-speaking-coach/data')
            self.assertEqual(data['profile']['practice_language'],'english_first')

    def test_pristine_voice_preparation_initializes_without_waiting_for_translation(self):
        from prepare_practice import prepare
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data';cfg=Path(tmp)/'workspace.json'
            with patch('prepare_practice.resolve_workspace',return_value={'data_root':str(root),'mode':'user-data','config_path':str(cfg),'project_page':None}):
                result=prepare(auto_scene=True)
            self.assertEqual(result['status'],'needs_voice_task')
            self.assertTrue((root/'profile.json').exists());self.assertTrue(cfg.exists())

    def test_short_question_reading_keeps_words_together_and_separates_memory_pattern(self):
        from reading_guidance import stabilize_basic_guides,validate_guide
        guide={'kind':'suggestion','groups':[{'text':'How much is','stress':['much']},{'text':'each one?','stress':['each']}],'tone':'rise','tone_note':'Question rises','memory':[{'text':'How much is …?','meaning':'询问价格'}]}
        fixed=stabilize_basic_guides({'expressions':[{'english':'How much is each one?','reading_guide':guide}]})['expressions'][0]['reading_guide']
        self.assertEqual(len(fixed['groups']),1);self.assertEqual(fixed['tone'],'fall')
        self.assertEqual(fixed['memory'],guide['memory']);validate_guide(fixed,'How much is each one?')
        self.assertEqual(len(guide['groups']),2,'Input remains unchanged')

    def test_storage_route_is_readable_when_old_root_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing=Path(tmp)/'missing';cfg=Path(tmp)/'workspace.json'
            store.write_json(cfg,{'schema_version':1,'data_root':str(missing),'project_page':None})
            server=LibraryServer(('127.0.0.1',0),missing,workspace=True,config_path=cfg,background=False)
            try:
                self.assertFalse(server.storage.info()['available'])
                self.assertEqual(server.archive.query('/api/storage',{})['data_root'],str(missing.resolve()))
                copied=Path(tmp)/'copied';store.initialize(copied);store.rebuild(copied)
                plan=server.storage.preview({'action':'adopt','destination':str(copied)})
                server.storage.apply({'plan':plan['plan']})
                self.assertEqual(server.archive.root,copied.resolve());self.assertFalse(missing.exists())
            finally:server.server_close()


class ReviewTransportTests(unittest.TestCase):
    def test_short_transport_ids_roundtrip_without_rewriting_quotes(self):
        from review_worker import map_turn_ids
        ids={'very-long-actual-source-id':'t1'}
        source={'transcript':[{'id':'very-long-actual-source-id','text':'very-long-actual-source-id'}],
            'prior_draft':{'expressions':[{'source_turn_ids':['very-long-actual-source-id'],'original':'very-long-actual-source-id'}],
                           'omitted_turns':{'very-long-actual-source-id':'A greeting'},
                           'word_checks':[{'segment_id':'very-long-actual-source-id'}]}}
        mapped=map_turn_ids(source,ids)
        self.assertEqual(mapped['transcript'][0],{'id':'t1','text':'very-long-actual-source-id'})
        self.assertEqual(mapped['prior_draft']['expressions'][0]['original'],'very-long-actual-source-id')
        self.assertEqual(mapped['prior_draft']['omitted_turns'],{'t1':'A greeting'})
        self.assertEqual(map_turn_ids(mapped,{v:k for k,v in ids.items()}),source)

    def test_review_timeout_does_not_claim_translation_failed(self):
        from review_worker import ReviewClient
        with patch('codex_translation.CodexTranslator.receive',side_effect=ValueError('翻译连接超时')):
            with self.assertRaisesRegex(ValueError,'复盘模型'):
                ReviewClient().receive(0)

    def test_bad_optional_guide_and_redundant_omission_do_not_lose_selected_evidence(self):
        from review_worker import reconcile_annotations
        draft={'expressions':[{'source_turn_ids':['a'],'english':"Okay, I'll buy it. Can I pay by card?",'original':'I buy it. Card okay?',
            'reading_guide':{'kind':'suggestion','groups':[{'text':'Can I pay by card?','stress':['card']}],
              'tone':'rise','tone_note':'A polite question.','memory':[{'text':'Can I ...?','meaning':'Request permission'}]}}],
            'concept_observations':[],'omitted_turns':{'a':'Also chosen','b':'A greeting'}}
        fixed=reconcile_annotations(draft,'en')
        self.assertEqual(fixed['omitted_turns'],{'b':'A greeting'})
        self.assertNotIn('reading_guide',fixed['expressions'][0])
        self.assertIn('withheld',fixed['expressions'][0]['note'])
        self.assertEqual(fixed['expressions'][0]['english'],draft['expressions'][0]['english'])
        self.assertEqual(fixed['expressions'][0]['source_turn_ids'],['a'])
        self.assertIn('0',fixed['reading_omissions'])
