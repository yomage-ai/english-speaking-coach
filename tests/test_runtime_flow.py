"""Regression checks for startup variety, review state and scoped card data."""
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import practice_store as store
from practice_runtime import choose_scene, remember_scene, scene_for_binding, begin_review, review_status, review_file, code_revision
from prepare_practice import prepare
from library_server import Archive, SKILL_ROOT
from library_service import check_service
from test_fast_practice import record, THREAD, VOICE, OTHER_VOICE
from test_prepare_practice import SCENE
from test_live_companion import event
from live_companion import LiveStore


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);store.initialize(self.root);store.rebuild(self.root)

    def test_selected_but_unsaved_scenes_rotate_and_retry_keeps_scene(self):
        context=store.resume(self.root,'2026-01-01')
        chosen=[]
        for index in range(8):
            scene=choose_scene(self.root,context)
            chosen.append(scene['setting']);remember_scene(self.root,str(index),scene)
        self.assertEqual(len(set(chosen)),8)
        self.assertEqual(scene_for_binding(self.root,'7')['setting'],chosen[-1])
        self.assertEqual(store.build_state(self.root)['sessions'],[])

    def test_auto_prepare_is_one_context_read_and_retry_is_idempotent(self):
        source=self.root/'source.jsonl'
        source.write_text(json.dumps({'type':'session_meta','payload':{'id':THREAD}})+'\n')
        live=LiveStore(self.root)
        def reader(base):
            data=live.view();data['state'].update(ready=True,stale=False);return data
        args=dict(root=self.root,thread_id=THREAD,source=source,auto_scene=True,
                  opener=lambda *args:{'url':'http://127.0.0.1:12345'},reader=reader,timeout=0)
        with patch('prepare_practice.resume',wraps=store.resume) as resume:
            first=prepare(**args)
            self.assertEqual(resume.call_count,1)
        second=prepare(**args)
        self.assertEqual(first['binding'],second['binding'])
        self.assertEqual(first['context']['scene'],second['context']['scene'])
        self.assertEqual(first['status'],'backend_ready')
        self.assertLess(first['timing']['local_preparation_ms'],2000)

    def test_review_state_is_exact_voice_and_saved_record_wins(self):
        before=store.build_state(self.root)
        self.assertEqual(review_status(self.root,THREAD,VOICE)['status'],'waiting')
        first=begin_review(self.root,THREAD,VOICE)
        self.assertEqual(begin_review(self.root,THREAD,VOICE),first)
        self.assertEqual(review_status(self.root,THREAD,VOICE)['status'],'preparing')
        self.assertEqual(review_status(self.root,THREAD,OTHER_VOICE)['status'],'waiting')
        self.assertEqual(store.build_state(self.root),before)
        first['started_epoch']=time.time()-181
        store.write_json(review_file(self.root,THREAD,VOICE),first)
        archive=Archive(self.root,SKILL_ROOT)
        self.assertEqual(archive.query('/api/review',dict(thread=THREAD,voice=VOICE))['status'],'needs_attention')
        store.commit(self.root,record())
        self.assertEqual(archive.query('/api/review',dict(thread=THREAD,voice=VOICE))['status'],'saved')

    def test_theme_counts_use_same_session_as_cards_and_global_scope_is_reachable(self):
        store.commit(self.root,record())
        other=record(OTHER_VOICE,'SES-20260102-001');other['date']='2026-01-02'
        other['expressions'][0].update(id='EXP-20260102-001',english='Where is the library?',chinese='图书馆在哪？')
        store.commit(self.root,other)
        archive=Archive(self.root,SKILL_ROOT)
        filtered=archive.query('/api/terms',{'session':'SES-20260101-001'})
        self.assertEqual(filtered['total'],1);self.assertEqual(filtered['pages'],1)
        self.assertEqual(sum(b['count'] for b in filtered['books']),1)
        self.assertEqual(filtered['scope']['all_count'],2)
        self.assertEqual(filtered['scope']['session_title'],'Synthetic practice')
        self.assertEqual(archive.query('/api/terms',{})['total'],2)

    def test_running_old_code_cannot_be_claimed_as_updated(self):
        identity={'application':'english-speaking-coach','pid':1,'data_root':str(self.root),'skill_root':str(SKILL_ROOT),'code_revision':'old'}
        with patch('library_service.urlopen',return_value=io.StringIO(json.dumps(identity))):
            with self.assertRaisesRegex(ValueError,'outdated'):
                check_service('http://127.0.0.1:12345',self.root)
        self.assertEqual(len(code_revision(SKILL_ROOT)),16)

    def test_latest_window_never_shrinks_to_one_item_at_a_page_boundary(self):
        source=self.root/'source.jsonl'
        from test_live_companion import THREAD as LIVE_THREAD
        source.write_text(json.dumps({'type':'session_meta','payload':{'id':LIVE_THREAD}})+'\n')
        live=LiveStore(self.root);state=live.bind(LIVE_THREAD,source)
        with source.open('a') as stream:
            stream.write(json.dumps(event('realtime_session_started'))+'\n')
            for n in range(41):stream.write(json.dumps(event(id=str(n)))+'\n')
        live.read_tail(state)
        latest=live.view();older=live.view({'page':'1'})
        self.assertEqual(len(latest['items']),40)
        self.assertEqual(latest['items'][0]['id'],'1');self.assertEqual(latest['items'][-1]['id'],'40')
        self.assertEqual(older['items'][0]['id'],'0')


if __name__=='__main__':unittest.main()
