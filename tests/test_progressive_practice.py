"""Observable new startup, caption advice and review-preview behavior on fictional data."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from live_fragments import annotate_fragments
from live_teaching import validate_hint
from live_companion import LiveStore
from review_preview import expression_prefix,suggestion_prefix,checked_preview
from review_worker import ReviewClient
from prepare_practice import opening_context
import test_durable_review_transfer as worker_fixtures
from test_fast_practice import SCENE,THREAD,VOICE
from test_live_companion import event
import practice_store as store


def turn(id,text,role='user',second=0):
    return {'id':id,'role':role,'text':text,'timestamp':f'2026-01-01T00:00:{second:02d}Z'}

class ProgressiveTests(unittest.TestCase):
    def test_preview_can_show_complete_phrase_before_optional_metadata(self):
        item={'source_turn_ids':['u'],'original':'go shop','english':'Could we go shopping?','chinese':'我们可以去购物吗？'}
        core=json.dumps(item,ensure_ascii=False)
        stream='{"expressions": ['+core[:-1]+', "reading_guide": {"groups": ['
        self.assertEqual(suggestion_prefix(stream),[item])
        self.assertEqual(suggestion_prefix(stream[:stream.index('吗')]),[])
        self.assertEqual(suggestion_prefix(json.dumps({'comment':stream})),[])
        self.assertEqual(suggestion_prefix('{"expressions": ['+core+','+core+']}'),[item,item])

    def test_duplicate_phrase_keeps_evidence_and_remaps_links(self):
        from review_pipeline import coalesce_expressions
        first={'english':'Could we go shopping?','chinese':'我们可以去购物吗？','original':'go shop','source_turn_ids':['u1'],'mastery':'not_tested'}
        second={**first,'original':'Could we go shopping?','source_turn_ids':['u2'],'mastery':'source_text','review_result':'success','review_prompt':'source_text'}
        draft={'expressions':[first,second],'priority_indices':[1,0], 'reading_omissions':{'1':'short'},
               'concept_observations':[{'expression_indices':[1,0]}]}
        merged=coalesce_expressions(draft)
        self.assertEqual(len(merged['expressions']),1)
        item=merged['expressions'][0]
        self.assertEqual(item['original'],second['original'])
        self.assertEqual(item['mastery'],'source_text')
        self.assertEqual(item['source_turn_ids'],['u1','u2'])
        self.assertEqual([q['quote'] for q in item['source_quotes']],[first['original'],second['original']])
        self.assertEqual(merged['priority_indices'],[0])
        self.assertEqual(merged['concept_observations'][0]['expression_indices'],[0])
        self.assertEqual(merged['reading_omissions'],{'0':'short'})
        self.assertEqual(len(draft['expressions']),2)
        self.assertEqual(coalesce_expressions({'expressions':[{'english':'bad'},{'english':'bad'}]})['expressions'],[{'english':'bad'},{'english':'bad'}])

    def test_captions_publish_before_teaching_finishes(self):
        from codex_translation import CodexTranslator
        client=CodexTranslator();client.thread_id='test-thread'
        client.teaching_context={'conversation':[turn('u','Hello')]}
        text=json.dumps({'translations':[{'id':'u/english/0','chinese':'你好','kind':'translation'}], 'teaching':{'kind':'none'}})
        cut=text.index('],')+1;seen=[]
        events=iter([
            {'method':'item/agentMessage/delta','params':{'turnId':'turn','delta':text[:cut]}},
            {'method':'item/completed','params':{'turnId':'turn','item':{'type':'agentMessage','text':text}}},
            {'method':'turn/completed','params':{'turn':{'id':'turn','status':'completed'}}}])
        client.request=lambda *args:{'turn':{'id':'turn'}}
        client.on_translation=lambda result,latency:seen.append(result)
        def receive(deadline):
            event=next(events)
            if event['method']=='item/completed':self.assertEqual(seen,[[{'id':'u','chinese':'你好'}]])
            return event
        client.receive=receive
        result,_=client.translate([turn('u','Hello')]);self.assertEqual(result,seen[0])

    def test_fragments_keep_source_text_order_and_only_link_nearby_same_speaker(self):
        rows=[turn('u1','A block',second=1),turn('a1','Perfect','assistant',2),turn('u2','- buster',second=3)]
        result=annotate_fragments(rows)
        self.assertEqual(result[-1]['fragment']['joined_word'],'blockbuster')
        self.assertEqual(result[-1]['fragment']['previous_id'],'u1')
        self.assertEqual([r['text'] for r in result],[r['text'] for r in rows])
        self.assertNotIn('fragment',rows[-1])
        self.assertNotIn('fragment',annotate_fragments([rows[0],turn('late','- buster',second=20)])[-1])
        self.assertNotIn('fragment',annotate_fragments([turn('a','A block','assistant'),rows[-1]])[-1])
        self.assertNotIn('fragment',annotate_fragments([turn('u','- tea')])[0])
        self.assertEqual(annotate_fragments([turn('a','. So let us','assistant')])[0]['fragment']['kind'],'continuation')

    def test_hint_checks_exact_latest_evidence_language_length_and_reading_words(self):
        rows=[turn('u','maybe go shop')]
        hint={'kind':'help','source_id':'u','quote':'maybe go shop','english':'Maybe we could go shopping.',
              'chinese':'也许我们可以去购物。','next_cue':'','groups':['Maybe we could go shopping.']}
        self.assertEqual(validate_hint(hint,rows)['source_text'],rows[0]['text'])
        for changed in [{'source_id':'old'},{'quote':'invented'},{'english':'我们去 shopping'},
                        {'groups':['Maybe we can go shopping.']},{'english':'word '*26}]:
            self.assertIsNone(validate_hint({**hint,**changed},rows))
        self.assertIsNone(validate_hint(hint,rows+[turn('new','Yes')]))
        cue={**hint,'kind':'continue','english':'','chinese':'','groups':[],'next_cue':'When would you like to go?'}
        self.assertIsNotNone(validate_hint(cue,rows))

    def test_stream_parser_never_exposes_incomplete_objects_or_quoted_fake_arrays(self):
        item={'source_turn_ids':['u'],'original':'go shop','english':'Could we go shopping?','chinese':'我们可以去购物吗？'}
        text=json.dumps({'expressions':[item,item],'other':[]},ensure_ascii=False)
        cut=text.index('},')+1
        self.assertEqual(expression_prefix(text[:cut-1]),[])
        self.assertEqual(expression_prefix(text[:cut]),[item])
        self.assertEqual(len(expression_prefix(text)),2)
        self.assertEqual(expression_prefix(json.dumps({'comment':text})),[])
        self.assertEqual(expression_prefix('{"expressions": [{"english": "unclosed'),[])
        snap={'segments':[turn('u','maybe go shop')]}
        self.assertEqual(len(checked_preview([item],snap)),1)
        self.assertEqual(checked_preview([{**item,'original':'not said'}],snap),[])
        self.assertEqual(checked_preview([{**item,'source_turn_ids':['other']}],snap),[])
        self.assertEqual(checked_preview([{**item,'english':'中文'}],snap),[])

    def test_review_client_emits_preview_before_completion_and_restores_ids(self):
        client=ReviewClient();client.thread_id='test-thread'
        expression={'source_turn_ids':['t1'],'original':'go shop','english':'Could we go shopping?','chinese':'我们可以去购物吗？'}
        draft={'expressions':[expression],'concept_observations':[],'omitted_turns':[],'reading_omissions':[]}
        text=json.dumps(draft);cut=text.index('}],')+2
        seen=[];events=iter([
            {'method':'item/agentMessage/delta','params':{'turnId':'foreign','delta':text}},
            {'method':'item/agentMessage/delta','params':{'turnId':'turn','itemId':'answer','delta':text[:cut]}},
            {'method':'item/agentMessage/delta','params':{'turnId':'turn','itemId':'answer','delta':text[cut:]}},
            {'method':'item/completed','params':{'turnId':'turn','item':{'type':'agentMessage','phase':'final_answer','text':text}}},
            {'method':'turn/completed','params':{'turn':{'id':'turn','status':'completed'}}}])
        client.on_preview=lambda xs:seen.append(deepcopy(xs))
        client.request=lambda *args:{'turn':{'id':'turn'}}
        def receive(deadline):
            e=next(events)
            if e['method']=='item/completed':self.assertTrue(seen,'A preview must precede the completed response')
            return e
        client.receive=receive
        result,_=client.generate({'transcript':[turn('real-id','go shop')]})
        self.assertEqual(seen[0][0]['source_turn_ids'],['real-id'])
        self.assertEqual(result['expressions'][0]['source_turn_ids'],['real-id'])

    def test_live_context_and_api_hide_stale_changed_or_closed_hints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store.initialize(root);store.rebuild(root)
            source=root/'fictional.jsonl'
            source.write_text(json.dumps({'type':'session_meta','payload':{'id':THREAD}})+'\n'+json.dumps(event('realtime_session_started',voice=VOICE))+'\n'+json.dumps(event(id='u',text='go shop',voice=VOICE))+'\n')
            live=LiveStore(root);run=live.bind(THREAD,source);live.read_tail(run)
            context=live.teaching_context(run['id'])
            self.assertEqual(context['conversation'][-1]['text'],'go shop')
            hint={'source_id':'u','source_text':'go shop','kind':'continue','next_cue':'When?'}
            live.save_hint(run['id'],hint);self.assertEqual(live.view()['teaching'],hint)
            batch=live.batch(run['id'])
            live.translated(run['id'],[{'id':'u','chinese':'去商店'}],1,{'u':'go shop'})
            self.assertEqual(live.fail_batch(run['id'],batch),0)
            with live.db() as db:self.assertEqual(db.execute("SELECT status FROM segments WHERE id='u'").fetchone()[0],'translated')
            with live.db() as db:before=dict(db.execute("SELECT * FROM segments WHERE id='u'").fetchone())
            live.translated(run['id'],[{'id':'u','chinese':'去商店'}],5,{'u':'go shop'})
            with live.db() as db:after=dict(db.execute("SELECT * FROM segments WHERE id='u'").fetchone())
            self.assertEqual((before['translated_at'],before['latency']),(after['translated_at'],after['latency']))
            with live.db() as db:db.execute("UPDATE segments SET text='go shopping' WHERE id='u'")
            live.translated(run['id'],[{'id':'u','chinese':'过期译文'}],9,{'u':'go shop'})
            with live.db() as db:self.assertEqual(db.execute("SELECT chinese FROM segments WHERE id='u'").fetchone()[0],'去商店')
            self.assertIsNone(live.view()['teaching'])
            live.save_hint(run['id'],{**hint,'source_text':'go shopping'})
            self.assertIsNotNone(live.view()['teaching'])
            live.stop(run['id'],immediate=True);self.assertIsNone(live.view()['teaching'])

    def test_opening_preserves_preferences_evidence_project_and_failure_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store.initialize(root);store.rebuild(root)
            context=store.resume(root,'2026-01-01',scene=SCENE)
            data={'status':'backend_ready','context':context,'url':'http://localhost:1/#live','review_url':'http://localhost:1/#review',
                  'workspace':{'data_root':str(root)},'project_context':'Real project context','timing':{'local_preparation_ms':10}}
            result=opening_context(data,True)
            self.assertEqual(result['profile']['correction'],context['profile']['correction'])
            self.assertEqual(result['learning_context'],context['learning_context'])
            self.assertEqual(result['project_context'],'Real project context')
            self.assertEqual(result['scene']['opening_line'],SCENE['opening_line'])
            self.assertEqual(result['delivery']['spoken_opening'],'not_verified')
            self.assertTrue(result['conversation_may_start'])
            self.assertLess(len(json.dumps(result)),len(json.dumps(data))*.7)
            focused=deepcopy(data);focused['context']['phase']='review';focused['context']['scene']=None
            focused['context']['concept_review_candidates']=[{'id':'concept','term':'walk','meaning':'步行'}]
            review=opening_context(focused)
            self.assertEqual(review['concept_review'],focused['context']['concept_review_candidates'])
            self.assertIn('Start one due expression or word review',review['next_action'])
            failed={**data,'status':'preparation_error','error':'actual service failure'}
            self.assertIs(opening_context(failed),failed)

class PreviewWorkerTests(unittest.TestCase):
    def test_interrupted_complete_request_preserves_preview_without_saving_lesson(self):
        fixture=worker_fixtures.WorkerTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        root,source,draft=fixture.root,fixture.source,fixture.draft
        from review_worker import ReviewWorker,enqueue
        from practice_runtime import review_status
        class SlowClient:
            def generate(client,payload,feedback=None):
                client.on_preview(draft['expressions'][:2])
                status=review_status(root,THREAD,VOICE)
                self.assertEqual(len(status['preview']),2)
                self.assertEqual(store.build_state(root)['sessions'],[])
                raise ValueError('Fictional connection ended after preview')
            def close(client):pass
        worker=ReviewWorker(root,SlowClient);worker.process(enqueue(root,THREAD,VOICE,source))
        status=review_status(root,THREAD,VOICE)
        self.assertEqual(status['status'],'error');self.assertEqual(len(status['preview']),2)
        self.assertEqual(store.build_state(root)['sessions'],[])
