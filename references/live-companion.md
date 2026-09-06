# Bilingual Voice companion / 双语 Voice 伴随

Use this mode when the learner requests a local bilingual page alongside Codex Voice, or has already enabled it. The learner talks with the existing Voice interface; the page never captures audio. The existing archive server runs an ordinary background tailer and a tool-disabled, ephemeral Codex app-server connection. Only a new bound transcript segment starts a translation turn. No AI busy polling or per-sentence forwarding by the Voice agent.

用户用原有 Voice 说英语，网页显示双方原话与中文。后台普通程序等日志追加，有新片段才请求翻译。原话不纠错、不被译文替换；需要教学时仍由口语教练回应。

## Agent preparation / Agent 启动准备

1. Run `resume --compact --with-project` once to read current preferences, learning evidence and the project page together. `paths` is only needed for location diagnostics. Keep the same authoritative archive and current learning thread. The companion is optional for new users; a request to use it authorizes these bounded translation requests through their existing ChatGPT login. Successful non-demo binding remembers `enabled=true`. Respect a request to stop using it via `disable`; never silently purchase credits, consume a reset or fall back to an API key.
2. Resolve the **actual Voice task ID**, using the current task identity or the explicit source task when handling a delegation. Do not bind the implementation task or a translator task. `start` can resolve an exact UUID filename under the local Codex sessions tree; it never chooses the newest arbitrary task. Verify the source header. A currently active Voice is continued; otherwise bind the **next** Voice in that task, without replaying closed sessions.
3. Choose the fresh scene using [scenario-orchestration.md](scenario-orchestration.md), then use `prepare_practice.py --thread-id <voice-task-id> --scene <scene.json>` (add `--source <verified-jsonl>` when needed, `--companion` only for a new explicit enable request). This restores context, reads the project page, binds the exact source, reuses the existing service and checks its identity and live API. It waits finitely, preserves another task's active Voice, and returns the exact run URL. Do not stop at `paths`/`resume` and start an exercise before executing this entry. If an older installed implementation requires a restart, inspect identity and wait until no unrelated Voice is active; never launch a competing manager.
4. `backend_ready` requires the matching run/task/Voice, `ready=true`, and `stale=false`. Agent must then open and inspect the returned `/#live?run=…` in the host browser; the command reports `page_display: not_verified` because an HTTP response cannot prove a visible preview. Check `transcript_observed` separately. `waiting_backend`, `other_voice_active`, `ended` and errors do not count as ready. If tools are available but these steps were skipped, report an execution omission; only report a host limitation when the required tools/callback actually were unavailable. `probe` remains a separate login/model check, not a page or speech check.
5. Follow the host's actual handoff contract, using the distinction below. Preserve the chosen scene and restored preferences, but do not equate an ordinary response with an instruction-update API. Reading files is not a completed startup, and generating a brief does not prove Voice received or followed it. Keep IDs and file operations with the tool Agent; learners do not operate terminals or forward sentences.

<a id="handoff-boundary"></a>
## Handoff boundary / 交接边界

The tool Agent and the frontend Voice model may receive different instructions. `voice_brief` is guidance for practice, not a host configuration change. For text practice the current Agent can use that guidance directly. For Voice, inspect the active host contract and callable capabilities:

- A documented instruction-update API may receive practice guidance within its allowed scope. Verify its response; report observed conversation behavior separately.
- An ordinary backend reply may carry concise, speech-safe facts about the selected scene, saved preferences and readiness. It does not establish that Voice adopted those preferences. A host rule prohibiting instructions addressed to the frontend takes precedence over this Skill. Do not paste raw guidance, add “apply silently,” encode it, or reword commands as facts to bypass that rule.
- Without a permitted instruction interface, report the limitation. Do not label the scene's correction or speaking-opportunity behavior as configured or verified, and do not send recurring background messages to simulate control of Voice.

后台 Agent 与语音模型可能使用不同上下文。普通后台回复可以依宿主协议简述已核实的场景、用户偏好和准备结果，但不等于更新语音规则。禁止给前端模型发送指令的宿主中，不转发提示词、不伪装或绕过限制；没有允许的接口就如实报告。中文介绍、英文角色对话、网页双语是分别保存的偏好，不因传递受限而改写用户选择。

