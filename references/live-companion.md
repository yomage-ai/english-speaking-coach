# Bilingual Voice companion / 双语 Voice 伴随

Prepare this built-in companion automatically for every Voice practice, including first use, unless the learner explicitly disabled captions. The learner talks with the existing Voice interface; the page never captures audio. The existing archive server runs an ordinary background tailer and a tool-disabled, ephemeral Codex app-server connection. Only a new bound transcript segment starts a translation turn. Caption transport needs no AI busy polling or per-sentence forwarding; ordinary coaching callbacks remain separate.

用户用原有 Voice 说英语，网页显示双方原话与中文。后台普通程序等日志追加，有新片段才请求翻译。原话不纠错、不被译文替换；需要教学时仍由口语教练回应。

## Agent preparation / Agent 启动准备

1. Run `resume --compact --with-project` once to read current preferences, learning evidence and the project page together. `paths` is only needed for location diagnostics. Keep the same authoritative archive and current learning thread. Voice practice includes bounded translation requests through the learner's existing ChatGPT login; do not ask them to enable this built-in feature. A missing saved preference means captions are on. Respect an explicit request to stop using them via `disable`; never silently purchase credits, consume a reset or fall back to an API key. Reading records or installing the skill alone does not bind Voice or start translation.
2. Resolve the **actual Voice task ID**, using the current task identity or the explicit source task when handling a delegation. Do not bind the implementation task or a translator task. `start` can resolve an exact UUID filename under the local Codex sessions tree; it never chooses the newest arbitrary task. Verify the source header. A currently active Voice is continued; otherwise bind the **next** Voice in that task, without replaying closed sessions.
3. Choose the fresh scene using [scenario-orchestration.md](scenario-orchestration.md), then use `coach prepare --thread-id <voice-task-id> --scene <scene.json>` (add `--source <verified-jsonl>` when needed). Normal startup needs no `--companion` flag; that flag only restores a saved disable at the learner's request. This restores context, reads the project page, binds the exact source, reuses the existing service and checks its identity and live API. It waits finitely, preserves another task's active Voice, and returns the exact run URL. Do not stop at `paths`/`resume` and start an exercise before executing this entry. If an older installed implementation requires a restart, inspect identity and wait until no unrelated Voice is active; never launch a competing manager.
4. `backend_ready` requires the matching run/task/Voice, `ready=true`, and `stale=false`. Agent must then open and inspect the returned `/#live?run=…` in the host browser; the command reports `page_display: not_verified` because an HTTP response cannot prove a visible preview. Check `transcript_observed` separately. `waiting_backend`, `other_voice_active`, `ended` and errors do not count as ready. If tools are available but these steps were skipped, report an execution omission; only report a host limitation when the required tools/callback actually were unavailable. `probe` remains a separate login/model check, not a page or speech check.
5. Complete speech and visible-page delivery through [voice-delivery.md](voice-delivery.md). Keep source IDs and file operations with the Agent. The learner does not operate terminals, forward sentences or supervise setup.

<a id="handoff-boundary"></a>
## Delivery responsibility / 交付职责

Speech-facing output and visible page recovery are defined in [voice-delivery.md](voice-delivery.md), read once for the active host. The responding Agent handles each available learner turn through ordinary permitted replies; a separate instruction-update API is not a prerequisite for doing that well. The companion handles transcript display and translation only.

Backend readiness, a visible page and an observed spoken reply are separate outcomes. Use [experience-validation.md](experience-validation.md) for a real-session audit; do not count a passed file test or generated brief as evidence that the Voice followed the coaching rules.

语音输出与网页显示各有具体交付步骤；主规范负责完整学习流程，本文件只负责伴随程序的自动准备、绑定和恢复。每个可用回调都按当前偏好认真回应，不把缺少配置接口当成普通回应无法改进的理由。

Each binding covers one actual Voice, including consecutive Voices in the same task. If the host provides no execution opportunity, live binding may be missed. An earlier run's counts are not coverage for a new Voice. Inspect the current binding before maintenance and leave another task's active Voice alone.

## End and recovery / 结束与恢复

