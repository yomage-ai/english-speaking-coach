"""Learning support survives startup; preparation is not learning evidence."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import practice_store as store
from practice_context import compact_context, validate_scene
from library_server import Archive

SCENE = {'setting': 'An art studio', 'learner_role': 'Visitor', 'partner_role': 'Artist',
         'goal': 'Choose a class and ask what to bring', 'introduction': '你在工作室询问课程。',
         'opening_line': 'What would you like to make?'}


class LearningLoadTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); store.initialize(self.root); store.rebuild(self.root)

    def record(self, number=1, **extra):
        return {'id': f'SES-20260101-{number:03}', 'date': '2026-01-01',
                'title': 'A fictional practice', 'summary': 'Archived plot only',
                'source_ids': ['synthetic:learning-load'], 'expressions': [], **extra}

    def test_learning_needs_survive_compact_preparation_without_rewriting_history(self):
        record = self.record(next_focus=['Ask for the time with simple words.'],
                             coaching_notes=['Learner asked for less information per reply.'],
                             unfinished=['ARCHIVED PLOT'])
        store.commit(self.root, record)
        path = self.root / 'Sessions' / (record['id'] + '.md'); before = path.read_bytes()
        for prepared in (False, True):
            context = compact_context(store.resume(self.root, '2026-01-02', scene=SCENE), prepared=prepared)
            evidence = context['learning_context']['recent'][0]
            self.assertEqual(evidence['session_id'], record['id'])
            self.assertEqual(evidence['coaching_notes'], record['coaching_notes'])
            self.assertEqual(evidence['next_focus'], record['next_focus'])
            self.assertNotIn('unfinished', evidence)
            self.assertNotIn('ARCHIVED PLOT', context['voice_brief'])
        self.assertEqual(before, path.read_bytes())
        for move in ('pause', 'user_end'):
            context = store.resume(self.root, '2026-01-02', event=move)
            self.assertFalse(context['transition']['continue_voice'])

    def test_legacy_learning_focus_is_available_and_recent_window_is_bounded(self):
        for n in range(1, 5): store.commit(self.root, self.record(n, next_focus=[f'Need {n}']))
        context = store.resume(self.root, '2026-01-02')
        self.assertEqual([e['next_focus'] for e in context['learning_context']['recent']],
                         [['Need 4'], ['Need 3'], ['Need 2']])
        self.assertNotIn('summary', context['latest_session'])
        self.assertEqual(store.resume(self.root, '2026-01-02', phase='review')['latest_session']['summary'], 'Archived plot only')

    def test_preparation_terms_roundtrip_but_do_not_create_cards(self):
        self.assertEqual(validate_scene(SCENE), SCENE)
        scene = {**SCENE, 'key_terms': [{'term': 'apron', 'meaning': '围裙', 'example': 'Wear an apron.'}]}
        scene_file = self.root / 'scene.json'; scene_file.write_text(json.dumps(scene), encoding='utf-8')
        before = store.build_state(self.root)
        result = subprocess.run([sys.executable, store.__file__, '--root', str(self.root), 'resume',
                                 '--scene', str(scene_file), '--compact'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['scene'], scene)
        self.assertEqual(store.build_state(self.root)['concepts'], before['concepts'])
        self.assertEqual(store.build_state(self.root)['expressions'], before['expressions'])
        for value in ({**scene, 'key_terms': scene['key_terms'] * 4},
                      {**scene, 'key_terms': scene['key_terms'] * 2},
                      {**scene, 'key_terms': [{'term': 'apron'}]}):
            with self.assertRaises(ValueError): validate_scene(value)

    def test_actual_unresolved_word_becomes_card_without_scoring_mastery(self):
        observation = {'id': 'OBS-20260101-001-001', 'concept_id': 'CON-apron-clothing',
                       'term': 'apron', 'meaning': '围裙', 'dimension': 'meaning',
                       'result': 'needs_help', 'support': 'none', 'modality': 'transcript',
                       'context': 'Choosing an art class', 'quote_kind': 'utterance',
                       'quote': 'What is an apron?', 'note': 'Learner asked; no verified understanding.',
                       'expression_ids': []}
        store.commit(self.root, self.record(concept_observations=[observation]))
        concept = store.build_state(self.root)['concepts'][0]
        self.assertEqual(concept['level'], 'encountered')
        self.assertFalse(concept['dimensions']['meaning']['successful'])
        terms = Archive(self.root, Path(__file__).resolve().parents[1]).load()['terms']
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]['english'], 'apron')
        self.assertEqual(terms[0]['mastery'], 'not_tested')

    def test_coaching_notes_validate_before_writing(self):
        for notes in ('Too long', ['note'] * 4, ['x' * 501], ['']):
            with self.assertRaises(ValueError): store.validate_payload(self.record(coaching_notes=notes))
        self.assertFalse(list((self.root / 'Sessions').glob('*.md')))

    def test_saved_short_turn_support_survives_new_start_without_changing_other_choices(self):
        path = self.root / 'profile.json'
        old = store.read_json(path); old.pop('input_support')
        old.update(correction='in_character', review_limit=0)
        store.write_json(path, old)
        self.assertEqual(store.resume(self.root, '2026-01-02')['policy']['input_support'], 'adaptive')
        patch = self.root / 'patch.json'
        store.write_json(patch, {'input_support':'short_turns', 'source_ids':['synthetic:preference'], 'updated':'2026-01-02'})
        result = subprocess.run([sys.executable, store.__file__, '--root', str(self.root), 'set-preferences',
                                 '--input', str(patch), '--expected-profile-sha256', hashlib.sha256(path.read_bytes()).hexdigest()],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = compact_context(store.resume(self.root, '2026-01-02', scene=SCENE), prepared=True)
        self.assertEqual(context['policy']['input_support'], 'short_turns')
        self.assertEqual(context['profile']['correction'], 'in_character')
        self.assertEqual(context['profile']['review_limit'], 0)
        invalid = {**old, 'input_support':'beginner'}
        with self.assertRaises(ValueError): store.validate_profile(invalid)


if __name__ == '__main__': unittest.main()
