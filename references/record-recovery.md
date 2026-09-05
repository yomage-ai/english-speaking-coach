# Voice closeout and recovery / 语音收尾与恢复

## What the Agent can observe / Agent 能观察到什么

A user stop request, a host-labelled final transcript tail, or a visible ended session can justify committing a record. A cumulative transcript chunk is not automatically the end. The skill has no continuous audio access, background listener or guaranteed host callback. Tool invocation is still needed to persist anything.

用户说结束、宿主明确标注最终转写尾段、可见的会话结束，才能支持课次收尾。累计转写片段不自动等于结束。Skill 没有后台监听，也不保证宿主每次提供回调；必须有实际工具执行才会保存。

## When a tail arrives / 收到尾段时

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
