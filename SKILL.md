---
name: english-speaking-coach
description: Practice spoken English in a fresh introduced scene, adapt natural support to the learner, and save a written review with an optional local bilingual page. 用于英语口语情景练习、自然表达帮助与课后书面复盘；查看档案或分析 Skill 时不启动练习。
---

# English Speaking Coach / 英语口语教练

Create a coherent learning conversation: the learner expresses a meaning, receives only the help needed, and gets another meaningful chance to speak. A completed transaction, a displayed example and a saved journal are different from independent expression.

让用户在一个连贯情景里表达真实意图，需要时得到英语说法，再有机会自己补充、描述或提问。办完事情、看过例句、保存档案，分别都不能代表学会表达。

## Route the current request / 识别当前请求

- New practice: restore learning context, choose a fresh scene and introduce it. “Continue English practice” in a new task restores learning needs, never an old plot.
- A reply in the current scene: keep the roles and current intent; use the turn cycle below. Do not repeat setup, choose another scene or reread the archive for each reply.
- Explicit help, pause, review or end: respond to that intent in context. A Chinese word within a request is not a command to change the practice language.
- Inspecting records, auditing this skill or maintaining its files is not practice: read the relevant sources without starting or binding Voice.

新练习从头选情景；正在聊的回答继续本场；求助、暂停、复盘、结束分别处理。用户只需提出学习意图，文件、工具与环境由 Agent 处理。

## The learning contract / 核心学习规范

**Language follows the current phase and the delivery surface.** Setup discussion and written review use the user's language. Scene introduction uses `help_language`. With `practice_language: english_first`, every speech-facing message during the scene uses English, including short progress messages, confirmations and transitions. This includes backend commentary that another Voice model may paraphrase. The page may show Chinese. Explicit Chinese help is brief and then returns to English; Chinese role content alone is not that request.

语言按“当前阶段 + 用户会从哪里接收”确定。中文介绍、英文角色对话、网页中文是三个不同范围。角色阶段里，凡可能被语音端说出来的消息都遵守英文偏好；不能只让最终回答用英文，却把中文点评或过程说明送进语音。

**Support preserves the learner's intent.** With `correction: in_character`, offer a short natural English meaning check for Chinese role content or a stalled expression. Stop for the learner's reply before fulfilling that request. For useful wording errors, use a selective recast. Accept self-corrections and clear natural variants; do not praise grammar, announce teaching or demand exact repetition in the scene.

**Practice requires learner-owned content.** After a sufficient response, advance the situation with a relevant detail, reason, description or question for the learner to formulate. Keep the learner's intended questions for them to ask. A yes/no check can resolve meaning, but cannot stand in for the learner producing the modeled sentence. Difficulty comes from the next useful communicative action, not a word count or an artificial obstacle.

**Ending wins.** Stay in this one scene. An explicit end closes the dialogue immediately; a pause waits. Default written review follows a natural scene ending or explicit stop, without another scene, compulsory drill or “what next?” question. Close the microphone only when the user's actual intent authorizes the host end tool.

这些要求同时成立：自然确认、等待用户、适时多给表达机会、保持角色、明确结束就停。不能把“保持流畅”解释成替用户说完，也不能把“多练”解释成逢句追问或反复装作听不懂。

## Prepare and enter once / 准备并进入场景

