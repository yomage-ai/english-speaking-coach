"""Skill-local macOS supervision when no existing host manager is available.

No login startup. Unknown listeners are preserved. Linux/Windows hosts can use
an existing native supervisor and pass its URL to open_library --service-url.
"""
from pathlib import Path
from urllib.request import urlopen
import argparse
import hashlib
import json
import os
import plistlib
import re
import socket
import subprocess
import sys
import time
from workspace_config import CONFIG_PATH, SKILL_ROOT, resolve_workspace


def workspace_owned(root):
    return Path(root).resolve()==Path(resolve_workspace()['data_root']).resolve()


def command(args,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check)


def identity(root,skill=SKILL_ROOT):
    if workspace_owned(root):root=CONFIG_PATH.parent
    return hashlib.sha256((str(Path(root).resolve())+'\n'+str(skill.resolve())).encode()).hexdigest()[:16]


def paths(root):
    key=identity(root)
    folder=CONFIG_PATH.parent/'services'/key
    label='local.english-speaking-coach.'+key
    return folder,label,f'gui/{os.getuid()}/{label}'


def job_pid(domain):
    result=command(['launchctl','print',domain],False)
    match=re.search(r'^\s*pid = (\d+)\s*$',result.stdout,re.M)
    return int(match.group(1)) if match else None


def check_service(url,root,expected_pid=None):
    with urlopen(url+'/api/identity',timeout=2) as response:info=json.load(response)
    if info.get('application')!='english-speaking-coach' or Path(info.get('data_root','')).resolve()!=Path(root).resolve() or Path(info.get('skill_root','')).resolve()!=SKILL_ROOT.resolve():
        raise ValueError('The listener belongs to another archive; it was preserved.')
    if expected_pid is not None and info.get('pid')!=expected_pid:raise ValueError('Listener and supervised process do not match.')
    from practice_runtime import code_revision
    if info.get('code_revision') != code_revision(SKILL_ROOT):
        raise ValueError('Service code is outdated. Agent: verify its existing supervisor and exact PID, then restart this instance after the active Voice ends. Do not create another service or change ports.')
    with urlopen(url+'/api/overview',timeout=2) as response:overview=json.load(response)
    if not isinstance(overview.get('counts'),dict):raise ValueError('Learning data is not readable.')
    with urlopen(url+'/',timeout=2) as response:
        if response.status!=200:raise ValueError('Archive page is unavailable.')
    return info


def status(root):
    if sys.platform!='darwin':raise ValueError('Use the host native supervisor on this platform.')
    folder,label,domain=paths(root);record=folder/'service.json';pid=job_pid(domain)
    if not record.exists() or pid is None:raise ValueError('Archive service is not running.')
    cfg=json.loads(record.read_text(encoding='utf-8'))
    plist=plistlib.loads((folder/'service.plist').read_bytes())
    loaded=command(['launchctl','print',domain]).stdout
    if str(SKILL_ROOT/'scripts/library_server.py') not in loaded or ('--workspace' if workspace_owned(root) else str(Path(root).resolve())) not in loaded:
        raise ValueError('Loaded job identity differs; it was preserved.')
    info=check_service(cfg['url'],root,pid)
    # Verify the actual loopback socket owner as well as the HTTP identity.
    sockets=command(['/usr/sbin/lsof','-a','-p',str(pid),'-iTCP','-sTCP:LISTEN','-nP']).stdout
    if f"127.0.0.1:{cfg['port']}" not in sockets:raise ValueError('Loopback socket ownership could not be verified.')
    return {**cfg,'data_root':str(Path(root).resolve()),'pid':pid,'state':'running','manager':'launchd','persist':False,'identity_verified':True}


def start(root,port=8897):
    root=Path(root).resolve()
    if sys.platform!='darwin':
        return {'status':'needs_host_supervisor','serve_command':[sys.executable,str(SKILL_ROOT/'scripts/library_server.py'),'--root',str(root),'--port',str(port)],'message':'Agent: use an existing systemd user service or Windows Task Scheduler job, verify ownership, then call open_library --service-url with the actual loopback URL.'}
    folder,label,domain=paths(root)
    loaded=command(['launchctl','print',domain],False)
    if loaded.returncode==0:return status(root)
    # Selection does not claim a reservation; verify the bound PID after launch.
    for candidate in range(port,min(port+100,65536)):
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',candidate))
            except OSError:continue
            port=candidate;break
    else:raise ValueError('No free loopback port found; existing listeners were preserved.')
    folder.mkdir(parents=True,exist_ok=True)
    log=folder/'library.log';plist_path=folder/'service.plist'
    location=['--workspace'] if workspace_owned(root) else ['--root',str(root)]
    plist={'Label':label,'ProgramArguments':[str(Path(sys.executable).resolve()),str(SKILL_ROOT/'scripts/library_server.py'),*location,'--port',str(port)],'WorkingDirectory':str(SKILL_ROOT),'RunAtLoad':True,'StandardOutPath':str(log),'StandardErrorPath':str(log),'EnvironmentVariables':{'PYTHONUNBUFFERED':'1','CODEX_HOME':str(CONFIG_PATH.parent.parent)}}
    plist_path.write_bytes(plistlib.dumps(plist))
    cfg={'id':label,'data_root':str(root),'skill_root':str(SKILL_ROOT),'url':f'http://127.0.0.1:{port}','port':port,'log':str(log),'plist':str(plist_path)}
    (folder/'service.json').write_text(json.dumps(cfg),encoding='utf-8')
    command(['launchctl','bootstrap',f'gui/{os.getuid()}',str(plist_path)])
    for _ in range(40):
        try:return status(root)
        except (OSError,ValueError,subprocess.SubprocessError):time.sleep(.15)
    raise ValueError('Archive did not become healthy. Inspect '+str(log)+'; no unknown process was stopped.')


def stop(root):
    verified=status(root)
    _,_,domain=paths(root)
    command(['launchctl','bootout',domain])
    return {**verified,'state':'stopped'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['start','status','stop']);p.add_argument('--root',required=True,type=Path);p.add_argument('--port',type=int,default=8897)
    args=p.parse_args()
    if not 1024<=args.port<=65535:p.error('Choose a port between 1024 and 65535.')
    print(json.dumps(start(args.root,args.port) if args.action=='start' else status(args.root) if args.action=='status' else stop(args.root),ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.SubprocessError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
