"""Expose complete, source-checked suggestions while the one review request continues."""
import json
import re


def array_prefix(text, key, limit=40):
    """Only parse a first root array; return complete objects and whether it closed."""
    match=re.match(r'^\s*\{\s*"'+re.escape(key)+r'"\s*:\s*\[',text)
    if not match:return [],False
    decoder=json.JSONDecoder();cursor=match.end();items=[]
    while len(items)<=limit:
        cursor += len(text[cursor:])-len(text[cursor:].lstrip())
        if cursor>=len(text):break
        if text[cursor]==']':return items,True
        if len(items)==limit:break
        try:item,end=decoder.raw_decode(text,cursor)
        except ValueError:break
        if not isinstance(item,dict):break
        items.append(item);cursor=end
        cursor += len(text[cursor:])-len(text[cursor:].lstrip())
        if cursor<len(text) and text[cursor]==']':return items,True
        if cursor>=len(text) or text[cursor]!=',':break
        cursor+=1
    return items,False


def expression_prefix(text):
    return array_prefix(text,'expressions',3)[0]


def suggestion_prefix(text):
    """A complete phrase/quote need not wait for its optional reading annotations."""
    match=re.match(r'^\s*\{\s*"expressions"\s*:\s*\[',text)
    if not match:return []
    decoder=json.JSONDecoder();cursor=match.end();items=[]
    required={'source_turn_ids','original','english','chinese'}
    def skip(pos):return pos+len(text[pos:])-len(text[pos:].lstrip())
    while len(items)<3:
        cursor=skip(cursor)
        if cursor>=len(text) or text[cursor]!='{':break
        cursor+=1;fields={};finished=False
        while cursor<len(text):
            cursor=skip(cursor)
            if cursor<len(text) and text[cursor]=='}':cursor+=1;finished=True;break
            try:key,end=decoder.raw_decode(text,cursor)
            except ValueError:break
            cursor=skip(end)
            if not isinstance(key,str) or cursor>=len(text) or text[cursor]!=':':break
            cursor=skip(cursor+1)
            try:value,end=decoder.raw_decode(text,cursor)
            except ValueError:break
            fields[key]=value;cursor=skip(end)
            if cursor<len(text) and text[cursor]==',':cursor+=1
            elif cursor>=len(text) or text[cursor]!='}':break
        if required<=fields.keys():items.append({k:fields[k] for k in required})
        if not finished:break
        cursor=skip(cursor)
        if cursor>=len(text) or text[cursor]!=',':break
        cursor+=1
    return items


def checked_preview(expressions, snapshot):
    turns={s['id']:s for s in snapshot['segments'] if s['role']=='user'}
    result=[]
    for item in expressions[:3]:
        ids=item.get('source_turn_ids');original=item.get('original')
        if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in turns for i in ids):continue
        if not isinstance(original,str) or not original.strip() or not any(original in turns[i]['text'] for i in ids):continue
        if any(not isinstance(item.get(k),str) or not item[k].strip() or len(item[k])>1600 for k in ('english','chinese')):continue
        if re.search(r'[\u3400-\u9fff]',item['english']) or not re.search(r'[A-Za-z]',item['english']):continue
        result.append({k:item[k] for k in ('source_turn_ids','original','english','chinese')})
    return result