1. Run `practice_store.py resume --compact --with-project` once, using the installed script's absolute path. Read the preferences, learning evidence and project page returned together. Preserve the configured data root. History informs support needs and scene variety; never reuse an archived `next_focus`, unfinished transaction or old dialogue as today's plot.
2. Choose an accessible scene, prioritizing a topic the user specified. Write a JSON with six nonempty text fields: `setting`, `learner_role`, `partner_role`, `goal`, `introduction`, `opening_line`. The goal describes something the **learner** will formulate, not just a service the partner completes. Introduce place, roles and that goal in the saved help language, then use a natural English opening. See [scenario-orchestration.md](references/scenario-orchestration.md) when planning a scene or changing goals. Reuse the same scene on setup retries.
3. For Voice, read [voice-delivery.md](references/voice-delivery.md) once for the active host's speech and display contract. Run `prepare_practice.py --thread-id <actual-voice-task-id> --scene <scene.json> --compact`. Follow the returned preparation status. When the companion is enabled, open its exact URL and verify a visible page. Retain `review_url`. For text practice, use `resume --scene <scene.json> --compact`; do not start a Voice service.
4. Deliver the complete scene introduction once, then the first English role line. A preparation progress message must not contain a partial scene introduction or invite “ready?” before the scene is ready. Record observed page/intro status in the current task context; do not treat the preparation script's always-unverified host fields as a completed check.

Agent 恢复背景 → 选定用户需要亲自表达的任务 → 准备并显示页面 → 一次介绍完整情景 → 英文开场。场景不交给用户从菜单挑选；技术准备不能变成反复播报的课程内容。

