"""Open the skill-owned local archive through the host's existing service manager."""
from pathlib import Path
import argparse
import json
import re
import sys
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen
from workspace_config import resolve_workspace,SKILL_ROOT
from practice_context import review_route

def existing_service(root, port):
    """Reuse a matching healthy listener without replacing its supervisor."""
    base = f'http://127.0.0.1:{port}'
    try:
        with urlopen(base + '/api/identity', timeout=2) as response:
            info = json.load(response)
    except (OSError, URLError, ValueError):
        return None
    if (not isinstance(info, dict) or info.get('application') != 'english-speaking-coach'
            or not isinstance(info.get('data_root'), str) or not isinstance(info.get('skill_root'), str)):
        return None
    if (Path(info.get('data_root', '')).resolve() != Path(root).resolve()
            or Path(info.get('skill_root', '')).resolve() != SKILL_ROOT.resolve()):
        return None
    # A known matching service with failed health must be repaired by its owner,
    # not replaced with a second supervisor on another port.
    from library_service import check_service
    verified = check_service(base, root, info.get('pid'))
    return {'state': 'running', 'url': base, 'pid': verified['pid'], 'manager': 'existing'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path)
    p.add_argument('--session')
    p.add_argument('--review-thread', help='Open a read-only waiting page for an observed Voice end')
    p.add_argument('--review-voice', help='Exact Voice UUID; required with --review-thread')
    p.add_argument('--page',choices=['overview','terms','stats','progress','storage','live'],default='overview')
    p.add_argument('--service-url',help='Verified loopback URL from the existing host supervisor')
    p.add_argument('--port',type=int,default=8897)
    p.add_argument('--no-browser',action='store_true')
    args=p.parse_args()
    waiting_route = None
    if args.review_thread or args.review_voice:
        if args.session: p.error('Choose a saved session or a Voice waiting page, not both')
        waiting_route = review_route(args.review_thread, args.review_voice)
    if args.session and not re.fullmatch(r'SES-\d{8}-\d{3}',args.session):p.error('Invalid session ID')
    workspace=resolve_workspace(root=args.root)
    root=Path(workspace['data_root'])
    from practice_store import build_state
    state=build_state(root)
    if args.session and args.session not in {s['id'] for s in state['sessions']}:p.error('Session has not been saved')
    if not 1024<=args.port<=65535:p.error('Port must be between 1024 and 65535')
    if args.service_url:
        from urllib.parse import urlsplit
        from library_service import check_service
        parsed=urlsplit(args.service_url)
        if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost'} or parsed.path not in {'','/'} or parsed.query or parsed.fragment or parsed.username:
            p.error('--service-url must be a plain loopback HTTP URL')
        base=args.service_url.rstrip('/')
        identity=check_service(base,root)
        service={'state':'running','url':base,'pid':identity['pid'],'manager':'host-provided'}
    else:
        service = existing_service(root, args.port)
        if service is None:
            from library_service import start
            service = start(root, args.port)
            if service.get('status') == 'needs_host_supervisor':
                print(json.dumps(service, ensure_ascii=False, indent=2)); return 2
    if service.get('state')!='running' or not service.get('url'):raise ValueError('Archive service is not ready')
    url=service['url']+'/' + (waiting_route or '#'+('sessions/'+args.session if args.session else args.page))
    if not args.no_browser:webbrowser.open(url)
    print(json.dumps({'status':'ready','url':url,'service':service,'browser_open_requested':not args.no_browser},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,KeyError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
