"""Finite recovery and subsequent-session binding, using isolated fictional logs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from live_companion import LiveStore
from recover_voice import recover_voice, snapshot_voice, recovery_lock
from practice_store import initialize, resume

THREAD='00000000-0000-0000-0000-000000000021'


class Translator:
    calls=0
    fail=False
    def __init__(self,model):pass
    def translate(self,rows):
        type(self).calls+=1
        if self.fail:raise ValueError('Synthetic failure')
        return [{'id':r['id'],'chinese':'虚构译文'} for r in rows],.01
    def close(self):pass


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'source.jsonl'
        self.source.write_text(json.dumps({'type':'session_meta','payload':{'id':THREAD}})+'\n')
        self.store=LiveStore(self.root);Translator.calls=0;Translator.fail=False
    def tearDown(self):self.tmp.cleanup()
    def append(self,kind='transcript_segment',voice='second',id='s',text='How much is it?'):
        with self.source.open('a') as f:
            f.write(json.dumps({'type':'realtime_item','timestamp':'2026-01-01T01:00:00Z','ordinal':1,
                'payload':{'type':kind,'realtime_session_id':voice,'id':id,'role':'user','text':text}})+'\n')
    def closed(self):
        self.append('realtime_session_started');self.append();self.append('realtime_session_closed')
    def recover(self,**kwargs):return recover_voice(self.store,self.source,THREAD,'second',factory=Translator,**kwargs)

    def test_closed_recovery_preserves_active_binding_elsewhere(self):
        live=self.store.bind(THREAD,self.source,demo=True)
        self.closed();result=self.recover()
        self.assertEqual(self.store.active(),live)
        data=self.store.view({'run':result['run_id']})
        self.assertEqual(data['state']['recovery_mode'],'after_voice')
        self.assertEqual(data['state']['recovery_reason'],'missing_binding')
        self.assertEqual(data['counts'],{'translated':1})
        self.assertFalse(result['prior_binding_existed'])

    def test_retry_does_not_duplicate_or_retranslate_completed_rows(self):
        self.closed();first=self.recover();second=self.recover()
        self.assertEqual(first['run_id'],second['run_id']);self.assertEqual(Translator.calls,1)
        self.assertEqual(second['status'],'already_complete')
        self.append(id='late',text='Thank you.')
        third=self.recover();self.assertEqual(third['run_id'],first['run_id'])
        self.assertEqual(third['segments'],2);self.assertEqual(Translator.calls,2)

    def test_active_or_wrong_voice_is_not_recovered(self):
        self.append('realtime_session_started');self.append()
        with self.assertRaises(ValueError):self.recover()
        self.append('realtime_session_closed')
        with self.assertRaises(ValueError):snapshot_voice(self.source,'wrong','second')
        with self.assertRaises(ValueError):snapshot_voice(self.source,THREAD,'unknown')
        self.assertEqual(Translator.calls,0)

    def test_different_voices_and_duplicate_ids_are_filtered(self):
        self.append('realtime_session_started',voice='old');self.append(voice='old',id='old')
        self.append('realtime_session_closed',voice='old');self.closed();self.append()
        snap=snapshot_voice(self.source,THREAD,'second')
        self.assertEqual([s['id'] for s in snap['segments']],['s'])

    def test_two_failures_leave_error_and_original(self):
        self.closed();Translator.fail=True
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(Translator.calls,2)
        with self.store.db() as db:run=db.execute('SELECT id FROM runs').fetchone()[0]
        data=self.store.view({'run':run})
        self.assertEqual(data['state']['status'],'error');self.assertEqual(data['items'][0]['text'],'How much is it?')

    def test_lock_refuses_concurrent_recovery(self):
        with recovery_lock(self.store,THREAD,'second'):
            with self.assertRaises(ValueError):
                with recovery_lock(self.store,THREAD,'second'):pass

    def test_second_voice_requires_new_binding_and_stop_is_idempotent(self):
        self.append('realtime_session_started',voice='first');self.append(voice='first',id='first')
        first=self.store.bind(THREAD,self.source,demo=True);self.store.read_tail(first)
        self.append('realtime_session_closed',voice='first');self.store.read_tail(first)
        first['status']='ended';self.store.save(first)
        self.store.stop(first['id']);self.store.stop(first['id'])
        self.assertEqual(self.store.active()['desired'],'stopped')
        self.append('realtime_session_started');self.append()
        self.assertEqual(self.store.view({'run':first['id']})['total'],1)
        second=self.store.bind(THREAD,self.source,demo=True);self.store.read_tail(second)
        self.assertEqual(second['voice_id'],'second');self.assertNotEqual(first['id'],second['id'])
        self.assertEqual(self.store.view()['total'],1)

    def test_voice_brief_prioritizes_written_chinese_without_profile_mutation(self):
        initialize(self.root)
        self.store.bind(THREAD,self.source,demo=False)
        before=(self.root/'profile.json').read_bytes()
        result=resume(self.root,'2026-01-01')
        self.assertTrue(result['voice_brief'].startswith('Speak simple English in Voice.'))
        self.assertIn('do not read it aloud',result['voice_brief'])
        self.assertNotIn('Help language: zh-CN',result['voice_brief'])
        self.assertIn('EACH new Voice',result['voice_brief'])
        self.assertEqual((self.root/'profile.json').read_bytes(),before)


if __name__=='__main__':unittest.main()
