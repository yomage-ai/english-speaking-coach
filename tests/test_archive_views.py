"""Synthetic fixtures only; no learner archives are required by the test suite."""
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import json
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from learning_progress import summarize_concept
from progress_views import period_rows,progress_list,progress_detail
from library_server import Archive,SKILL_ROOT
import practice_store as store


def event(n,day='2026-01-01',result='supported',dimension='use',context='Commute'):
    return {'id':f'OBS-fixture-{n:05d}','concept_id':'CON-commute','term':'commute','meaning':'通勤','date':day,'session':'SES-'+day.replace('-','')+'-001','dimension':dimension,'result':result,'support':'none' if result=='success' else 'model','modality':'audio' if dimension=='reading' else 'transcript','context':context,'quote_kind':'utterance','quote':'I commute by train.','note':'Synthetic fixture, not an actual learner record.','source_ids':['test:fixture'],'expression_ids':[]}

def concept(events=None,id='CON-commute'):
    return summarize_concept({'id':id,'term':'commute','meaning':'通勤','events':events or [event(1)]})

class ViewTests(unittest.TestCase):
    def test_period_excludes_later_success_and_uses_prior_baseline(self):
        c=concept([event(1),event(2,'2026-01-03','success'),event(3,'2026-02-01','success',context='Work meeting')])
        original=deepcopy(c)
        early=period_rows([c],{'to':'2026-01-01'})[0]
        self.assertEqual(early['level'],'supported');self.assertEqual(early['change_kind'],'first');self.assertEqual(early['event_count'],1)
        middle=period_rows([c],{'from':'2026-01-02','to':'2026-01-03'})[0]
        self.assertEqual(middle['level'],'independent');self.assertEqual(middle['change_kind'],'improved')
        self.assertEqual(c,original)
    def test_first_success_is_first_record_not_comparative_improvement(self):
        row=period_rows([concept([event(1,result='success')])],{})[0]
        self.assertEqual(row['change_kind'],'first')
    def test_month_history_and_no_fake_milestones(self):
        c=concept([event(1),event(2,'2026-02-01')])
        detail=progress_detail([c],c['id'],{'month':'2026-01'})
        self.assertEqual(detail['history']['total'],1);self.assertEqual(detail['last_date'],'2026-02-01')
        self.assertEqual(len(detail['milestones']),1)
    def test_large_catalog_and_history_are_bounded(self):
        events=[event(i,(date(2025,1,1)+timedelta(days=i)).isoformat()) for i in range(1500)]
        rows=[concept([event(1)],f'CON-fixture-{i:05d}') for i in range(1200)]
        long=concept(events);rows.append(long)
        listing=progress_list(rows,{'page':'2'})
        self.assertEqual(len(listing['items']),20);self.assertEqual(listing['total'],1201)
        self.assertNotIn('events',listing['items'][0])
        history=progress_detail(rows,long['id'],{'page':'2'})
        self.assertEqual(history['history']['total'],1500);self.assertEqual(len(history['history']['items']),10)
        self.assertLess(len(json.dumps(history)),20000)
    def test_filters_paging_and_missing_concept(self):
        c=concept();self.assertEqual(progress_list([c],{'q':'通勤'})['total'],1)
        self.assertEqual(progress_list([c],{'stage':'stable'})['total'],0)
        self.assertEqual(progress_list([c],{'page':'999'})['page'],1)
        for args in [{'from':'bad'},{'from':'2026-02-01','to':'2026-01-01'},{'stage':'unknown'}]:
            with self.assertRaises(ValueError):progress_list([c],args)
        with self.assertRaises(KeyError):progress_detail([c],'CON-missing',{})
        with self.assertRaises(ValueError):progress_detail([c],c['id'],{'month':'2026-13'})
    def test_revisit_retains_previous_milestone(self):
        c=concept([event(1,result='success'),event(2,'2026-02-01')])
        self.assertTrue(progress_list([c],{'stage':'revisit'})['items'][0]['needs_revisit'])
        self.assertIn('首次自主用出',[m['label'] for m in progress_detail([c],c['id'],{})['milestones']])
    def test_actual_archive_reads_metadata_and_bounded_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store.initialize(root);store.rebuild(root)
            e=event(1);e={k:v for k,v in e.items() if k not in {'date','session','source_ids'}}
            payload={'id':'SES-20260101-001','date':'2026-01-01','title':'Synthetic fixture','summary':'Test only','source_ids':['test:fixture'],'expressions':[],'concept_observations':[e]}
            store.commit(root,payload)
            raw=(root/'Sessions/SES-20260101-001.md').read_text()
            self.assertNotIn('primary_project:',raw);self.assertNotIn('status: candidate',raw)
            archive=Archive(root,SKILL_ROOT)
            self.assertEqual(archive.query('/api/stats',{})['progress_total'],1)
            self.assertNotIn('events',archive.query('/api/stats',{})['highlights'][0])
            self.assertEqual(archive.query('/api/progress',{})['total'],1)
            self.assertEqual(archive.query('/api/progress/CON-commute',{})['event_count'],1)
            self.assertEqual(archive.query('/api/stats',{'to':'2025-12-31'})['progress_total'],0)
    def test_optional_vault_metadata_is_explicit_and_escaped(self):
        data={'id':'SES-20260101-001','date':'2026-01-01','source_ids':['test:fixture'],'record_metadata':{'type':'task-record','status':'candidate','primary_project':'PRJ-TEST'}}
        text=store.record_frontmatter(data)
        self.assertIn('primary_project: "PRJ-TEST"',text)
        data['record_metadata']={'created':'overwrite'}
        with self.assertRaises(ValueError):store.record_frontmatter(data)

if __name__=='__main__':unittest.main()
