# Voice closeout and recovery / 语音收尾与恢复

## What the Agent can observe / Agent 能观察到什么

A user stop request, a host-labelled final transcript tail, or a visible ended session can justify committing a record. A cumulative transcript chunk is not automatically the end. The skill has no continuous audio access or guaranteed host callback. The built-in bilingual companion reads only a bound text log; formal learning records still require Agent selection and tool execution. See [live-companion.md](live-companion.md) for subtitle tail recovery.

用户说结束、宿主明确标注最终转写尾段、可见的会话结束，才能支持课次收尾。累计转写片段不自动等于结束。双语伴随只监听绑定文字日志，不保证宿主每次提供回调；正式课次仍须 Agent 精选并执行保存。

## When a tail arrives / 收到尾段时

The current learner task includes written closeout. A host tail saying “acknowledge unless something remains” does not erase that unfinished work. Stop spoken practice first; use the same permitted tool execution or the supplied final-tail callback to complete selected saving and display. If the host requires an immediate terminal reply and prevents further execution, record that exact remaining step instead of claiming the lesson was saved.

`practice_store.py review-context --thread-id <actual-id> --voice-id <actual-id> --with-transcript` combines record matching with a read-only snapshot of the exact closed Voice. `--source <log>` can supply a verified source path; otherwise the Agent's exact task ID is resolved locally. The snapshot includes unique `transcript_segment` IDs once and does not duplicate cumulative `transcript_delta` tails. `observed_closed` describes available text, not a complete audio recording. An unavailable snapshot does not prove an end or a missing lesson; use already supplied evidence with its actual scope.

读取转写不启动翻译、不切换实时绑定，也不自动创建课次。已保存时复用课次；未保存时由 Agent 精选。程序只查证输入，不能替代真实学习判断。

1. Agent loads the current session ID or matches an existing checkpoint by the real task/source ID and practice date. Check both `Sessions` and `Pending`; never allocate a new ID just because the same final tail was delivered again.
2. Merge selected evidence from prior checkpoints and the tail. Remove repeated cumulative segments and unrelated background speech. Do not infer missing wording. Preserve both the actual practice date and a later import date.
3. If this was a final end signal, write an ended payload with `add-session` and run `validate`. If it was only a pause, keep an `in_progress` checkpoint and resume naturally later.
4. On duplicate final delivery, reuse the committed payload rather than rephrasing its summary and conflicting with its ID. Any genuinely new evidence after commit belongs in a subsequent, sourced record; do not silently overwrite the first.

## Interrupted write / 写入中断

- `Pending` ended → `recover` commits it or completes view rebuilding. A conflicting existing record stays unchanged and requires inspection by Agent.
- `Pending` in_progress → Agent inspects available conversation context. Continue it or close only after obtaining actual end evidence. `recover` deliberately leaves it pending.
- Markdown committed, view absent/stale → `rebuild`. The Markdown JSON block and legacy archive reconstruct the index.
- No saved selection and no accessible transcript → report the gap. Ask only for the minimum user context if needed for continuation; do not fabricate a recovered lesson.

Agent 应尽可能从已有文件与可访问对话恢复，不要求用户维护文件。没有证据就承认缺口；不能将“可以恢复”说成“任何语音都必然自动保存”。

## Historical import / 历史补录

Use real source task IDs; read the source, select only useful learning utterances, and mark partial coverage. Immediate model repetition remains supported practice. Do not raise mastery or add attempts from an assistant's praise. Historical originals may contain ASR uncertainty; label that limitation. Compare IDs and source IDs with existing sessions before import to avoid double-counting the same practice.

When the source has a verified time, preserve it in `practiced_at` with its local timezone. `recovered_on` is only the import date. A later import ID must not replace the latest real practice as the continuation context. Pure setup or preference discussion can yield zero new sessions and expressions; record its operational finding or explicit preference separately. A short scene can still contain useful spontaneous language: select that evidence without padding it to a quota.

有可核对时间时保存 `practiced_at`；补录日期不当作练习时间。先对真实来源去重，晚补的旧场不能挤掉较新练习。纯环境设置/偏好讨论允许零新课次，语言证据与产品问题分开沉淀。
