"""Intent boundaries and exact-Voice written closeout on synthetic sources."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import practice_store as store
from practice_context import compact_context
from open_library import existing_service

THREAD = '00000000-0000-0000-0000-000000000091'
VOICE = '00000000-0000-0000-0000-000000000092'
OTHER = '00000000-0000-0000-0000-000000000093'


def event(kind, voice=VOICE, **data):
    return {'type': 'realtime_item', 'timestamp': '2026-01-01T10:00:00Z',
            'payload': {'type': kind, 'realtime_session_id': voice, **data}}


class CloseoutTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        store.initialize(self.root); store.rebuild(self.root)
        self.source = self.root / 'source.jsonl'

    def log(self, rows):
        rows = [{'type': 'session_meta', 'payload': {'id': THREAD}}, *rows]
        self.source.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

    def lookup(self):
        return store.review_context(self.root, '2026-01-01', THREAD, VOICE,
                                    with_transcript=True, source=self.source)

    def test_end_keeps_written_work_in_compact_context_but_pause_does_not(self):
        before = (self.root / 'profile.json').read_bytes()
        for phase in ('scene', 'review'):
            for name in ('user_end', 'host_closed'):
                closed = compact_context(store.resume(self.root, '2026-01-01', phase, name))
                self.assertIsNone(closed['phase'])
                self.assertFalse(closed['transition']['continue_voice'])
                self.assertTrue(closed['closeout']['required'])
                self.assertEqual(closed['closeout']['record_status'], 'not_checked')
                self.assertFalse(closed['closeout']['spoken_review'])
            for name in ('pause', 'word_help_requested', 'coaching_feedback',
                         'meaning_confirmed', 'content_clear'):
                result = store.resume(self.root, '2026-01-01', phase, name)
                self.assertNotIn('closeout', result)
                self.assertEqual(result['phase'], phase)
                self.assertFalse(result['transition']['save_selected'])
        self.assertEqual((self.root / 'profile.json').read_bytes(), before)

    def test_exact_closed_snapshot_deduplicates_without_writing_or_binding(self):
        segment = event('transcript_segment', id='line-1', role='user', text='I like walking.')
        self.log([event('realtime_session_started'), segment, segment,
                  event('transcript_segment', OTHER, id='foreign', role='user', text='Other Voice'),
                  {'type': 'response_item', 'payload': {'transcript_delta': 'duplicate handoff text'}},
                  event('realtime_session_closed')])
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.lookup()
        self.assertEqual(result['transcript']['status'], 'observed_closed')
        self.assertEqual([s['text'] for s in result['transcript']['segments']], ['I like walking.'])
        self.assertEqual(result['existing_records'], [])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        record = {'id': 'SES-20260101-001', 'date': '2026-01-01', 'title': 'Synthetic lesson',
                  'summary': 'Test only', 'expressions': [], 'source_ids': result['source_ids']}
        store.commit(self.root, record)
        repeated = self.lookup()
        self.assertEqual(repeated['existing_records'], [record])
        self.assertEqual(repeated['suggested_session_id'], record['id'])
        self.assertEqual(len(store.build_state(self.root)['sessions']), 1)

    def test_unclosed_foreign_or_conflicting_evidence_does_not_become_verified(self):
        self.log([event('realtime_session_started')])
        self.assertEqual(self.lookup()['transcript']['status'], 'unavailable')
        self.log([event('realtime_session_started', OTHER), event('realtime_session_closed', OTHER)])
        self.assertEqual(self.lookup()['transcript']['status'], 'unavailable')
        a = event('transcript_segment', id='same', role='user', text='First')
        b = event('transcript_segment', id='same', role='user', text='Different')
        self.log([event('realtime_session_started'), a, b, event('realtime_session_closed')])
        self.assertEqual(self.lookup()['transcript']['status'], 'unavailable')
        self.assertNotIn('segments', self.lookup()['transcript'])

    def test_cli_snapshot_and_invalid_flag_scope(self):
        self.log([event('realtime_session_started'), event('realtime_session_closed')])
        command = [sys.executable, store.__file__, '--root', str(self.root)]
        valid = subprocess.run(command + ['review-context', '--thread-id', THREAD, '--voice-id', VOICE,
                                          '--with-transcript', '--source', str(self.source)],
                               capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)['transcript']['status'], 'observed_closed')
        invalid = subprocess.run(command + ['resume', '--with-transcript'], capture_output=True)
        self.assertNotEqual(invalid.returncode, 0)


class ExistingServiceTests(unittest.TestCase):
    def response(self, root, **extra):
        return io.StringIO(json.dumps({'application': 'english-speaking-coach', 'data_root': str(root),
                                      'skill_root': str(Path(store.__file__).resolve().parents[1]),
                                      'pid': 123, **extra}))

    def test_reuses_healthy_listener_without_claiming_supervisor_ownership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch('open_library.urlopen', return_value=self.response(root)), \
                 patch('library_service.check_service', return_value={'pid': 123}) as check:
                service = existing_service(root, 8897)
            check.assert_called_once_with('http://127.0.0.1:8897', root, 123)
            self.assertEqual(service['manager'], 'existing')
            self.assertEqual(service['state'], 'running')

    def test_foreign_listener_is_not_reused_and_matching_unhealthy_one_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch('open_library.urlopen', return_value=self.response(root / 'other')), \
                 patch('library_service.check_service') as check:
                self.assertIsNone(existing_service(root, 8897)); check.assert_not_called()
            with patch('open_library.urlopen', return_value=self.response(root)), \
                 patch('library_service.check_service', side_effect=ValueError('Unhealthy')):
                with self.assertRaises(ValueError): existing_service(root, 8897)


if __name__ == '__main__':
    unittest.main()
