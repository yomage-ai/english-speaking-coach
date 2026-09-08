# Bilingual Voice companion

Prepare this built-in companion automatically for every Voice practice, including first use, unless the learner explicitly disabled captions. The learner talks with the existing Voice interface; the page never captures audio. The existing archive server runs an ordinary background tailer and a tool-disabled, ephemeral Codex app-server connection. Only a new bound transcript segment starts a translation turn. Caption transport needs no AI busy polling or per-sentence forwarding; ordinary coaching callbacks remain separate.

## Agent preparation

1. Run `resume --compact --with-project` once to read current preferences, learning evidence and the project page together. `paths` is only needed for location diagnostics. Keep the same authoritative archive and current learning thread. Voice practice includes bounded translation requests through the learner's existing ChatGPT login; do not ask them to enable this built-in feature. A missing saved preference means captions are on. Respect an explicit request to stop using them via `disable`; never silently purchase credits, consume a reset or fall back to an API key. Reading records or installing the skill alone does not bind Voice or start translation.
2. Resolve the **actual Voice task ID**, using the current task identity or the explicit source task when handling a delegation. Do not bind the implementation task or a translator task. `start` can resolve an exact UUID filename under the local Codex sessions tree; it never chooses the newest arbitrary task. Verify the source header. A currently active Voice is continued; otherwise bind the **next** Voice in that task, without replaying closed sessions.
3. Choose the fresh scene using [scenario-orchestration.md](scenario-orchestration.md), then use `coach prepare --thread-id <voice-task-id> --scene <scene.json>` (add `--source <verified-jsonl>` when needed). Normal startup needs no `--companion` flag; that flag only restores a saved disable at the learner's request. This restores context, reads the project page, binds the exact source, reuses the existing service and checks its identity and live API. It waits finitely, preserves another task's active Voice, and returns the exact run URL. Do not stop at `paths`/`resume` and start an exercise before executing this entry. If an older installed implementation requires a restart, inspect identity and wait until no unrelated Voice is active; never launch a competing manager.
4. `backend_ready` requires the matching run/task/Voice, `ready=true`, and `stale=false`. Agent must then open and inspect the returned `/#live?run=…` in the host browser; the command reports `page_display: not_verified` because an HTTP response cannot prove a visible preview. Check `transcript_observed` separately. `waiting_backend`, `other_voice_active`, `ended` and errors do not count as ready. If tools are available but these steps were skipped, report an execution omission; only report a host limitation when the required tools/callback actually were unavailable. `probe` remains a separate login/model check, not a page or speech check.
5. Complete speech and visible-page delivery through [voice-delivery.md](voice-delivery.md). Keep source IDs and file operations with the Agent. The learner does not operate terminals, forward sentences or supervise setup.

<a id="handoff-boundary"></a>
## Delivery responsibility

Speech-facing output and visible page recovery are defined in [voice-delivery.md](voice-delivery.md), read once for the active host. The responding Agent handles each available learner turn through ordinary permitted replies; a separate instruction-update API is not a prerequisite for doing that well. The companion handles transcript display and translation only.

Backend readiness, a visible page and an observed spoken reply are separate outcomes. Use [experience-validation.md](experience-validation.md) for a real-session audit; do not count a passed file test or generated brief as evidence that the Voice followed the coaching rules.

Each binding covers one actual Voice, including consecutive Voices in the same task. If the host provides no execution opportunity, live binding may be missed. An earlier run's counts are not coverage for a new Voice. Inspect the current binding before maintenance and leave another task's active Voice alone.

## End and recovery

At an observed end, open the prepared `review_url` before drafting the written review. It is scoped by both task and Voice IDs; the read-only page checks for a matching saved source about once a second while visible, and stops automatic waiting after five minutes. It never creates a lesson or claims a waiting review is saved. Retain transcript selection, deduplication and validation; the browser navigates to the matching lesson after its source is committed. If the page was queued rather than displayed, Agent uses the available visible browser to open and inspect the exact URL. Existing translation/drain work remains separate from review generation.

