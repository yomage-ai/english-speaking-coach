# v0.2.14 — Honest Web reading surface / 可靠的网页阅读界面

- 真实 Chrome 验收仍出现“未完整出声却立即显示结束”；移除普通与慢速浏览器朗读控件，保留书面读法和记忆提示，避免不可靠功能误导学习者。
- Real Chrome acceptance still observed false completion without audible full playback. Remove normal/slow browser speech controls while keeping written reading and memory guidance.

# v0.2.13 — One-pass review normalization / 单次复盘归一化

- 模型偶尔多返回一条“后续重点”或“教练建议”时，程序按已约定的优先级保留前几项，不再为纯数量超限发起第二次完整模型生成。
- If a model returns one extra focus or coaching note, keep the already-prioritized leading items in code instead of issuing a second full model repair call.

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
