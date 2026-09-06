"""Compact learning context and exact-Voice review updates on fictional records."""
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import practice_store as store
from practice_context import compact_context, review_route
from library_server import Archive, Handler, SKILL_ROOT

THREAD = '00000000-0000-0000-0000-000000000081'
VOICE = '00000000-0000-0000-0000-000000000082'
OTHER_VOICE = '00000000-0000-0000-0000-000000000083'
SCENE = dict(setting='Fictional cafe', learner_role='Customer', partner_role='Server',
             goal='Ask for a recommendation', introduction='在咖啡馆询问推荐。',
             opening_line='What are you in the mood for?')


def record(voice=VOICE, sid='SES-20260101-001'):
    return dict(id=sid, date='2026-01-01', title='Synthetic practice', summary='Test only',
                source_ids=['codex-thread:' + THREAD, 'codex-voice:' + voice],
                expressions=[dict(id='EXP-20260101-001', original='recommend?',
                    english='What would you recommend?', chinese='你推荐什么？',
                    issue_tags=['request'], mastery='source_text', next_review='2026-01-02',
                    note='Synthetic model-supported attempt; not independent use.')])


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class FastPracticeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); store.initialize(self.root); store.rebuild(self.root)

    def cli(self, *args):
        return subprocess.run([sys.executable, store.__file__, '--root', str(self.root), *args],
                              capture_output=True, text=True)

    def test_compact_context_keeps_instruction_and_learning_evidence(self):
        store.commit(self.root, record())
        profile = store.read_json(self.root / 'profile.json')
        profile['correction'] = 'in_character'; store.write_json(self.root / 'profile.json', profile)
        full = store.resume(self.root, '2026-01-02', scene=SCENE)
        short = compact_context(full)
        for key in ('voice_brief', 'scene', 'policy', 'latest_session', 'concept_review_candidates'):
            self.assertEqual(short[key], full[key])
        self.assertEqual(short['profile']['correction'], 'in_character')
        self.assertEqual(short['due_candidates'][0]['note'], full['due_candidates'][0]['note'])
        ready = compact_context(full, prepared=True)
        self.assertEqual(ready['voice_brief'], full['voice_brief'])
        self.assertLess(len(json.dumps(ready)), len(json.dumps(full)))
        self.assertNotIn('recent_scenarios', ready)

    def test_readonly_closeout_respects_pending_ids_and_duplicate_end(self):
        store.write_json(self.root / 'Pending/SES-20260101-001.json', {'id': 'reserved-fixture'})
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        context = store.review_context(self.root, '2026-01-01', THREAD, VOICE)
        self.assertEqual(context['suggested_session_id'], 'SES-20260101-002')
        self.assertFalse(context['id_reserved']); self.assertEqual(context['existing_records'], [])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        saved = record(sid='SES-20260101-002'); store.commit(self.root, saved)
        again = store.review_context(self.root, '2026-01-01', THREAD, VOICE)
        self.assertEqual(again['existing_records'], [saved])
        self.assertEqual(again['suggested_session_id'], saved['id'])
        self.assertEqual(store.review_context(self.root, '2026-01-01', THREAD, OTHER_VOICE)['existing_records'], [])

    def test_interrupted_closeout_reuses_the_matching_pending_selection(self):
        pending = {**record(), 'end_status': 'ended'}
        store.write_json(self.root / 'Pending/SES-20260101-001.json', pending)
        context = store.review_context(self.root, '2026-01-01', THREAD, VOICE)
        self.assertEqual(context['suggested_session_id'], pending['id'])
        self.assertEqual(context['pending_records'], [pending])
        self.assertEqual(context['existing_records'], [])

    def test_cli_saves_and_validates_without_rewriting_history(self):
        archive = self.root / 'Archive/legacy-v1.md'
        before = hashlib.sha256(archive.read_bytes()).hexdigest()
        payload = self.root / 'payload.json'; store.write_json(payload, record())
        result = self.cli('add-session', '--input', str(payload), '--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout); self.assertTrue(data['validation']['ok'])
        self.assertEqual(data['archive_route'], '#sessions/SES-20260101-001')
        repeated = self.cli('add-session', '--input', str(payload), '--check')
        self.assertEqual(json.loads(repeated.stdout)['status'], 'already_saved')
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), before)
        lookup = self.cli('review-context', '--thread-id', THREAD, '--voice-id', VOICE, '--query', '推荐')
        self.assertEqual(lookup.returncode, 0, lookup.stderr)
        self.assertEqual(len(json.loads(lookup.stdout)['expression_catalog']), 1)

    def test_http_waiting_page_uses_both_sources_and_observes_atomic_save(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        server.archive = Archive(self.root, SKILL_ROOT)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        def read(voice=VOICE):
            with urlopen(base + '/api/' + review_route(THREAD, voice)[1:]) as r:
                return json.load(r)
        store.commit(self.root, record(OTHER_VOICE))
        self.assertEqual(read()['status'], 'waiting')
        self.assertEqual(read(OTHER_VOICE)['status'], 'saved')
        store.commit(self.root, record(sid='SES-20260101-002'))
        self.assertEqual(read()['session_id'], 'SES-20260101-002')
        store.commit(self.root, record(sid='SES-20260101-003'))
        with self.assertRaises(HTTPError) as exc: read()
        self.assertEqual(exc.exception.code, 400)
        exc.exception.close()
        with self.assertRaises(ValueError): review_route(THREAD, 'not-a-voice-id')


if __name__ == '__main__':
    unittest.main()