- The exact Voice close event starts a drain. The worker keeps reading complete lines for at least five quiet seconds, translates pending rows, then closes its owned Codex child. An Agent-observed end should also run `stop --run <binding-id>`; this requests a drain and is idempotent. It does not terminate Voice or other tasks. Check for `ended` or report the actual error. With no end event, 30 minutes without new transcript (or six hours per binding) expires it visibly.
- Restarting the archive service resumes a still-requested binding from its committed cursor. Completed translations persist. A model call interrupted before its result was committed may be sent again; do not claim exactly-once billing.
- Two failed attempts on a batch stop automatic translation visibly. Preserve the English and error. After Agent fixes the cause, `resume --run <id>` explicitly retries failed rows and reads any later tail for the same binding. It never automatically switches source tasks. A normal new Voice uses `start` after the old binding has ended.
- For a missed **closed** Voice, use `coach recover-voice` with the verified task ID, exact Voice ID and source. It snapshots only that Voice, marks the page as **after-Voice recovery**, and never changes the active binding or enabled preference. Repeated recovery is idempotent; at most two failed attempts per batch stop it visibly. `--refresh-translations` explicitly recomputes an ended run's translations after a translator fix. Originals and formal lesson records remain unchanged.
- Late segments arriving after the five-second close grace require explicit recovery; use the finite helper for an ended Voice, especially when another task now owns the active binding. An incomplete trailing line is left for a later snapshot. Invalid complete lines, conflicting IDs or a changed source identity fail visibly. Ordinary `resume` is for an existing binding that needs to continue; do not use it to displace another task's active run.
- After draining, perform normal selected-evidence lesson save and validation. Keep the existing lesson ID and duplicate rules. Neither an assistant's translation nor viewing Chinese proves independent ability.

## Data, runtime and limits

`<data-root>/Live/companion.sqlite3` is a private, transient SQLite cache (SQLite is included in the Go executable; no external database service). It stores the bound source, byte cursor, fragment IDs, English, Chinese, statuses and timestamps. Authoritative facts remain in `Sessions/`, `Evidence/` and `profile.json`. The page exposes at most 40 utterances per page and the 12 most recent companion runs. Caches older than seven days are removed when another run starts; this is ordinary cache cleanup, not secure disk erasure. Obsidian need not read this runtime cache. The automatic learning recovery ZIP excludes it; user-managed whole-folder backups remain under the user’s own retention policy.

The standalone Go companion includes its own runtime, SQLite and TOML reader. No Python, Node.js or Go installation is required. It still needs a current Codex CLI supporting app-server and that user’s existing login. Agent checks the desktop bundled binary before an older PATH CLI; `ENGLISH_COACH_CODEX` may explicitly select a verified binary. No global CLI upgrade or auth-file copy is needed. New live bindings select `gpt-5.6-sol` with `low` for combined translation and teaching, independently of the speaking model. Standalone recovery defaults to the same `gpt-5.6-sol` with `low`; an explicit verified `--model` remains available. Existing explicit binding choices remain unchanged. It calls the hosted model with that user's ChatGPT login and quota; model weights are not bundled or run locally. Availability is verified against that account's model list; an unavailable model produces an error, with no silent fallback to another model. The app-server connection is reused for up to 20 turns, then replaced to bound translation context. Each batch has up to three segments, normally up to 4,500 characters; original single segments are limited to 12,000 characters.

Shell, exec, apps, plugins, MCP, browsing, hooks, subagents and related tools are disabled in the translator's local process configuration. Transcript content is untrusted translation input. No configuration is written globally. Unexpected tool/approval requests abort the connection. The server uses a scratch working directory, ephemeral threads and no history persistence; the program never tails those threads. Existing account/platform request logging is outside this local cache's control.

The program enumerates every English span in mixed Chinese/English segments and requires a Chinese meaning for each, including quoted teaching examples. Missing IDs or an English echo fail validation; a narrow proper-name exception preserves names. Chinese-only segments need no translation request when teaching is disabled; during live practice the same combined request can supply English wording help. These checks prevent omissions, but do not prove semantic perfection; the original remains available beside the separate Chinese display.

Local tests cover incremental reading, deduplication, half UTF-8 lines, finite errors, restart recovery, filtering and end draining. Actual translation latency must be measured on the host. Voice timestamps alone do not prove that the host flushes transcript during an active call. User Voice trial still needs to establish speech-to-file delay, coverage and end-to-end comfort. Updating skill instructions cannot force a host that missed skill loading or lacks a tool callback to run this setup.

```bash
# Agent-only commands; the companion is prepared as part of Voice practice.
<skill>/scripts/coach live probe
<skill>/scripts/coach prepare --thread-id <actual-voice-task-id>
<skill>/scripts/coach live start --thread-id <actual-voice-task-id>
<skill>/scripts/coach open --page live --no-browser
<skill>/scripts/coach live status
<skill>/scripts/coach live stop --run <binding-id>
<skill>/scripts/coach live resume --run <binding-id>
<skill>/scripts/coach recover-voice --thread-id <verified-task-id> --voice-id <closed-voice-id> --source <verified-jsonl>
<skill>/scripts/coach live disable
```

## Current written help

Live translation streams first; a complete validated translation array can display before the same request finishes its optional teaching hint. Teaching receives only the current scene/profile and up to 30 recent bound segments. It shows one exact-source-linked English model or next cue. It hides on changed/new learner wording, older pages and closed practice; suggestions never count as speech or mastery. Short models keep one reading group. No additional per-hint model call is made. A source-text condition prevents an old in-flight translation from overwriting a revised segment.
