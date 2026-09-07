"""Opt-in scene support survives CLI persistence without changing historical evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import practice_store as store
from practice_context import speaking_context

SCENE = {'setting': 'A fictional cafe', 'learner_role': 'Customer', 'partner_role': 'Server',
         'goal': 'Ask for a recommendation and explain a preference',
         'introduction': '你在咖啡馆点餐，我是店员。请询问推荐并说明你的口味。',
         'opening_line': 'What are you in the mood for today?'}


class InCharacterTests(unittest.TestCase):
    def test_authorized_cli_update_and_phase_boundaries_preserve_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store.initialize(root)
            store.commit(root, {'id': 'SES-20260101-001', 'date': '2026-01-01',
                               'title': 'Fictional prior practice', 'summary': 'Synthetic evidence',
                               'source_ids': ['synthetic:lesson'], 'expressions': []})
            profile_path = root / 'profile.json'
            prior = store.read_json(profile_path)
            old_lesson = root / 'Sessions/SES-20260101-001.md'
            old_bytes = old_lesson.read_bytes()
            patch = root / 'patch.json'
            store.write_json(patch, {'correction': 'in_character',
                                    'source_ids': prior['source_ids'] + ['synthetic:decision'],
                                    'updated': '2026-01-02'})
            call = subprocess.run([sys.executable, str(Path(store.__file__)), '--root', str(root),
                                   'set-preferences', '--input', str(patch),
                                   '--expected-profile-sha256', hashlib.sha256(profile_path.read_bytes()).hexdigest()],
                                  capture_output=True, text=True)
            self.assertEqual(call.returncode, 0, call.stderr)
            current = store.read_json(profile_path)
            for key in prior.keys() - {'correction', 'source_ids', 'updated'}:
                self.assertEqual(current[key], prior[key])
            selected = root / 'scene.json'
            store.write_json(selected, SCENE)
            reopened = subprocess.run([sys.executable, str(Path(store.__file__)), '--root', str(root),
                                       'resume', '--scene', str(selected)], capture_output=True, text=True)
            self.assertEqual(reopened.returncode, 0, reopened.stderr)
            result = json.loads(reopened.stdout)
            self.assertEqual(result['scene'], SCENE)
            self.assertTrue(result['policy']['embedded_recasts'])
            self.assertTrue(result['policy']['learner_expansion'])
            self.assertFalse(result['policy']['proactive_teaching'])
            self.assertFalse(result['policy']['guided_drills'])
            review = store.resume(root, '2026-01-02', phase='review')
            self.assertFalse(review['policy']['embedded_recasts'])
            self.assertFalse(review['policy']['learner_expansion'])
            self.assertTrue(review['policy']['guided_drills'])
            for event in ('user_end', 'host_closed'):
                ended = store.resume(root, '2026-01-02', event=event, scene=SCENE)
                self.assertFalse(ended['transition']['continue_voice'])
                self.assertIsNone(ended['phase'])
            complete = store.resume(root, '2026-01-02', event='scene_complete_and_continuing', scene=SCENE)
            self.assertTrue(complete['transition']['continue_voice'])
            self.assertEqual(complete['transition']['action'], 'offer_next_scene_or_finish')
            paused = store.resume(root, '2026-01-02', event='pause', scene=SCENE)
            self.assertFalse(paused['transition']['continue_voice'])
            self.assertEqual(old_lesson.read_bytes(), old_bytes)
            self.assertTrue(store.validate(root)['ok'])

    def test_existing_correction_modes_do_not_opt_in(self):
        for correction in ('after_scene', 'light', 'detailed'):
            with self.subTest(correction=correction):
                profile = store.default_profile()
                profile['correction'] = correction
                result = speaking_context(profile, False, None, scene=SCENE)
                self.assertFalse(result['policy']['embedded_recasts'])
                self.assertFalse(result['policy']['learner_expansion'])
                self.assertEqual(result['policy']['proactive_teaching'], correction != 'after_scene')
        self.assertEqual(store.default_profile()['correction'], 'after_scene')


if __name__ == '__main__':
    unittest.main()
