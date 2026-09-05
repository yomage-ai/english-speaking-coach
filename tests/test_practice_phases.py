"""Phase, chronology, and concurrent-preference regressions on fictional records."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import practice_store as store
from practice_context import transition
from library_server import Archive


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);store.initialize(self.root);store.rebuild(self.root)

    def test_scene_help_review_and_ending_do_not_change_stable_preferences(self):
        profile=store.read_json(self.root/'profile.json');profile['mode']='roleplay'
        store.write_json(self.root/'profile.json',profile);before=(self.root/'profile.json').read_bytes()
        scene=store.resume(self.root,'2026-01-01')
        self.assertEqual(scene['policy']['role'],'character')
        self.assertFalse(scene['policy']['proactive_teaching']);self.assertFalse(scene['policy']['guided_drills'])
        # “Nothing” while browsing is an ordinary reply; explicit help also stays in scene.
        self.assertEqual(transition('scene','continue')['action'],'respond')
        self.assertEqual(transition('scene','help_requested')['phase'],'scene')
        review=store.resume(self.root,'2026-01-01','scene','scene_complete_and_continuing')
        self.assertEqual(review['phase'],'review');self.assertTrue(review['policy']['guided_drills'])
        ended=store.resume(self.root,'2026-01-01','review','user_end')
        self.assertIsNone(ended['phase']);self.assertFalse(ended['transition']['continue_voice'])
        self.assertFalse(ended['transition']['spoken_review']);self.assertTrue(ended['transition']['save_selected'])
        self.assertEqual(transition('scene','host_closed')['action'],'end')
        self.assertFalse(transition('scene','pause')['continue_voice'])
        self.assertEqual((self.root/'profile.json').read_bytes(),before)

    def test_legacy_preferences_and_explicit_review_remain_supported(self):
        profile=store.read_json(self.root/'profile.json')
        profile.update(correction='detailed',drills='on_request',mode='conversation')
        store.write_json(self.root/'profile.json',profile)
        result=store.resume(self.root,'2026-01-01')
        self.assertTrue(result['policy']['proactive_teaching'])
        self.assertFalse(store.resume(self.root,'2026-01-01','review')['policy']['guided_drills'])
        profile['mode']='focused';store.write_json(self.root/'profile.json',profile)
        self.assertEqual(store.resume(self.root,'2026-01-01')['phase'],'review')

    def test_stale_preference_update_is_rejected_without_overwrite(self):
        profile=self.root/'profile.json';oldhash=hashlib.sha256(profile.read_bytes()).hexdigest()
        current=store.read_json(profile);current['review_limit']=0;store.write_json(profile,current)
        patch=self.root/'patch.json';store.write_json(patch,{'correction':'after_scene','source_ids':['synthetic:user-decision'],'updated':'2026-01-01'})
        command=[sys.executable,str(Path(store.__file__)), '--root',str(self.root),'set-preferences','--input',str(patch),'--expected-profile-sha256',oldhash]
        self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
        self.assertEqual(store.read_json(profile),current)
        command[-1]=hashlib.sha256(profile.read_bytes()).hexdigest()
        self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
        self.assertEqual(store.read_json(profile)['review_limit'],0)

    def test_late_import_does_not_replace_later_practice_or_latest_attempt(self):
        def payload(n,clock,mastery,result,prompt):
            return {'id':f'SES-20260101-{n:03}','date':'2026-01-01','practiced_at':f'2026-01-01T{clock}:00+08:00','recovered_on':'2026-01-02',
                    'title':'Fictional shopping '+clock,'summary':'Synthetic observation','source_ids':['synthetic:'+clock],'next_focus':[clock],
                    'expressions':[{'id':'EXP-20260101-001','original':'Is there a discount?','english':'Is there a discount?','chinese':'有折扣吗？','mastery':mastery,'next_review':'2026-01-02','review_result':result,'review_prompt':prompt,'note':'Synthetic evidence'}]}
        later=payload(1,'21:35','independent','success','none');older=payload(2,'21:26','source_text','partial','source_text')
        store.commit(self.root,later);raw=(self.root/'Sessions'/f"{later['id']}.md").read_bytes()
        store.commit(self.root,older);self.assertEqual(store.commit(self.root,older)['status'],'already_saved')
        state=store.build_state(self.root)
        self.assertEqual(store.resume(self.root,'2026-01-02')['latest_session']['id'],later['id'])
        self.assertEqual(state['expressions'][0]['mastery'],'independent')
        self.assertEqual([a['session'] for a in state['expressions'][0]['attempts']],[older['id'],later['id']])
        self.assertEqual(Archive(self.root,Path(store.__file__).resolve().parents[1]).query('/api/overview',{})['latest']['id'],later['id'])
        self.assertEqual((self.root/'Sessions'/f"{later['id']}.md").read_bytes(),raw)
        # An undated old import cannot jump ahead of an actually timed same-day lesson.
        unknown=deepcopy(older);unknown.update(id='SES-20260101-003',expressions=[]);unknown.pop('practiced_at')
        store.commit(self.root,unknown)
        self.assertEqual(store.resume(self.root,'2026-01-02')['latest_session']['id'],later['id'])
        self.assertIn(unknown['id'],store.resume(self.root,'2026-01-02')['agent_context']['same_day_without_time'])


if __name__=='__main__':unittest.main()