At an observed end, open the prepared `review_url` before drafting the written review. It is scoped by both task and Voice IDs; the read-only page checks for a matching saved source about once a second while visible, and stops automatic waiting after five minutes. It never creates a lesson or claims a waiting review is saved. Retain transcript selection, deduplication and validation; the browser navigates to the matching lesson after its source is committed. If the page was queued rather than displayed, Agent uses the available visible browser to open and inspect the exact URL. Existing translation/drain work remains separate from review generation.

结束后先显示本次复盘入口，保存完成后自动展示；网页只查询本地状态，不增加模型轮次。等待状态、已保存及读取失败分别显示，同一任务连续两场也按真实 Voice 区分。不为提速省略原话核对和复盘校验。

- The exact Voice close event starts a drain. The worker keeps reading complete lines for at least five quiet seconds, translates pending rows, then closes its owned Codex child. An Agent-observed end should also run `stop --run <binding-id>`; this requests a drain and is idempotent. It does not terminate Voice or other tasks. Check for `ended` or report the actual error. With no end event, 30 minutes without new transcript (or six hours per binding) expires it visibly.
- Restarting the archive service resumes a still-requested binding from its committed cursor. Completed translations persist. A model call interrupted before its result was committed may be sent again; do not claim exactly-once billing.
- Translation validation is per utterance: retain complete valid sentences, retry rejected sentences at most twice, and prioritize new sentences before retries. A bad unit never halts the following conversation. Only connection/protocol failures use the three-failure circuit breaker. The page offers a bounded retry; raw details live under More → diagnostics. A retry never switches source tasks.
- For a missed **closed** Voice, use `coach recover-voice` with the verified task ID, exact Voice ID and source. It snapshots only that Voice, marks the page as **after-Voice recovery**, and never changes the active binding or enabled preference. Repeated recovery is idempotent. Validation failures are isolated to their sentence; connection failures stop after a bounded retry. The page can queue this exact closed-Voice recovery with its retry button, preserving any unrelated active binding. `--refresh-translations` explicitly recomputes an ended run's translations after a translator fix. Originals and formal lesson records remain unchanged.
- Late segments arriving after the five-second close grace require explicit recovery; use the finite helper for an ended Voice, especially when another task now owns the active binding. An incomplete trailing line is left for a later snapshot. Invalid complete lines, conflicting IDs or a changed source identity fail visibly. Ordinary `resume` is for an existing binding that needs to continue; do not use it to displace another task's active run.
- After draining, perform normal selected-evidence lesson save and validation. Keep the existing lesson ID and duplicate rules. Neither an assistant's translation nor viewing Chinese proves independent ability.

结束时 Agent 请求当前绑定排空并检查结果，然后按原流程保存精选课次。后台只在明确绑定范围内读转写，不自动写“掌握”。超过结束宽限期才出现的尾段需要 Agent 恢复；不能承诺宿主任何延迟都无遗漏。

漏绑定的已结束场次由 `coach recover-voice` 定向恢复，页面明确标“结束后恢复”，不接管当前字幕。重新运行只补缺项；修复译文后才显式加 `--refresh-translations`。恢复缓存不替代精选课次保存，也不能算作会中实时覆盖。

## Data, runtime and limits / 数据、环境与边界

`<data-root>/Live/companion.sqlite3` is a private, transient SQLite cache (SQLite is included in the Go executable; no external database service). It stores the bound source, byte cursor, fragment IDs, English, Chinese, statuses and timestamps. Authoritative facts remain in `Sessions/`, `Evidence/` and `profile.json`. The page exposes at most 40 utterances per page and the 12 most recent companion runs. Caches older than seven days are removed when another run starts; this is ordinary cache cleanup, not secure disk erasure. Obsidian need not read this runtime cache. The automatic learning recovery ZIP excludes it; user-managed whole-folder backups remain under the user’s own retention policy.

The standalone Go companion includes its own runtime, SQLite and TOML reader. No Python, Node.js or Go installation is required. It still needs a current Codex CLI supporting app-server and that user’s existing login. Agent checks the desktop bundled binary before an older PATH CLI; `ENGLISH_COACH_CODEX` may explicitly select a verified binary. No global CLI upgrade or auth-file copy is needed. New live bindings select `gpt-5.6-sol` with `low` for combined translation and teaching, independently of the speaking model. Standalone recovery defaults to the same `gpt-5.6-sol` with `low`; an explicit verified `--model` remains available. Existing explicit binding choices remain unchanged. It calls the hosted model with that user's ChatGPT login and quota; model weights are not bundled or run locally. Availability is verified against that account's model list; an unavailable model produces an error, with no silent fallback to another model. The app-server connection is reused for up to 20 turns, then replaced to bound translation context. Each batch has up to three segments, normally up to 4,500 characters; original single segments are limited to 12,000 characters.