For a real-session audit, check loaded preferences, permitted delivery and unique observed turns separately. Inspect a Chinese/stalled-expression opportunity and a learner-owned question opportunity when present. Deduplicate cumulative transcripts, treat unclear ASR as uncertain, and do not require every short answer to become a drill. A passing file test or correct opening cannot substitute for those observations.

真实验收分别检查偏好读取、允许的传递方式和去重后的实际回合；有中文/卡词、主动提问目标时，再判断是否给出英语确认和表达空间。不要把测试通过、保存成功或开场正确算作会中练习效果通过。

Agent 先恢复学习，再绑定实际 Voice 所在任务。新用户主动提出伴随需求即可启用，已启用者不反复征询。Agent 完成依赖检查、服务复用与页面检查；用户只需说英语。`bound` 不等于已就绪；须核对任务 ID、后台心跳和 `ready=true`。网页仍为空时，不声称已看到实时转写。

Each binding covers one Voice. A second Voice in the same task needs a fresh `start` and readiness check. If the host gives the Agent no execution opportunity, that Voice may be missed live. Do not use an earlier run's counts as coverage for the new Voice. Before maintenance or rebinding, inspect the current binding; leave another task's active Voice alone.

先介绍新场景，再开始英文角色对话。同一任务连续开两场 Voice，也必须逐场绑定。宿主没有执行回调时，Agent 不能自动接上；要如实说明会中漏绑定，不能沿用上一场完成数。`voice_brief` 已生成不等于已交给 Voice；没有可用交接接口时，不声称已注入。维护前核对当前绑定，不打断其他任务正在用的 Voice。

## End and recovery / 结束与恢复

At an observed end, open the prepared `review_url` before drafting the written review. It is scoped by both task and Voice IDs; the read-only page checks for a matching saved source about once a second while visible, and stops automatic waiting after five minutes. It never creates a lesson or claims a waiting review is saved. Retain transcript selection, deduplication and validation; the browser navigates to the matching lesson after its source is committed. If the page was queued rather than displayed, Agent uses the available visible browser to open and inspect the exact URL. Existing translation/drain work remains separate from review generation.

结束后先显示本次复盘入口，保存完成后自动展示；网页只查询本地状态，不增加模型轮次。等待状态、已保存及读取失败分别显示，同一任务连续两场也按真实 Voice 区分。不为提速省略原话核对和复盘校验。

- The exact Voice close event starts a drain. The worker keeps reading complete lines for at least five quiet seconds, translates pending rows, then closes its owned Codex child. An Agent-observed end should also run `stop --run <binding-id>`; this requests a drain and is idempotent. It does not terminate Voice or other tasks. Check for `ended` or report the actual error. With no end event, 30 minutes without new transcript (or six hours per binding) expires it visibly.
- Restarting the archive service resumes a still-requested binding from its committed cursor. Completed translations persist. A model call interrupted before its result was committed may be sent again; do not claim exactly-once billing.
- Two failed attempts on a batch stop automatic translation visibly. Preserve the English and error. After Agent fixes the cause, `resume --run <id>` explicitly retries failed rows and reads any later tail for the same binding. It never automatically switches source tasks. A normal new Voice uses `start` after the old binding has ended.
- For a missed **closed** Voice, use `recover_voice.py` with the verified task ID, exact Voice ID and source. It snapshots only that Voice, marks the page as **after-Voice recovery**, and never changes the active binding or enabled preference. Repeated recovery is idempotent; at most two failed attempts per batch stop it visibly. `--refresh-translations` explicitly recomputes an ended run's translations after a translator fix. Originals and formal lesson records remain unchanged.
- Late segments arriving after the five-second close grace require explicit recovery; use the finite helper for an ended Voice, especially when another task now owns the active binding. An incomplete trailing line is left for a later snapshot. Invalid complete lines, conflicting IDs or a changed source identity fail visibly. Ordinary `resume` is for an existing binding that needs to continue; do not use it to displace another task's active run.
- After draining, perform normal selected-evidence lesson save and validation. Keep the existing lesson ID and duplicate rules. Neither an assistant's translation nor viewing Chinese proves independent ability.

结束时 Agent 请求当前绑定排空并检查结果，然后按原流程保存精选课次。后台只在明确绑定范围内读转写，不自动写“掌握”。超过结束宽限期才出现的尾段需要 Agent 恢复；不能承诺宿主任何延迟都无遗漏。

