"""One bounded Agent entry: recover context, bind exact Voice, verify service and return the page to inspect."""
import argparse
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.parse import urlsplit

from live_companion import LiveStore, TERMINAL, find_source
from practice_store import initialize, rebuild, resume, writer, write_json
from workspace_config import resolve_workspace, SKILL_ROOT, backup_embedded_data


def open_service(root, service_url=None):
    command = [sys.executable, str(SKILL_ROOT/'scripts/open_library.py'), '--root', str(root), '--page', 'live', '--no-browser']
    if service_url:
        command += ['--service-url', service_url]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Archive service is not available')
    opened = json.loads(result.stdout)
    from library_service import check_service
    parsed = urlsplit(opened['url'])
    check_service(parsed.scheme + '://' + parsed.netloc, root)
    return opened


def read_live(base):
    with urlopen(base + '/api/live', timeout=3) as response:
        return json.load(response)


def readiness(data, binding):
    state = data.get('state') or {}
    if state.get('id') != binding['id'] or state.get('thread_id') != binding['thread_id']:
        return 'binding_changed'
    if binding.get('voice_id') and state.get('voice_id') != binding['voice_id']:
        return 'binding_changed'
    if state.get('status') in TERMINAL or state.get('status') == 'draining':
        return 'ended' if state.get('status') in {'ended','draining'} else 'backend_error'
    if state.get('error'):
        return 'backend_error'
    if not state.get('ready') or state.get('stale'):
        return 'waiting_backend'
    return 'backend_ready'


def prepare(root=None, thread_id=None, source=None, phase=None, enable_companion=False,
            service_url=None, timeout=12, opener=open_service, reader=read_live):
    if not 0 <= timeout <= 45:
        raise ValueError('Readiness wait must be between 0 and 45 seconds')
    workspace = resolve_workspace(root=root)
    root = Path(workspace['data_root'])
    if not (root/'profile.json').is_file():
        if workspace['mode'] != 'skill-data':
            raise ValueError('Configured archive is unavailable; no empty replacement was created')
        with writer(root):
            initialize(root); rebuild(root)
            write_json(Path(workspace['config_path']), {'schema_version':1, 'data_root':str(root), 'project_page':None})
            backup_embedded_data(root)
    context = resume(root, str(date.today()), phase)
    page = workspace.get('project_page')
    project_context = Path(page).read_text(encoding='utf-8') if page else None
    result = {'context':context, 'workspace':workspace, 'project_context':project_context,
              'checks':{'context_restored':True, 'project_page':workspace.get('project_page'),
                        'binding_verified':False, 'backend_ready':False, 'page_display':'not_verified',
                        'voice_handoff':'not_verified'}}
    if not (enable_companion or context['companion']['enabled']):
        return {**result, 'status':'conversation_only', 'url':None}
    if not thread_id:
        return {**result, 'status':'needs_voice_task', 'url':None,
                'next_action':'Agent must resolve the actual Voice task ID; do not bind the implementation task.'}
    store = LiveStore(root)
    active = store.active()
    if active and active['desired'] != 'stopped' and active['status'] not in TERMINAL and active['thread_id'] != thread_id:
        return {**result, 'status':'other_voice_active', 'url':None,
                'next_action':'Leave the other active Voice alone. Do not stop or replace it.'}
    source = Path(source) if source else find_source(thread_id)
    # Binding verifies the source identity before any service operation. Repeating this entry
    # reuses an active/waiting binding in the same task and never replays a closed Voice.
    binding = store.bind(thread_id, source)
    result['checks']['binding_verified'] = True
    result['binding'] = {k:binding.get(k) for k in ['id','thread_id','voice_id']}
    result['context'] = resume(root, str(date.today()), phase)
    try:
        service = opener(root, service_url)
        parsed = urlsplit(service['url'])
        if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1','localhost'} or parsed.username:
            raise ValueError('Service must return a loopback URL')
        base = parsed.scheme + '://' + parsed.netloc
        result['service'] = service.get('service', {})
        result['url'] = base + '/#live?run=' + binding['id']
        deadline = time.monotonic() + timeout
        while True:
            data = reader(base)
            status = readiness(data, binding)
            if status != 'waiting_backend' or time.monotonic() >= deadline:
                break
            time.sleep(min(.25, max(0, deadline - time.monotonic())))
        result['status'] = status
        result['checks']['binding_verified'] = status != 'binding_changed'
        result['checks'].update(backend_ready=status == 'backend_ready',
                                transcript_observed=bool(data.get('total')),
                                voice_id=(data.get('state') or {}).get('voice_id'))
        result['next_action'] = ('Agent: open and inspect this exact URL in the host browser. Report backend readiness, page visibility, and transcript ingestion separately. Pass only voice_brief when the host supports handoff; this result does not prove delivery.'
                                 if status == 'backend_ready' else 'Agent: inspect the actual backend status; do not claim subtitles are ready or a page was shown.')
        if (data.get('state') or {}).get('error'):
            result['error'] = data['state']['error']
        return result
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        # Prevent a failed setup from leaving a newly-created, unattended binding behind.
        if not active or active['id'] != binding['id']:
            store.stop(binding['id'], immediate=True)
        return {**result, 'status':'preparation_error', 'error':str(exc),
                'next_action':'Agent: inspect the service error. No page display or Voice handoff has been verified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path); parser.add_argument('--thread-id')
    parser.add_argument('--source', type=Path); parser.add_argument('--phase', choices=['scene','review'])
    parser.add_argument('--companion', action='store_true', help='Use only for an actual user request to enable the companion')
    parser.add_argument('--service-url'); parser.add_argument('--timeout', type=float, default=12)
    args = parser.parse_args()
    result = prepare(args.root, args.thread_id, args.source, args.phase, args.companion, args.service_url, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] in {'conversation_only','backend_ready'} else 2


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError) as exc: sys.exit(str(exc))
