"""Functional closeout checks with fictional logs, including canonical reference reuse."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import practice_store as store
from review_pipeline import finish_review
from practice_runtime import begin_review, review_status, set_review_stage
from library_server import Archive, SKILL_ROOT
from test_fast_practice import THREAD, VOICE, OTHER_VOICE, record
from test_live_companion import event


class ReviewPipelineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); store.initialize(self.root); store.rebuild(self.root)
        self.source = self.root / 'fictional.jsonl'
        rows = [event('realtime_session_started', voice=VOICE)]
        self.sentences = ['how much every one', 'others bread you have', 'how much all',
                          'milk and juice do have', '折扣怎么说', 'Thanks, goodbye.']
        rows += [event(id='u'+str(i), text=text, voice=VOICE) for i, text in enumerate(self.sentences)]
        rows += [event('realtime_session_closed', voice=VOICE)]
        self.source.write_text(json.dumps({'type':'session_meta','payload':{'id':THREAD}})+'\n'+''.join(json.dumps(r)+'\n' for r in rows))
        self.draft = dict(title='Fictional bakery', summary='Synthetic coverage check',
                          expressions=[dict(source_turn_ids=['u'+str(i)], original=text,
                            english=['How much is each one?', 'What other bread do you have?', 'How much is that altogether?', 'Do you have milk or juice?', 'Is there a discount?'][i],
                            chinese='虚构含义'+str(i), note='Review-only suggestion; the coach did not model this during Voice.') for i, text in enumerate(self.sentences[:5])],
                          omitted_turns={'u5':'Closing greeting, no language help needed'}, priority_indices=[0,2,3],
                          coaching_notes=['Make the next action clear.'])

    def finish(self, draft=None, voice=VOICE):
        with store.writer(self.root):
            return finish_review(self.root, draft if draft is not None else self.draft, THREAD, voice, self.source)

    def test_complete_review_keeps_all_five_needs_and_three_priorities(self):
        before = (self.root/'Archive/legacy-v1.md').read_bytes()
        begin_review(self.root, THREAD, VOICE)
        started=time.monotonic(); result = self.finish()
        self.assertLess(time.monotonic()-started, 2)
        self.assertTrue(result['validation']['ok'])
        saved=store.extract(self.root/'Sessions'/f"{result['session']}.md",store.MARKER)
        self.assertEqual(len(saved['expressions']),5)
        self.assertEqual(len(saved['review_priority_ids']),3)
        self.assertEqual(saved['review_coverage']['available_learner_turns'],6)
        self.assertEqual(saved['review_coverage']['selected_learner_turns'],5)
        self.assertTrue(all(e['mastery']=='not_tested' for e in saved['expressions']))
        self.assertEqual((self.root/'Archive/legacy-v1.md').read_bytes(),before)
        self.assertEqual(self.finish({})['status'],'already_saved')
        self.assertEqual(len(store.build_state(self.root)['sessions']),1)
        page=Archive(self.root, SKILL_ROOT).query('/api/sessions/'+result['session'],{})
        self.assertEqual(page['coaching_notes'],['Make the next action clear.'])
        self.assertEqual(page['review_priority_ids'],saved['review_priority_ids'])

    def test_reading_guide_survives_closeout_api_and_rebuild_without_mastery_change(self):
        guide={'kind':'suggestion','groups':[{'text':'How much is each one?','stress':['much','one']}],
               'tone':'fall','tone_note':'A neutral information question can fall at the end.',
               'memory':[{'text':'How much is …?','meaning':'Ask the price'}]}
        self.draft['expressions'][0]['reading_guide']=guide
        result=self.finish()
        archive=Archive(self.root,SKILL_ROOT)
        lesson=archive.query('/api/sessions/'+result['session'],{})
        item=lesson['excerpts'][0]
        self.assertEqual(item['reading_guide'],guide)
        self.assertEqual(item['english'],'How much is each one?')
        self.assertEqual(item['mastery'],'not_tested')
        term=archive.query('/api/terms/'+item['id'],{})
        self.assertEqual(term['reading_guide'],guide)
        store.rebuild(self.root)
        self.assertEqual(store.build_state(self.root)['expressions'][0]['reading_guide'],guide)
        self.assertIn('怎么念（参考）',(self.root/'Sessions'/f"{result['session']}.md").read_text())

    def test_invalid_annotation_cannot_rewrite_sentence_or_claim_audio(self):
        from reading_guidance import validate_guide
        guide={'kind':'suggestion','groups':[{'text':'Can I pay by card?','stress':['card']}],
               'tone':'rise','tone_note':'A possible polite question.',
               'memory':[{'text':'Can I …?','meaning':'Ask permission'}]}
        validate_guide(guide,'Can I pay by card?')
        for broken in [dict(guide,kind='measured'),dict(guide,groups=[{'text':'Can pay I by card?','stress':[]}]),
                       dict(guide,groups=[{'text':'Can I pay by card?','stress':['cash']}]),
                       dict(guide,groups=[{'text':'Can I pay by card?','stress':['card!']}])]:
            with self.assertRaises(ValueError):validate_guide(broken,'Can I pay by card?')
        self.draft['expressions'][0]['reading_guide']=guide
        with self.assertRaisesRegex(ValueError,'preserve'):self.finish()
        self.assertEqual(store.build_state(self.root)['sessions'],[])

    def test_unaccounted_turn_and_invented_quote_cannot_silently_save(self):
        missing=deepcopy(self.draft); missing['expressions'].pop()
        with self.assertRaisesRegex(ValueError,'u4'): self.finish(missing)
        self.assertEqual(review_status(self.root,THREAD,VOICE)['status'],'error')
        invented=deepcopy(self.draft); invented['expressions'][0]['original']='How much is each one?'
        with self.assertRaisesRegex(ValueError,'exact excerpt'): self.finish(invented)
        self.assertEqual(store.build_state(self.root)['sessions'],[])
        self.assertEqual(self.finish()['status'],'saved')

    def test_existing_concept_reference_uses_canonical_meaning_without_copying(self):
        prior=record(OTHER_VOICE)
        prior['concept_observations']=[dict(id='OBS-old-discount', concept_id='CON-discount-price',
             term='discount', meaning='折扣；价格优惠', dimension='meaning',result='explained',
             support='model',modality='transcript',context='Old fictional store',note='Given explanation',
             quote_kind='utterance',quote='discount?')]
        store.commit(self.root,prior)
        context=store.review_context(self.root,'2026-01-01',THREAD,VOICE,with_transcript=True,source=self.source)
        self.assertEqual(context['concept_catalog'][0]['meaning'],'折扣；价格优惠')
        self.assertIn('finish_contract',context)
        self.draft['concept_observations']=[dict(concept_id='CON-discount-price',source_turn_ids=['u4'],
             dimension='meaning', result='needs_help', support='none',quote='折扣怎么说',note='Forgot word',expression_indices=[4])]
        result=self.finish(); saved=store.extract(self.root/'Sessions'/f"{result['session']}.md",store.MARKER)
        self.assertEqual(saved['concept_observations'][0]['meaning'],'折扣；价格优惠')
        self.assertEqual(saved['concept_observations'][0]['expression_ids'],[saved['expressions'][4]['id']])
        self.assertEqual(len(store.build_state(self.root)['concepts']),1)

    def test_false_independence_foreign_source_and_active_voice_are_rejected(self):
        bad=deepcopy(self.draft);bad['expressions'][0]['mastery']='independent'
        with self.assertRaisesRegex(ValueError,'Independent'):self.finish(bad)
        with self.assertRaises(ValueError):self.finish(voice=OTHER_VOICE)
        self.source.write_text('\n'.join(self.source.read_text().splitlines()[:-1])+'\n')
        with self.assertRaises(ValueError):self.finish()
        self.assertEqual(store.build_state(self.root)['sessions'],[])

    def test_transcript_closeout_cannot_claim_audio_fluency(self):
        self.draft['concept_observations']=[dict(term='discount',meaning='折扣',source_turn_ids=['u4'],
            dimension='reading',result='success',support='none',modality='audio',quote='折扣怎么说',note='Invalid fictional audio claim')]
        with self.assertRaisesRegex(ValueError,'transcript utterances'):self.finish()
        self.assertEqual(store.build_state(self.root)['sessions'],[])

    def test_id_allocation_skips_pending_other_voice_and_ended_recovery_is_safe(self):
        other=record(OTHER_VOICE)
        store.write_json(self.root/'Pending'/f"{other['id']}.json",other)
        result=self.finish();self.assertEqual(result['session'],'SES-20260101-002')
        self.assertNotEqual(store.build_state(self.root)['expressions'][0]['id'],other['expressions'][0]['id'])
        recovered=self.finish({},voice=OTHER_VOICE)
        self.assertEqual(recovered['session'],other['id']);self.assertTrue(recovered['validation']['ok'])

    def test_cli_contract_saves_in_one_command_and_reports_validation(self):
        payload=self.root/'draft.json';store.write_json(payload,self.draft)
        done=subprocess.run([sys.executable,store.__file__,'--root',str(self.root),'finish-review',
              '--thread-id',THREAD,'--voice-id',VOICE,'--source',str(self.source),'--input',str(payload)],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr)
        result=json.loads(done.stdout)
        self.assertTrue(result['validation']['ok']);self.assertTrue(result['archive_route'].startswith('#sessions/'))

    def test_review_catalog_retains_delayed_job_and_exact_saved_destination(self):
        set_review_stage(self.root,THREAD,OTHER_VOICE,'preparing',title='Older pending')
        set_review_stage(self.root,THREAD,VOICE,'practicing',title='Current bakery')
        begin_review(self.root,THREAD,VOICE)
        self.finish()
        data=Archive(self.root,SKILL_ROOT).query('/api/reviews',{})
        self.assertEqual(data['items'][0]['voice_id'],VOICE)
        self.assertEqual(data['items'][0]['status'],'saved')
        self.assertEqual(data['items'][0]['stage'],'saved')
        self.assertIsNone(data['items'][0]['elapsed_seconds'])
        self.assertEqual(data['items'][1]['voice_id'],OTHER_VOICE)
        self.assertEqual(data['items'][1]['status'],'preparing')
        self.assertEqual(data['items'][0]['session_id'],'SES-20260101-001')


if __name__=='__main__':unittest.main()
