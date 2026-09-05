import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import practice_store as store
import practice_view
import serve_practice

class PracticeStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = Path(self.temp.name)
        self.root = store.project_dir(self.vault)
        store.initialize(self.root)
        store.rebuild(self.root)

    def payload(self, items=True):
        return {'id':'SES-20260905-001','date':'2026-09-05','title':'A daily plan', 'summary':'A selected speaking observation.', 'source_ids':['test:utterance-1'], 'progress':['Asked for clarification.'], 'next_focus':['Tomorrow’s plan'], 'end_status':'ended', 'expressions':[{'id':'EXP-20260905-001','original':'I like go beach','english':"I'd like to go to the beach.",'chinese':'我想去海边。','mastery':'source_text','next_review':'2026-09-06','note':'Repeated after the full model.','review_result':'partial','review_prompt':'source_text'}] if items else []}

    def hashes(self):
        import hashlib
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}

    def cli(self, command, **kwargs):
        args = [sys.executable,str(SCRIPTS/'practice_store.py'),'--vault',str(self.vault),command]
        for k,v in kwargs.items(): args += ['--'+k,str(v)]
        return subprocess.run(args,capture_output=True,text=True)

    def test_empty_session_roundtrip(self):
        store.commit(self.root, self.payload(False))
        (self.root/'state.json').unlink()
        store.rebuild(self.root)
        result=store.validate(self.root)
        self.assertTrue(result['ok']); self.assertEqual(result['sessions'],1); self.assertEqual(result['expressions'],0)

    def test_duplicate_preserves_user_notes(self):
        data=self.payload(); store.commit(self.root,data)
        path=self.root/'Sessions'/f"{data['id']}.md"
        with path.open('a') as f: f.write('\nMy own note.\n')
        store.rebuild(self.root)
        before=self.hashes()
        self.assertEqual(store.commit(self.root,data)['status'],'already_saved')
        self.assertEqual(before,self.hashes())
        self.assertIn('My own note.',(self.root/'dashboard.html').read_text())
        data['summary']='Different'
        with self.assertRaisesRegex(ValueError,'Conflicting session'):store.commit(self.root,data)
        self.assertEqual(before,self.hashes())

    def test_failed_view_generation_recovers(self):
        data=self.payload()
        with patch.object(practice_view,'render',side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):store.commit(self.root,data)
        self.assertTrue((self.root/'Pending'/f"{data['id']}.json").exists())
        result=self.cli('recover');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(store.validate(self.root)['sessions'],1)
        self.assertEqual(list((self.root/'Pending').glob('*.json')),[])

    def test_pending_before_markdown_recovers(self):
        data=self.payload();store.write_json(self.root/'Pending'/f"{data['id']}.json",data)
        self.assertEqual(self.cli('recover').returncode,0)
        self.assertEqual(store.validate(self.root)['sessions'],1)

    def test_unfinished_is_not_completed(self):
        data=self.payload(False);data['end_status']='in_progress'
        store.write_json(self.root/'Pending'/f"{data['id']}.json",data)
        result=self.cli('recover');self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('needs_session_context',result.stdout)
        self.assertEqual(store.validate(self.root)['sessions'],0)

    def test_conflicting_pending_not_replaced(self):
        data=self.payload();store.write_json(self.root/'Pending'/f"{data['id']}.json",data)
        altered=self.payload();altered['summary']='unrelated'
        with self.assertRaisesRegex(ValueError,'Conflicting ended'):store.commit(self.root,altered)
        self.assertEqual(store.read_json(self.root/'Pending'/f"{data['id']}.json"),data)

    def test_resume_validate_read_only(self):
        store.commit(self.root,self.payload());before=self.hashes()
        self.assertEqual(self.cli('resume',today='2026-09-07').returncode,0)
        self.assertEqual(self.cli('validate').returncode,0)
        self.assertEqual(self.hashes(),before)
        missing=self.vault/'not-created'
        p=subprocess.run([sys.executable,str(SCRIPTS/'practice_store.py'),'--vault',str(missing),'validate'],capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertFalse(missing.exists())

    def test_untrusted_text_and_source_links(self):
        data=self.payload();data['summary']='</script><script>alert(1)</script>'
        data['expressions'][0]['english']='Hi <!-- speaking-record-v2 --> <img src=x onerror=alert(1)>'
        store.commit(self.root,data)
        self.assertEqual(store.extract(self.root/'Sessions'/f"{data['id']}.md",store.MARKER),data)
        page=(self.root/'dashboard.html').read_text()
        self.assertNotIn('<img src=x',page)
        self.assertIn('&lt;img src=x',page)
        self.assertIn('href="Sessions/SES-20260905-001.md"',page)
        self.assertIn('id="session-SES-20260905-001"',page)

    def test_invalid_ids_and_false_mastery(self):
        for bad in ('SES-../../x','SES-20260904-001'):
            data=self.payload();data['id']=bad
            with self.assertRaises(ValueError):store.validate_payload(data)
        data=self.payload();data['expressions'][0]['mastery']='independent'
        with self.assertRaises(ValueError):store.validate_payload(data)
        data=self.payload();data['source_ids']=[]
        with self.assertRaises(ValueError):store.validate_payload(data)

    def test_retrieval_updates_one_expression(self):
        data=self.payload();store.commit(self.root,data)
        later=self.payload();later.update(id='SES-20260907-001',date='2026-09-07')
        later['expressions'][0].update(mastery='independent',review_result='success',review_prompt='none',next_review='2026-09-14',note='Used after a delay with no prompt.')
        store.commit(self.root,later)
        state=store.build_state(self.root)
        self.assertEqual(len(state['expressions']),1)
        self.assertEqual(len(state['expressions'][0]['attempts']),2)
        self.assertEqual(state['expressions'][0]['mastery'],'independent')

    def test_preferences_survive_rebuild(self):
        changes=self.vault/'changes.json';store.write_json(changes,{'mode':'roleplay','source_ids':['test:user-choice'],'updated':'2026-09-05'})
        self.assertEqual(self.cli('set-preferences',input=changes).returncode,0)
        store.rebuild(self.root)
        self.assertEqual(store.resume(self.root,'2026-09-05')['profile']['mode'],'roleplay')

    def test_legacy_migration_exact_preservation(self):
        (self.root/'Archive'/'legacy-v1.md').unlink()
        old=store.baseline();old['sessions']=[{'id':'SES-20260901-001','date':'2026-09-01','title':'Old note','next_focus':[]}]
        old['expressions']=[{'id':'EXP-20260901-001','english':'Hello.','chinese':'你好','mastery':'source_text','next_review':'2026-09-02','note':'Old','source_session':'SES-20260901-001','seen_in_sessions':['SES-20260901-001'],'attempts':[{'date':'2026-09-01','session':'SES-20260901-001','result':'partial','prompt':'source_text'}],'updated':'2026-09-01'}]
        path=self.root/'Sessions'/'SES-20260901-001.md';path.write_text('# My old note\n用户自己的补充。\n')
        store.write_json(self.root/'state.json',old);original=path.read_bytes()
        store.initialize(self.root);store.rebuild(self.root)
        (self.root/'state.json').unlink();store.rebuild(self.root)
        self.assertEqual(store.read_json(self.root/'state.json')['expressions'],old['expressions'])
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(store.validate(self.root)['legacy_notes_changed'],[])

    def test_legacy_view_uses_original_table(self):
        session={'id':'SES-20260901-002','date':'2026-09-01','title':'Original table'}
        (self.root/'Sessions'/'SES-20260901-002.md').write_text('## 精选表达与证据\n\n| 用户原话 | 推荐表达 | 中文意思 | 问题标签 | 掌握状态 | 下次复习 |\n| --- | --- | --- | --- | --- | --- |\n| My old words | My improved words | 中文 | 标签 | 需要原文 | 2026-09-02 |\n')
        record,_=practice_view.read_record(self.root,session,{'expressions':[{'english':'Unrelated latest wording'}]})
        self.assertEqual(record['expressions'][0]['original'],'My old words')
        self.assertEqual(record['expressions'][0]['english'],'My improved words')

    def test_server_only_serves_journal_and_records(self):
        from http.server import ThreadingHTTPServer
        store.commit(self.root,self.payload())
        server=ThreadingHTTPServer(('127.0.0.1',0),serve_practice.handler(self.root))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base='http://127.0.0.1:'+str(server.server_port)
        self.assertEqual(urlopen(base+'/dashboard.html').status,200)
        self.assertTrue(urlopen(base+'/Sessions/SES-20260905-001.md').headers['Content-Type'].startswith('text/plain'))
        for path in ('/state.json','/profile.json','/../state.json','/Archive/legacy-v1.md','/'):
            if path=='/':continue
            with self.assertRaises(HTTPError) as error:urlopen(base+path)
            self.assertEqual(error.exception.code,404)
            error.exception.close()

if __name__=='__main__':unittest.main()
