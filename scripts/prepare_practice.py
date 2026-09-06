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
from practice_context import compact_context, review_route


def open_service(root, service_url=None):
    command = [sys.executable, str(SKILL_ROOT/'scripts/open_library.py'), '--root', str(root), '--page', 'overview', '--no-browser']
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


def service_base(service):
    parsed = urlsplit(service['url'])
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1','localhost'} or parsed.username:
        raise ValueError('Service must return a loopback URL')
    return parsed.scheme + '://' + parsed.netloc


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
            service_url=None, timeout=12, opener=open_service, reader=read_live, scene=None):
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
    context = resume(root, str(date.today()), phase, scene=scene)
    page = workspace.get('project_page')
    project_context = Path(page).read_text(encoding='utf-8') if page else None
    result = {'context':context, 'workspace':workspace, 'project_context':project_context,
              'startup_complete':False,
              'checks':{'context_restored':True, 'project_page':workspace.get('project_page'),
                        'scene_selected':context['startup']['scene_selected'],
                        'binding_verified':False, 'backend_ready':False, 'page_display':'not_verified',
                        'voice_handoff':'not_verified'}}
    if context['startup']['scene_required'] and not context['startup']['scene_selected']:
        return {**result, 'status':'needs_scene', 'url':None,
                'next_action':context['startup']['next_action']}
    if not (enable_companion or context['companion']['enabled']):
        try:
            service = opener(root, service_url)
            return {**result, 'status':'conversation_only',
                    'url':service_base(service) + '/#overview', 'service':service.get('service', {}),
                    'next_action':'Agent: automatically open this learning page and verify it is visible before introducing the scene. Captions remain disabled; do not bind Voice or enable translation. At the end, save and show the matching written review.'}
        except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
            return {**result, 'status':'preparation_error', 'url':None, 'error':str(exc),
                    'next_action':'Agent: inspect the archive service error. No page display has been verified.'}
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
    result['context'] = resume(root, str(date.today()), phase, scene=scene)
    try:
        service = opener(root, service_url)
        base = service_base(service)
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
        if result['checks']['voice_id']:
            result['review_url'] = base + '/' + review_route(thread_id, result['checks']['voice_id'])
        result['next_action'] = ('Agent: complete page delivery using references/voice-delivery.md: open this exact URL, inspect the visible result, and recover a queued display through an available permitted browser route. Introduce the complete scene once. Use the restored turn cycle for ordinary learner replies; all speech-facing scene messages follow the practice language. context.voice_brief is local guidance, never a prohibited prompt relay. Keep preparation diagnostics on the appropriate written surface. Backend readiness is not startup completion; verify actual opening and dialogue separately. Observe transcripts after speech, not as a prerequisite for the first line.'
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
    parser.add_argument('--scene', type=Path, help='Agent-authored fresh scene JSON; required for roleplay startup')
    parser.add_argument('--companion', action='store_true', help='Restore captions after an explicit user request to undo a saved disable; normal Voice practice needs no flag')
    parser.add_argument('--service-url'); parser.add_argument('--timeout', type=float, default=12)
    parser.add_argument('--compact', action='store_true', help='After resume --with-project, omit repeated history and project text')
    args = parser.parse_args()
    scene = json.loads(args.scene.read_text(encoding='utf-8')) if args.scene else None
    result = prepare(args.root, args.thread_id, args.source, args.phase, args.companion, args.service_url, args.timeout, scene=scene)
    if args.compact:
        result['context'] = compact_context(result['context'], prepared=True)
        result.pop('project_context', None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] in {'conversation_only','backend_ready'} else 2


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError) as exc: sys.exit(str(exc))
