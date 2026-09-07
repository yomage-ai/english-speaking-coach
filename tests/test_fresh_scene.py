"""Fresh scene startup and preference compatibility on fictional data only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import practice_store as store
from practice_context import speaking_context

SCENE={'setting':'Fictional station','learner_role':'Passenger','partner_role':'Ticket clerk',
       'goal':'Buy a train ticket','introduction':'你在车站买票。你是乘客，我是售票员。',
       'opening_line':'Where would you like to go?'}


class FreshSceneTests(unittest.TestCase):
    def test_startup_history_omits_plot_while_archive_review_keeps_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store.initialize(root);store.rebuild(root)
            record={'id':'SES-20260101-001','date':'2026-01-01','title':'OLD-PLOT-ONLY',
                    'summary':'OLD-DIALOGUE-ONLY','next_focus':['OLD-NEXT-ONLY'],'unfinished':['OLD-TAIL-ONLY'],
                    'scenarios':['shopping'],'progress':['Asked a clear question'],
                    'source_ids':['synthetic:history'],'expressions':[]}
            store.commit(root,record)
            path=root/'Sessions/SES-20260101-001.md';before=path.read_bytes()
            startup=store.resume(root,'2026-01-02')
            self.assertEqual(startup['recent_scenarios'][0]['scenarios'],['shopping'])
            self.assertEqual(startup['latest_session']['progress'],record['progress'])
            for field in ('title','summary','next_focus','unfinished'):
                self.assertNotIn(field,startup['latest_session'])
            self.assertEqual(store.resume(root,'2026-01-02','review')['latest_session']['summary'],record['summary'])
            self.assertEqual(path.read_bytes(),before)

    def test_old_plot_is_excluded_and_both_opening_parts_are_delivered(self):
        profile=store.default_profile()
        old={'title':'OLD-PLOT-ONLY','next_focus':['OLD-LINE-ONLY'],'unfinished':['OLD-ENDING-ONLY']}
        result=speaking_context(profile,True,old,scene=SCENE)
        brief=result['voice_brief']
        self.assertEqual(result['scene'],SCENE)
        self.assertFalse(result['policy']['history_continuation'])
        self.assertNotIn(SCENE['introduction'],brief)
        self.assertLess(brief.index(SCENE['setting']),brief.index(SCENE['opening_line']))
        self.assertEqual(result['scene']['introduction'],SCENE['introduction'])
        for value in ['OLD-PLOT-ONLY','OLD-LINE-ONLY','OLD-ENDING-ONLY']:
            self.assertNotIn(value,brief)
        self.assertIsNone(speaking_context(profile,True,old)['voice_brief'])

    def test_english_introduction_and_non_roleplay_routes(self):
        profile=store.default_profile();profile['help_language']='en'
        scene={**SCENE,'introduction':'You are at a station. Buy a ticket; I am the clerk.'}
        result=speaking_context(profile,False,None,scene=scene)
        self.assertEqual(result['scene']['introduction'],scene['introduction'])
        self.assertIn(scene['introduction'],result['voice_brief'])
        profile['mode']='conversation'
        self.assertFalse(speaking_context(profile,False,None)['startup']['scene_required'])
        review=speaking_context(profile,False,None,phase='review')
        self.assertFalse(review['startup']['scene_required']);self.assertTrue(review['policy']['guided_drills'])

    def test_cli_adds_authorized_field_to_legacy_profile_without_rewriting_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store.initialize(root);store.rebuild(root)
            old=store.read_json(root/'profile.json');old.pop('review_delivery')
            old.update(correction='light',review_limit=0)
            store.write_json(root/'profile.json',old)
            archive=(root/'Archive/legacy-v1.md').read_bytes()
            patch=root/'patch.json'
            store.write_json(patch,{'review_delivery':'written','source_ids':['synthetic:decision'],'updated':'2026-01-01'})
            result=subprocess.run([sys.executable,str(Path(store.__file__)), '--root',str(root),
                'set-preferences','--input',str(patch),'--expected-profile-sha256',hashlib.sha256((root/'profile.json').read_bytes()).hexdigest()],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            current=store.read_json(root/'profile.json')
            self.assertEqual(current['review_delivery'],'written');self.assertEqual(current['correction'],'light')
            self.assertEqual(current['review_limit'],0);self.assertEqual((root/'Archive/legacy-v1.md').read_bytes(),archive)
            selected=root/'scene.json';store.write_json(selected,SCENE)
            cli=subprocess.run([sys.executable,str(Path(store.__file__)),'--root',str(root),'resume','--scene',str(selected)],capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stderr)
            self.assertEqual(json.loads(cli.stdout)['scene'],SCENE)


if __name__=='__main__':unittest.main()