Shell, exec, apps, plugins, MCP, browsing, hooks, subagents and related tools are disabled in the translator's local process configuration. Transcript content is untrusted translation input. No configuration is written globally. Unexpected tool/approval requests abort the connection. The server uses a scratch working directory, ephemeral threads and no history persistence; the program never tails those threads. Existing account/platform request logging is outside this local cache's control.

The program enumerates every English span in mixed Chinese/English segments and requires a Chinese meaning for each, including quoted teaching examples. Missing IDs or an English echo fail validation; a narrow proper-name exception preserves names, including internal capitals such as iPad or eBay; a casing signal alone does not establish name semantics. Chinese-only segments need no translation request when teaching is disabled; during live practice the same combined request can supply English wording help. These checks prevent omissions, but do not prove semantic perfection; the original remains available beside the separate Chinese display.

中英混合句按英文片段逐项翻译，中文说明中引用的例句也要有中文句意。缺项或照抄英文不会标记完成，专名可保留原拼写；仅翻译模式下纯中文不请求模型；练习中的纯中文可在同一次合并请求中获得英语表达帮助。程序能检查覆盖，不能保证译意永远准确，原话始终保留。

页面只连本机；翻译需要现有 Codex 登录及网络，会使用账户额度。没有新片段就没有模型轮次。默认每批至多三条，连接每二十轮轮换。临时缓存只用于字幕回看，正式档案仍在原目录。服务由现有档案管理器托管；没有额外麦克风、录音权限或网站。

Local tests cover incremental reading, deduplication, half UTF-8 lines, finite errors, restart recovery, filtering and end draining. Actual translation latency must be measured on the host. Voice timestamps alone do not prove that the host flushes transcript during an active call. User Voice trial still needs to establish speech-to-file delay, coverage and end-to-end comfort. Updating skill instructions cannot force a host that missed skill loading or lacks a tool callback to run this setup.

本地程序验证与真实 Voice 体验分开报告。会中是否及时写盘、实际漏句情况和听说效果，需要真实试用。Skill 说明无法强制宿主正确加载或提供回调。

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

正常新 Voice 用统一准备入口，底层 start/status/stop 保留给诊断与收尾。入口输出后台核验和页面地址，Agent 仍须实际打开并检查。没有可见预览就说“后台已就绪，页面尚未核验”；没有实际转写就说“等待转写”，不冒充字幕已同步。这个入口不主动开启用户麦克风，也不安装全局监控。

## Current written help / 当前一句提示

Live translation streams first; a complete validated translation array can display before the same request finishes its optional teaching hint. Teaching receives only the current scene/profile and up to 30 recent bound segments. It shows one exact-source-linked English model or next cue. It hides on changed/new learner wording, older pages and closed practice; suggestions never count as speech or mastery. Short models keep one reading group. No additional per-hint model call is made. A source-text condition prevents an old in-flight translation from overwriting a revised segment.

字幕先显示；同一次请求再给当前一句表达或下一步提示。提示独立于原话，不是 Voice 已说的话，也不表示已掌握。新发言、原话修订或结束练习后，旧提示隐藏。明确的续接片段保留原文并标注可能的连读词，不把词尾单独当生词翻译；程序不推断发音。

## Compact reading surface / 紧凑阅读界面

The live page dedicates its remaining viewport to one scrolling transcript. Chinese, the exact review link and follow/pause controls stay visible; the scene, session selector, archive navigation, local folder and raw diagnostics live under More. Pause controls automatic scrolling only: new text and delayed translations keep arriving. The review link reflects saved/generating/error state without a separate large banner. Only a verified native Voice close starts final review; speaking an end phrase without a host callback cannot be represented as a closed source.

双语页优先显示原话和中文；场景、场次、学习目录与诊断收进“更多”。暂停只停止自动滚动，转写和翻译仍继续接收。本次复盘入口直接显示整理或保存状态。口头说结束不一定关闭 Voice；未收到真实关闭信号时明确提示，不能把仍开启的窗口伪装成已结束的证据。
