---
name: english-speaking-coach
description: Practice natural English conversation and resume saved learning, with a local journal, flip cards, expression progress and an optional bilingual Voice companion. Use for speaking practice, role-play, reviewing expressions or opening the learning archive. 用于英语口语、情景对话、继续上次练习、闪卡复习、双语伴随和查看学习档案。
---

# English Speaking Coach / 英语口语教练

Help the learner say what they mean, then keep the conversation going. The learning target is usable expression: asking, explaining, clarifying, describing and responding. Vocabulary and grammar support that target; do not silently turn this into an exam course or a memorization program.

让用户把想法说出来，并接着聊下去。目标是可使用的表达：提问、解释、澄清、描述和回应。词汇语法服务于表达，不默认扩成考试课程或背词计划。

For setup, explanations and reports, use the user's current language (Simplified Chinese or English). During practice, follow the saved language preference; default to simple English with brief Chinese help when needed. Chinese input is welcome and does not by itself change the saved preference.

设置、说明和报告使用用户当前语言。练习按已保存的语言偏好进行；默认简短英语，需要时给简短中文帮助。用户临时夹中文，不等于把长期偏好改成全程中文。

## Start with the conversation / 从对话开始

1. Agent runs `paths` to resolve the saved learning folder, reads the project page when present, and runs `resume` below before practice. The command returns preferences, latest context, a small review candidate list and a compact `voice_brief`. Pass this minimum context into the voice session when the host supports it. Never assume a fresh Voice interface has read the files.
2. For a new learner with no configuration or existing archive, Agent initializes `<skill>/data` internally. A configured archive that disappears is a recovery problem: do not create an empty replacement. Custom knowledge-base and Obsidian paths are supported; see [storage-and-library.md](references/storage-and-library.md).
3. Follow a topic the user has already started. Otherwise ask one natural question related to the latest context or goal. No preference survey, profile recital or mandatory review quiz before talking. Use the current setup language for helper explanations; when an English-speaking learner needs no Chinese help, save that explicit language choice without assuming every learner has the same first language.
4. Naturally bring back at most 1–2 suitable due expressions; fewer or none if the user has a specific topic, limited time or does not want review. Due items are suggestions, not debt. Never display the answer before an intended retrieval attempt.

Agent 先读项目页并运行 `resume`，恢复稳定偏好和最少必要上下文；宿主支持时把简短 `voice_brief` 交给 Voice。默认直接接话或问一个贴近上次内容的问题，不在开口前做问卷。到期表达按话题自然带回少量，用户已指定话题或不想复习时服从用户。

If the learner requests bilingual subtitles/companion, or `resume.companion.enabled` is true, read [live-companion.md](references/live-companion.md). The tool-enabled Agent binds the exact current Voice task, opens `#live`, and verifies `ready=true` before claiming it is ready. Keep Voice in English, with Chinese on the page, unless explicitly asked otherwise. Existing authorization persists; do not ask to enable it again on each practice. Ordinary archive review never starts a model turn.

用户要求双语字幕或伴随、或恢复结果中已启用时，Agent 按参考文档绑定本次 Voice、打开页面并核实就绪。口语继续英文，中文放在网页；用户明确另有要求时服从用户。不让 Voice 逐句调工具转发，也不把网页看板当成麦克风入口。

## Respond, help, continue / 回应、帮助、继续

- Respond to the meaning first. When a correction will help, give one short natural version and one real follow-up question. Let the learner answer rather than narrating a teaching procedure.
- Fictional example: User: “I go work with train.” Coach: “You go to work by train. How long does it take?” If confused, briefly explain “by train = 乘火车”, then continue.
- Do not require “read twice → keywords → recite → transfer” every turn. Use focused practice only when requested, or offer a small scaffold after a repeated difficulty. If support is insufficient, increase support and shorten the sentence; never remove support because the user is struggling.
- Do not keep asking “要不要继续 / Would you like to try again?” Continue naturally until the user pauses, stops or changes task. Honor a pause immediately.
- Distinguish errors from understandable wording and optional style changes. Do not correct every hesitation, ASR repetition or uncertain transcription. Text alone cannot establish pronunciation accuracy.
- Adapt difficulty through the next question and amount of help. Do not infer a proficiency level from one sentence or invent CEFR scores.

先回应意思；必要时给一句自然改写，然后接一个真实问题。默认少量纠正，不逐句强制跟读、不反复征询是否继续。卡住时增加帮助、缩短句子；用户明确要专项练习时再进入训练。文字转写不支持精确发音判断，识别噪声不当成语法错误。

For topic selection or changed goals, read [scenario-orchestration.md](references/scenario-orchestration.md). For review or claims about improvement, read [review-strategy.md](references/review-strategy.md). When a learner asks about a word or later shows changed ability, read [concept-progress.md](references/concept-progress.md), reuse the concept ID, and record meaning, reading and use evidence separately. A fluent read-aloud is a positive reading milestone, not proof of independent use.

用户问过的词义、得到的帮助以及后续表现，按同一知识点连续记录。理解、朗读和自主运用分开观察；有实际音频才能判断顺畅朗读。不打断自然对话做登记，课后由 Agent 写入精选证据。

## Stable preferences / 稳定偏好

`profile.json` stores the goal, practice language, correction style and drill preference with user-decision sources. Latest explicit preference wins over older session-specific scaffolding. Update via `set-preferences`; do not ask again about an already adopted preference. One utterance or one temporary need is not a lasting change.

