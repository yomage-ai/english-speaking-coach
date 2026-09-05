"""Dated concept evidence, with separate meaning, reading and use observations."""
from datetime import date
from pathlib import Path
import re

MARKER='speaking-evidence-v1'
DIMENSIONS={'meaning':'理解词义','reading':'顺畅朗读','use':'自主运用'}
RESULTS={'needs_help':'当时还不明白','explained':'获得解释','supported':'有提示完成','success':'成功完成'}
SUPPORTS={'model':'完整示范','keywords':'关键词提示','none':'无语言提示'}

def validate_observations(observations):
    if not isinstance(observations,list):raise ValueError('concept_observations must be a list')
    ids=set()
    for o in observations:
        for key in ['id','concept_id','term','meaning','dimension','result','support','modality','context','note','quote_kind','quote']:
            if not isinstance(o.get(key),str) or not o[key].strip():raise ValueError('Concept observation missing '+key)
        if not re.fullmatch(r'OBS-[A-Za-z0-9_-]+',o['id']) or o['id'] in ids:raise ValueError('Invalid/duplicate observation ID')
        ids.add(o['id'])
        if not re.fullmatch(r'CON-[A-Za-z0-9_-]+',o['concept_id']):raise ValueError('Invalid concept ID')
        if o['dimension'] not in DIMENSIONS or o['result'] not in RESULTS or o['support'] not in SUPPORTS:raise ValueError('Invalid evidence classification')
        if o['modality'] not in {'text','transcript','audio'} or o['quote_kind'] not in {'utterance','session_note'}:raise ValueError('Invalid evidence source kind')
        if o['result']=='success' and o['quote_kind']!='utterance':raise ValueError('Successful ability observation requires actual learner evidence, not a summary alone')
        if o['dimension']=='reading' and o['result']=='success' and o['modality']!='audio':raise ValueError('Reading fluency needs actual audio evidence; transcript alone is insufficient')
        if o['result']=='success' and o['dimension'] in {'meaning','use'} and o['support']!='none':raise ValueError('Independent meaning/use success cannot have a supplied answer')
        if o['result']=='supported' and o['support']=='none':raise ValueError('Supported completion must name the support')
        if not isinstance(o.get('expression_ids',[]),list):raise ValueError('expression_ids must be a list')

def evidence_records(root):
    from practice_store import extract
    records=[]
    for file in sorted((Path(root)/'Evidence').glob('*.md')):
        record=extract(file,MARKER)
        if not record or record.get('id')!=file.stem:raise ValueError('Evidence file/ID mismatch')
        records.append(record)
    return records

def collect_progress(root, state, extra=None):
    sessions={s['id']:s for s in state['sessions']}
    expression_ids={e['id'] for e in state['expressions']}
    records=[{'session':s['id'],'date':s['date'],'source_ids':s.get('source_ids',[]),'concept_observations':s.get('concept_observations',[])} for s in sessions.values()]
    records+=evidence_records(root)
    if extra:records.append(extra)
    concepts={};seen={}
    for record in records:
        if record.get('session') not in sessions or record.get('date')!=sessions[record['session']]['date']:raise ValueError('Evidence must link to an actual session and its practice date')
        observations=record.get('concept_observations',[])
        validate_observations(observations)
        if observations and (not record.get('source_ids') or any(not isinstance(s,str) or not s for s in record['source_ids'])):raise ValueError('Evidence needs actual source identifiers')
        for raw in observations:
            if any(x not in expression_ids for x in raw.get('expression_ids',[])):raise ValueError('Unknown expression reference in concept evidence')
            event={**raw,'date':record['date'],'session':record['session'],'source_ids':record['source_ids'],'session_title':sessions[record['session']]['title']}
            if event['id'] in seen:
                if seen[event['id']]!=event:raise ValueError('Conflicting observation ID')
                continue
            seen[event['id']]=event
            concept=concepts.setdefault(raw['concept_id'],{'id':raw['concept_id'],'term':raw['term'],'meaning':raw['meaning'],'events':[]})
            if (concept['term'],concept['meaning'])!=(raw['term'],raw['meaning']):raise ValueError('Same concept ID has a different term or meaning; use a separate sense ID')
            concept['events'].append(event)
    for concept in concepts.values():
        summarize_concept(concept)
    return sorted(concepts.values(),key=lambda c:(c['last_date'],c['id']),reverse=True)

def summarize_concept(concept):
    """Derive a state using only the supplied chronological evidence."""
    concept['events'].sort(key=lambda o:(o['date'],o['session'],o['id']))
    dimensions={}
    for key,label in DIMENSIONS.items():
        events=[e for e in concept['events'] if e['dimension']==key]
        latest=events[-1] if events else None
        dimensions[key]={'label':label,'status':RESULTS[latest['result']] if latest else '还没有观察','evidence':latest,'successful':bool(latest and latest['result']=='success')}
    concept['dimensions']=dimensions
    independent=[e for e in concept['events'] if e['dimension']=='use' and e['result']=='success' and e['support']=='none']
    days=sorted({e['date'] for e in independent});contexts={e['context'].strip().casefold() for e in independent}
    stable=len(days)>=2 and len(contexts)>=2 and dimensions['use']['successful']
    concept['level']='stable' if stable else 'independent' if dimensions['use']['successful'] else 'supported' if any(e['result']=='supported' for e in concept['events']) else 'encountered'
    concept['level_label']={'stable':'表达已较稳定','independent':'曾自主用出','supported':'有提示能完成','encountered':'开始认识它'}[concept['level']]
    concept['needs_revisit']=bool(independent and not dimensions['use']['successful'])
    concept['first_date']=concept['events'][0]['date'];concept['last_date']=concept['events'][-1]['date']
    concept['independent_days']=len(days);concept['context_count']=len(contexts)
    concept['next_step']='换个话题再自然用一次，看看是否仍然顺手。' if stable else '隔天换个场景，在没有示范的情况下试着用出来。' if independent else '下次聊到相关话题时，先自己试一句，再按需要提示。'
    return concept

def save_evidence(root,data):
    from practice_store import build_state,extract,write_text,block
    if not re.fullmatch(r'EVD-\d{8}-\d{3}',str(data.get('id',''))):raise ValueError('Evidence ID must be EVD-YYYYMMDD-NNN')
    if not isinstance(data.get('reason'),str) or not data['reason'].strip():raise ValueError('Evidence needs a reason and source context')
    collect_progress(root,build_state(root),extra=data)
    target=Path(root)/'Evidence'/(data['id']+'.md')
    if target.exists():
        if extract(target,MARKER)!=data:raise ValueError('Conflicting evidence file; original preserved')
        return {'status':'already_saved','evidence':data['id']}
    import json
    from practice_store import record_frontmatter
    text=record_frontmatter(data)+'# 知识点学习记录 / Concept practice record\n\n课次：'+data['session']+' · '+data['date']+'\n\n'+data['reason']+'\n\n'
    for o in data['concept_observations']:
        text+='## '+o['term']+' · '+DIMENSIONS[o['dimension']]+'\n\n'+o['meaning']+'\n\n'+RESULTS[o['result']]+'；'+SUPPORTS[o['support']]+'。\n\n来源选段（'+o['quote_kind']+'）：'+o['quote']+'\n\n'+o['note']+'\n\n'
    text+='来源：'+', '.join(data['source_ids'])+'\n\n'+block(MARKER,data)
    write_text(target,text)
    return {'status':'saved','evidence':data['id']}
