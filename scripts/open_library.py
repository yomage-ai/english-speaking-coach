"""Open the skill-owned local archive through the host's existing service manager."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys
import webbrowser
from workspace_config import resolve_workspace,SKILL_ROOT
from practice_context import review_route

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
    manager=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills/local-service-manager/scripts/services.py'
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
    elif manager.is_file():
        command=[sys.executable,str(manager),'start','--project',str(root),'--role','learning-library','--environment','local','--name','英语学习档案','--port',str(args.port),'--health','/','--health','/api/overview','--','python3',str(SKILL_ROOT/'scripts/library_server.py'),'--root',str(root),'--port','{port}']
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode:print(result.stdout+result.stderr,file=sys.stderr);return result.returncode
        service=json.loads(result.stdout)
    else:
        from library_service import start
        service=start(root,args.port)
        if service.get('status')=='needs_host_supervisor':
            print(json.dumps(service,ensure_ascii=False,indent=2));return 2
    if service.get('state')!='running' or not service.get('url'):raise ValueError('Archive service is not ready')
    url=service['url']+'/' + (waiting_route or '#'+('sessions/'+args.session if args.session else args.page))
    if not args.no_browser:webbrowser.open(url)
    print(json.dumps({'status':'ready','url':url,'service':service,'browser_open_requested':not args.no_browser},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,KeyError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
