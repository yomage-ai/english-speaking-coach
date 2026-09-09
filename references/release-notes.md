# v0.2.12 — Reliable review and reading / 稳定复盘与朗读

- 复盘模型只生成需要语义判断的内容；程序补齐并校验逐回合覆盖和词义记账，显著缩短长对话复盘，保留来源与完整性检查。
- 修复网页慢速朗读的取消竞态和长句中断，改用短句队列并优先选择可靠的本地英语声音。
- 带省略号、占位符或混合语言的句型模板不再硬送给系统朗读，避免产生像坏语法一样的残缺语音。
- Voice 开场不再等待截图、字幕或翻译；禁止用 “let me think/check/sort” 之类等待话术冒充教学内容。

- Generate semantic review judgments only; derive and validate exhaustive turn/word bookkeeping in code, substantially reducing long-review latency without dropping provenance checks.
- Fix slow-playback cancellation races and long utterance cutoffs with a bounded sentence queue and preferred reliable local English voices.
- Do not send ellipsis, placeholder or mixed-language pattern cards to system speech as broken utterances.
- Start Voice without waiting for screenshots, captions or translations, and never use holding phrases as teaching content.

Native Voice may still respond autonomously, emit holding phrases or paraphrase before the delegated Agent returns. Skill instructions cannot fully control that host layer; verify actual Voice separately.
原生 Voice 仍可能在 Agent 返回前自主回应、说等待话术或改述；Skill 指令无法完全控制宿主语音层，真实 Voice 仍需单独验收。
