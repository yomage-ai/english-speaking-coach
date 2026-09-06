"""Real local HTTP and synthetic transcript worker; no learner Voice or account calls."""
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from practice_store import initialize,rebuild
from live_companion import LiveStore,LiveSupervisor
from library_server import Archive,Handler
from prepare_practice import prepare,readiness
from test_live_companion import FakeTranslator

THREAD='00000000-0000-0000-0000-000000000051'
SCENE={'setting':'A fictional hotel','learner_role':'Guest','partner_role':'Receptionist',
       'goal':'Check in','introduction':'你在酒店办理入住，你是客人，我是前台。',
       'opening_line':'Welcome! Do you have a reservation?'}


class QuietHandler(Handler):
    def log_message(self,*args):pass


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);initialize(self.root);rebuild(self.root)
        self.source=self.root/'voice.jsonl'
        self.source.write_text(json.dumps({'type':'session_meta','payload':{'id':THREAD}})+'\n')
        self.store=LiveStore(self.root)

    def test_no_companion_does_not_start_service_or_model(self):
        def forbidden(*args):self.fail('No service should be started')
        result=prepare(self.root,opener=forbidden,scene=SCENE)
        self.assertEqual(result['status'],'conversation_only');self.assertIsNone(self.store.active())

    def test_actual_http_preparation_reuses_binding_but_does_not_claim_ui_or_handoff(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        server.archive=Archive(self.root,Path(__file__).resolve().parents[1])
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        worker=LiveSupervisor(self.root,FakeTranslator);worker.start();self.addCleanup(worker.close)
        FakeTranslator.calls=0
        base=f'http://127.0.0.1:{server.server_port}'
        def opener(*args):return {'url':base+'/#live','service':{'manager':'isolated-test'}}
        first=prepare(self.root,THREAD,self.source,enable_companion=True,opener=opener,timeout=3,scene=SCENE)
        second=prepare(self.root,THREAD,self.source,opener=opener,timeout=3,scene=SCENE)
        self.assertEqual(first['status'],'backend_ready');self.assertEqual(first['binding'],second['binding'])
        self.assertFalse(first['checks']['transcript_observed'])
        self.assertEqual(first['checks']['page_display'],'not_verified')
        self.assertEqual(first['checks']['voice_handoff'],'not_verified')
        self.assertFalse(first['startup_complete']);self.assertEqual(first['context']['scene'],SCENE)
        self.assertIn(first['binding']['id'],first['url']);self.assertEqual(FakeTranslator.calls,0)

    def test_competing_task_and_wrong_source_cannot_replace_binding(self):
        current=self.store.bind(THREAD,self.source)
        result=prepare(self.root,'00000000-0000-0000-0000-000000000052',self.source,scene=SCENE)
        self.assertEqual(result['status'],'other_voice_active');self.assertEqual(self.store.active(),current)
        self.store.stop(current['id'],immediate=True)
        with self.assertRaises(ValueError):prepare(self.root,'wrong',self.source,scene=SCENE)
        self.assertEqual(self.store.active()['id'],current['id'])

    def test_service_failure_does_not_report_ready_or_leave_new_binding_requested(self):
        def broken(*args):raise OSError('Synthetic service failure')
        result=prepare(self.root,THREAD,self.source,enable_companion=True,opener=broken,scene=SCENE)
        self.assertEqual(result['status'],'preparation_error')
        self.assertFalse(result['checks']['backend_ready']);self.assertEqual(self.store.active()['desired'],'stopped')

    def test_saved_binding_without_heartbeat_is_not_readiness(self):
        def opener(*args):return {'url':'http://127.0.0.1:12345/#live'}
        result=prepare(self.root,THREAD,self.source,enable_companion=True,opener=opener,
                       reader=lambda base:self.store.view(),timeout=0,scene=SCENE)
        self.assertEqual(result['status'],'waiting_backend');self.assertFalse(result['checks']['backend_ready'])
        binding=result['binding'];data=self.store.view()
        data['state'].update(status='ended',ready=True,stale=False)
        self.assertEqual(readiness(data,binding),'ended')
        data['state']['id']='different';self.assertEqual(readiness(data,binding),'binding_changed')

    def test_missing_or_invalid_scene_cannot_bind_or_start_service(self):
        def forbidden(*args):self.fail('Incomplete scene must not start a service')
        result=prepare(self.root,THREAD,self.source,enable_companion=True,opener=forbidden)
        self.assertEqual(result['status'],'needs_scene')
        self.assertIsNone(result['context']['voice_brief']);self.assertIsNone(self.store.active())
        for invalid in ({}, {**SCENE,'goal':''}, {**SCENE,'goal':42}):
            with self.assertRaises(ValueError):
                prepare(self.root,THREAD,self.source,enable_companion=True,opener=forbidden,scene=invalid)
        self.assertIsNone(self.store.active())

    def test_parallel_bindings_have_one_winner(self):
        other=self.root/'other.jsonl';tid='00000000-0000-0000-0000-000000000052'
        other.write_text(json.dumps({'type':'session_meta','payload':{'id':tid}})+'\n')
        gate=threading.Barrier(2)
        def bind(args):
            gate.wait()
            try:return self.store.bind(*args)['thread_id']
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(bind,[(THREAD,self.source),(tid,other)]))
        self.assertEqual(sum(r is not None for r in results),1)
        self.assertIn(self.store.active()['thread_id'],[r for r in results if r])
        with self.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],1)


if __name__=='__main__':unittest.main()