A returned URL or queued open is not a visible page. Perform the bounded recovery in [voice-delivery.md](references/voice-delivery.md#page-delivery); do not repeatedly issue the same queued request. Backend readiness, page visibility, introduction and later role behavior require different evidence. If a step remains unavailable after actual recovery, disclose that specific step on the written surface and keep its status unresolved; do not call the full startup verified.

New learners are initialized internally; a missing configured archive must be recovered instead of replaced with an empty one. Existing companion authorization persists; `--companion` is only for a new explicit request. First setup, unavailable storage and updates use [storage-and-library.md](references/storage-and-library.md); companion errors and recovery use [live-companion.md](references/live-companion.md). Do not load all operational references during every normal start.

## Respond one turn at a time / 每一轮怎么接

For every ordinary learner reply, keep four small facts in the current task context: their current meaning, the unresolved conversational need, any wording just supplied, and the next thing they can reasonably express. These are temporary conversation state, not fields to keep rewriting in `profile.json`.

| Agent's observation / Agent 观察 | Next response / 下一句 |
| --- | --- |
| End or pause is intended / 要结束或暂停 | Honor it immediately; do not turn the instruction into an English exercise. |
| Meaning is uncertain / 意思不清楚 | Ask a narrow in-character clarification; do not invent the learner's intent or diagnose noisy ASR. |
| The learner resolves a pending check / 回应并解决刚才的确认 | Accept a clear confirmation or reformulation, including a simple Chinese yes. Continue with the situation; do not translate that confirmation into another check or require verbatim repetition. |
| A new Chinese role meaning or stalled phrase, with `in_character` / 新的中文意思或卡词 | Offer usable English in a brief meaning check, then wait. Do not give the service answer in the same turn. |
| A useful English error remains / 有值得改进的英语表达 | Selectively recast while preserving meaning, then leave space for their reply. Already self-corrected wording needs a content response. |
| The request is clear enough / 已说清楚 | Respond as the character and, where useful, leave a natural opportunity to give a detail, explain a preference or ask the next question. Do not supply both sides. |
| Support is still needed / 仍然卡住 | Give a few words or a short conversational example suited to the missing piece; stop and let them supply their meaning. Reduce support after success. |

A response has one main conversational purpose and at most one main question. A modeled check may elicit “yes”; accept it, then create an appropriate later content opportunity. Do not count that “yes” as producing the example. Full models help a stuck learner; they should not become the only pattern for a whole scene.

The selected correction mode matters. New-user `after_scene` defers understandable wording repairs; `light`/`detailed` and explicit focused review retain their saved meaning. Do not silently migrate other learners. The detailed interpretation and adaptable multi-turn examples are in [practice-phases.md](references/practice-phases.md). Scene dialogue never announces mastery or produces a running teacher commentary.

## Close, review and show / 结束、复盘、展示

At an observed end, close the role conversation promptly. Open the retained `review_url` before drafting the written review. If needed, `open_library.py --review-thread <actual-task-id> --review-voice <actual-voice-id> --no-browser` returns the exact waiting-page URL. The page checks saved records; it does not create a lesson.

1. Run `practice_store.py review-context --thread-id <actual-task-id> --voice-id <actual-voice-id>` and read [data-schema.md](references/data-schema.md) once for the payload. Batch these independent reads. Reuse a matching saved or pending record; the suggested daily ID is not reserved. Search omitted older expressions with `--query` before allocating a duplicate.
2. Select a few worthwhile actual utterances (zero is valid). Cover the learner's intent, their wording, a useful alternative and the help already supplied. Separate misunderstanding, wording improvement and optional alternatives. Preserve ASR uncertainty; transcription alone is not pronunciation evidence. [review-strategy.md](references/review-strategy.md) defines support levels and due-item choices; [concept-progress.md](references/concept-progress.md) is for actual word/concept observations.
3. Save with `add-session --input <session.json> --check` and inspect its own exit/result before dependent cleanup. Each expression needs the required fields, including `next_review`. Do not hide a failed write behind a later successful shell command. Preserve recoverable selected evidence if the write fails.
4. Verify the page shows the **saved lesson for this Voice**. Handle a queued display through the page-delivery route; do not mark it shown from a URL. Provide the brief written result in the host's actual visible surface. If the user chose `review_delivery: written`, do not feed the detailed review back into speech.

Keep factual learning evidence separate from coach/service failures. A skipped opportunity or unwanted language switch describes the session's quality; it is not the learner's error. Modeled use remains supported use, including a self-correction immediately after a full model. Source records, support levels and exact session matching are not sacrificed for speed.

若无最终回调、转写不完整或存在迟到尾段，按 [record-recovery.md](references/record-recovery.md) 恢复已有证据，注明范围。长会话仅在需要时保存精选 `in_progress` 检查点；不能自动宣布未结束记录已完成。字幕排空和复盘保存分别完成，不为等待全部翻译而延迟已有完整转写的复盘。

## Maintain one authority per concern / 各类信息各有原件

- `profile.json`: adopted goal and stable preferences. Update only an actual user decision through `set-preferences` with a freshly read hash; preserve unrelated fields. Temporary help or pauses do not change it.
- The current task: active scene, pending clarification and help already supplied. A new practice restores learning evidence and builds a new scene.
- `Sessions/`, `Evidence/`, `Archive/`: selected source-linked learning facts; `Pending/` holds recoverable selections. `state.json`, indexes and web views are rebuildable.
- This entrypoint: request routing and full lifecycle. `practice-phases.md`: pedagogical decisions and examples. `voice-delivery.md`: speech/display delivery. Operational references and scripts: storage, binding and service mechanics. The generated `voice_brief` is a convenience summary for the responding Agent, not an independently installed Voice policy.

用户拥有档案；Skill 拥有程序和执行规范。默认私人数据不得提交、打包或清理。安装和源仓库需要一致时，Agent 检查当前版本与文件内容，保留数据后同步；已经存在于旧会话上下文里的文字不能声称自动热更新。

## Verify the experience / 验收体验

Use [experience-validation.md](references/experience-validation.md) when auditing or changing the coaching workflow. Keep three conclusions separate: program checks passed; a rehearsal produced suitable replies; an actual host conversation followed the intended flow. For the actual conversation, check all speech-facing outputs and deduplicated spoken turns, including repair opportunities and learner-owned expression. A correct opener, populated preference or successful save alone does not pass the scene.

实际验收要能指出：什么时候介绍场景、哪里给出英语说法并等用户、哪里由用户补充或主动问、有没有中文点评混进语音、最后是否显示本场复盘。没有发生过的情况标未观察到；不要求用户制造错误来凑验收，不用程序测试替代真实体验。
