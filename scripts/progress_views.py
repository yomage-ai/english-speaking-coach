"""Bounded reading views; period summaries never include later observations."""
from copy import deepcopy
from datetime import date
import re
from learning_progress import summarize_concept

LEVELS = {'encountered':'开始学习', 'supported':'有提示能完成', 'independent':'曾自主用出', 'stable':'表达已较稳定'}

def date_range(args):
    start, end = args.get('from',''), args.get('to','')
    for value in (start, end):
        if value and date.fromisoformat(value).isoformat()!=value:
            raise ValueError('日期格式应为 YYYY-MM-DD。')
    if start and end and start > end:
        raise ValueError('开始日期不能晚于结束日期。')
    return start,end

def paginate(rows,args,limit=20):
    pages=max(1,(len(rows)+limit-1)//limit)
    page=min(max(1,int(args.get('page',1))),pages)
    return {'items':rows[(page-1)*limit:page*limit], 'page':page, 'pages':pages,'total':len(rows),'limit':limit}

def snapshot(concept,events):
    return summarize_concept({'id':concept['id'],'term':concept['term'],'meaning':concept['meaning'],'events':events})

def brief(concept):
    fields=['id','term','meaning','level','level_label','needs_revisit','first_date','last_date','independent_days','context_count','next_step']
    row={k:concept[k] for k in fields}
    row['event_count']=len(concept['events'])
    row['dimensions']={k:{'label':v['label'],'status':v['status'],'successful':v['successful'],'date':v['evidence']['date'] if v['evidence'] else None} for k,v in concept['dimensions'].items()}
    return row

def period_rows(concepts,args):
    start,end=date_range(args)
    rows=[]
    for original in concepts:
        all_events=original['events']
        selected=[e for e in all_events if (not start or e['date']>=start) and (not end or e['date']<=end)]
        if not selected:continue
        current=snapshot(original,[e for e in all_events if not end or e['date']<=end])
        prior=[e for e in all_events if start and e['date']<start]
        row=brief(current);last=selected[-1];row['period_event_count']=len(selected)
        row['last_session']=last['session'];row['latest_in_period']=last['date']
        if not prior:
            row.update(change_kind='first',change_text='首次留下练习记录；'+current['level_label'])
        else:
            previous=snapshot(original,prior)
            improved=[d['label'] for k,d in current['dimensions'].items() if d['successful'] and not previous['dimensions'][k]['successful']]
            if current['needs_revisit']:
                row.update(change_kind='revisit',change_text='最近又需要帮助，可以再练一次')
            elif improved:
                row.update(change_kind='improved',change_text='有了新的成功表现：'+'、'.join(improved))
            elif current['level']=='stable' and previous['level']!='stable':
                row.update(change_kind='improved',change_text='跨日、换场景后，仍能自主运用')
            else:
                row.update(change_kind='practiced',change_text='再次练习；'+current['level_label'])
        rows.append(row)
    return sorted(rows,key=lambda r:(r['latest_in_period'],r['id']),reverse=True)

def progress_list(concepts,args):
    rows=period_rows(concepts,args)
    query=args.get('q','').strip().casefold()
    stage=args.get('stage','')
    if stage and stage not in {*LEVELS,'revisit'}:raise ValueError('未知的练习状态。')
    rows=[r for r in rows if (not query or query in (r['term']+' '+r['meaning']).casefold()) and (not stage or (r['needs_revisit'] if stage=='revisit' else r['level']==stage))]
    return {**paginate(rows,args),'as_of':args.get('to') or None,'stages':LEVELS}

def progress_detail(concepts,id,args):
    original=next((c for c in concepts if c['id']==id),None)
    if original is None:raise KeyError('没有找到这个词句的练习历程。')
    month=args.get('month','')
    if month and (not re.fullmatch(r'\d{4}-\d{2}',month) or date.fromisoformat(month+'-01').strftime('%Y-%m')!=month):raise ValueError('月份格式应为 YYYY-MM。')
    events=original['events']
    months=sorted({e['date'][:7] for e in events},reverse=True)
    selected=[e for e in reversed(events) if not month or e['date'].startswith(month)]
    milestones=[{'label':'首次记录','date':events[0]['date'],'session':events[0]['session']}]
    for dim,label in [('meaning','首次独立理解'),('reading','首次顺畅读出'),('use','首次自主用出')]:
        first=next((e for e in events if e['dimension']==dim and e['result']=='success'),None)
        if first:milestones.append({'label':label,'date':first['date'],'session':first['session']})
    return {**brief(original),'history':paginate(selected,args,10),'months':months,'milestones':milestones,'month':month}