漏绑定的已结束场次由 `recover_voice.py` 定向恢复，页面明确标“结束后恢复”，不接管当前字幕。重新运行只补缺项；修复译文后才显式加 `--refresh-translations`。恢复缓存不替代精选课次保存，也不能算作会中实时覆盖。

## Data, runtime and limits / 数据、环境与边界

`<data-root>/Live/companion.sqlite3` is a private, transient SQLite cache (Python standard library; no external database service). It stores the bound source, byte cursor, fragment IDs, English, Chinese, statuses and timestamps. Authoritative facts remain in `Sessions/`, `Evidence/` and `profile.json`. The page exposes at most 40 utterances per page and the 12 most recent companion runs. Caches older than seven days are removed when another run starts; this is ordinary cache cleanup, not secure disk erasure. Obsidian need not read this runtime cache. The automatic learning recovery ZIP excludes it; user-managed whole-folder backups remain under the user’s own retention policy.

The optional translator requires Python 3.11+ and a current Codex CLI supporting app-server. Agent checks the desktop bundled binary before an older PATH CLI; `ENGLISH_COACH_CODEX` may explicitly select a verified binary. No global CLI upgrade or auth-file copy is needed. Default model is `gpt-5.6-luna` with `low`, verified against the logged-in model list; no silent fallback to another model. It uses account quota. The app-server connection is reused for up to 20 turns, then replaced to bound translation context. Each batch has up to three segments, normally up to 4,500 characters; original single segments are limited to 12,000 characters.

Shell, exec, apps, plugins, MCP, browsing, hooks, subagents and related tools are disabled in the translator's local process configuration. Transcript content is untrusted translation input. No configuration is written globally. Unexpected tool/approval requests abort the connection. The server uses a scratch working directory, ephemeral threads and no history persistence; the program never tails those threads. Existing account/platform request logging is outside this local cache's control.

The program enumerates every English span in mixed Chinese/English segments and requires a Chinese meaning for each, including quoted teaching examples. Missing IDs or an English echo fail validation; a narrow proper-name exception preserves names. Chinese-only segments need no model request. These checks prevent omissions, but do not prove semantic perfection; the original remains available beside the separate Chinese display.

中英混合句按英文片段逐项翻译，中文说明中引用的例句也要有中文句意。缺项或照抄英文不会标记完成，专名可保留原拼写；纯中文不请求模型。程序能检查覆盖，不能保证译意永远准确，原话始终保留。

页面只连本机；翻译需要现有 Codex 登录及网络，会使用账户额度。没有新片段就没有模型轮次。默认每批至多三条，连接每二十轮轮换。临时缓存只用于字幕回看，正式档案仍在原目录。服务由现有档案管理器托管；没有额外麦克风、录音权限或网站。

Local tests cover incremental reading, deduplication, half UTF-8 lines, finite errors, restart recovery, filtering and end draining. Actual translation latency must be measured on the host. Voice timestamps alone do not prove that the host flushes transcript during an active call. User Voice trial still needs to establish speech-to-file delay, coverage and end-to-end comfort. Updating skill instructions cannot force a host that missed skill loading or lacks a tool callback to run this setup.

本地程序验证与真实 Voice 体验分开报告。会中是否及时写盘、实际漏句情况和听说效果，需要真实试用。Skill 说明无法强制宿主正确加载或提供回调。

```bash
# Agent-only commands; ordinary users simply request the feature.
python3 <skill>/scripts/live_companion.py probe
python3 <skill>/scripts/prepare_practice.py --thread-id <actual-voice-task-id>
python3 <skill>/scripts/live_companion.py start --thread-id <actual-voice-task-id>
python3 <skill>/scripts/open_library.py --page live --no-browser
python3 <skill>/scripts/live_companion.py status
python3 <skill>/scripts/live_companion.py stop --run <binding-id>
python3 <skill>/scripts/live_companion.py resume --run <binding-id>
python3 <skill>/scripts/recover_voice.py --thread-id <verified-task-id> --voice-id <closed-voice-id> --source <verified-jsonl>
python3 <skill>/scripts/live_companion.py disable
```

正常新 Voice 用统一准备入口，底层 start/status/stop 保留给诊断与收尾。入口输出后台核验和页面地址，Agent 仍须实际打开并检查。没有可见预览就说“后台已就绪，页面尚未核验”；没有实际转写就说“等待转写”，不冒充字幕已同步。这个入口不主动开启用户麦克风，也不安装全局监控。