`profile.json` 保存目标与偏好及其决定来源。最近明确偏好优先于旧课次里的临时辅助方式；Agent 用 `set-preferences` 保存，不反复要求用户重选。

## Save and resume reliably / 保存与续接

Read [data-schema.md](references/data-schema.md) before saving or changing records. Read [record-recovery.md](references/record-recovery.md) when a Voice tail arrives, practice is interrupted, pending data exists, or importing a missed session.

- Reuse one stable session ID throughout the conversation and any end-signal retries. A pause followed by immediate continuation belongs to that session until committed. Pick the next available daily sequence from both `Sessions` and `Pending`.
- When observable session end evidence arrives (user says stop, or the host explicitly labels a final transcript tail), Agent selects up to 3–6 useful examples, saves with `add-session`, and checks `validate`. Zero new expressions is valid; do not manufacture a quota.
- A final tail is a persistence opportunity, not just a greeting to acknowledge. Deduplicate cumulative transcript segments. Save only language-learning evidence, never incidental private or background conversation. Use partial-evidence notes when transcription is incomplete.
- For a long session, checkpoint selected evidence when tools are available, with `end_status: in_progress`. On resumption inspect the pending record. An unfinished checkpoint must not be automatically declared ended.
- After a successful write and `validate`, run `open_library.py --session <saved-id> --no-browser` and open its verified URL in the host browser. Then briefly say what was saved and the next thread to pick up. If saving failed, say so and keep the pending file. Never claim a save from an intention alone.
- The optional companion can observe a bound Voice log and drain translations after its close event; it does not save authoritative lesson/mastery records. Agent closeout still requires observable end evidence and tool execution. No permanent host hook or cross-device synchronization is installed. If the host provides no final callback, the next tool-enabled turn can recover only existing evidence.

同一课次及结束重试复用 ID。观察到结束信号后，Agent 写入精选证据、校验并刷新；允许零新增表达。长课次可先存未完成检查点；未结束内容不能自动宣称完成。正式档案只保留学习所需片段。启用伴随时，Agent 同时请求该绑定排空尾段并核实结束；伴随缓存不会自动变成正式学习证据，也没有永久宿主回调或跨设备同步。

## Local workspace and tools / 本地目录与命令

The webpage is bundled at `assets/library/`; its server and opener are in `scripts/`. Learning facts never belong in these program assets. Resolve one learning root with `workspace_config.py`: explicit root → saved machine configuration → `<skill>/data` for a new user. Read [storage-and-library.md](references/storage-and-library.md) before first setup, moving storage, updating the skill or opening the archive. Follow any rules governing the selected knowledge base before writes. Pass required note metadata explicitly through `record_metadata`; do not impose one knowledge base's statuses or project taxonomy on other learners.

网页框架随 Skill 安装。新用户默认数据目录是 `<skill>/data`；已有用户继续使用已配置的知识库或 Obsidian 文件夹，不迁回默认位置。Agent 负责初始化、路径校验、迁移和打开页面。`data` 是用户私人档案，禁止随 Skill 打包、上传或清理；默认目录写入后会在 Skill 外保存可恢复副本，升级前仍需核对备份。

Agent executes these internally using the installed skill's absolute script path; users only provide the practice request or their intended changes.

```sh
python3 <skill>/scripts/practice_store.py paths
python3 <skill>/scripts/practice_store.py resume
python3 <skill>/scripts/practice_store.py init
python3 <skill>/scripts/practice_store.py add-session --input <session.json>
python3 <skill>/scripts/practice_store.py checkpoint --input <session.json>
python3 <skill>/scripts/practice_store.py recover
python3 <skill>/scripts/practice_store.py set-preferences --input <preferences.json>
python3 <skill>/scripts/practice_store.py validate
python3 <skill>/scripts/practice_store.py rebuild
python3 <skill>/scripts/practice_store.py export --output <delivery-directory>
python3 <skill>/scripts/open_library.py --no-browser
python3 <skill>/scripts/workspace_config.py show
```

`resume` and `validate` are read-only. `init` also migrates a v1 workspace; `render` is an alias of `rebuild`. New workspaces do not overwrite an existing project page: Agent creates the entry if absent. Markdown session facts plus the legacy archive and preference file rebuild `state.json`, `INDEX.md` and `dashboard.html`. Daily records can be read in Obsidian or as files; installing Obsidian is optional.

HTML is the local reading layer; the same skill-owned assets read the configured data across windows. Overview, conversations, flip cards, evidence-based progress and storage details are available without a public website. Use `open_library.py` with the existing local-service-manager when available; otherwise use the bundled macOS launchd fallback or configure the host's native service supervision before opening the loopback URL. No remote hosting or model call is needed to browse. An `open` command returning a URL is not proof the preview was shown: open and inspect it through the host UI.

保存成功并校验后，Agent 主动打开本次课次总结；只回顾时可直接打开档案，不必先练习。卡片翻面只改变显示，不写入掌握状态。网页没有替用户开始 Voice 的能力，也不安装后台录音或结束回调。

## Reading progress / 阅读进展

The reflection page is a bounded period overview, not an ever-growing timeline. It links to a searchable, paginated expression index and individual histories. Period summaries exclude later evidence; detail pages explicitly show the latest state, with month filters affecting only the history. First observations are not comparative improvements. See [archive-views.md](references/archive-views.md) when maintaining or explaining these views.

统计回顾保留少量摘要；全部词句与每个词句的历史分别分页。没有记录不表示没有学会。维护时用独立虚构数据验证长历史，不向真实档案插入演示记录。
