"""Display annotations for explicit transcript continuations; raw evidence stays intact."""
from datetime import datetime
import re


def annotate_fragments(rows):
    result = [dict(row) for row in rows]
    for index, row in enumerate(result):
        text = row['text'].strip()
        tail = re.fullmatch(r'[-–—]\s*([A-Za-z]+)[.!?,]?', text)
        if tail:
            previous = next((r for r in reversed(result[max(0,index-4):index])
                             if r['role'] == row['role']), None)
            if previous:
                try:
                    gap = (datetime.fromisoformat(row['timestamp'].replace('Z','+00:00')) -
                           datetime.fromisoformat(previous['timestamp'].replace('Z','+00:00'))).total_seconds()
                except (ValueError, TypeError, KeyError):
                    gap = -1
                stem = re.search(r'([A-Za-z]+)\s*$', previous['text'])
                if stem and 0 <= gap <= 3:
                    row['fragment'] = {'kind':'word_tail', 'previous_id':previous['id'],
                                       'joined_word':stem[1] + tail[1]}
                    continue
        if re.match(r'^[.,;:]\s+\S', text):
            row['fragment'] = {'kind':'continuation'}
    return result
