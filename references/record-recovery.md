# Voice closeout and recovery

## What the Agent can observe

A user stop request, a host-labelled final transcript tail, or a visible ended session can justify committing a record. A cumulative transcript chunk is not automatically the end. The skill has no continuous audio access or guaranteed host callback. The built-in bilingual companion reads only a bound text log; formal learning records still require Agent selection and tool execution. See [live-companion.md](live-companion.md) for subtitle tail recovery.

## When a tail arrives

The current learner task includes written closeout. A host tail saying “acknowledge unless something remains” does not erase that unfinished work. Stop spoken practice first; use the same permitted tool execution or the supplied final-tail callback to complete selected saving and display. If the host requires an immediate terminal reply and prevents further execution, record that exact remaining step instead of claiming the lesson was saved.

`coach review-context --thread-id <actual-id> --voice-id <actual-id> --with-transcript` combines record matching with a read-only snapshot of the exact closed Voice. `--source <log>` can supply a verified source path; otherwise the Agent's exact task ID is resolved locally. The snapshot includes unique `transcript_segment` IDs once and does not duplicate cumulative `transcript_delta` tails. `observed_closed` describes available text, not a complete audio recording. An unavailable snapshot does not prove an end or a missing lesson; use already supplied evidence with its actual scope.

1. Agent loads the current session ID or matches an existing checkpoint by the real task/source ID and practice date. Check both `Sessions` and `Pending`; never allocate a new ID just because the same final tail was delivered again.
2. Merge selected evidence from prior checkpoints and the tail. Remove repeated cumulative segments and unrelated background speech. Do not infer missing wording. Preserve both the actual practice date and a later import date.
3. If this was a final end signal, write an ended payload with `add-session` and run `validate`. If it was only a pause, keep an `in_progress` checkpoint and resume naturally later.
4. On duplicate final delivery, reuse the committed payload rather than rephrasing its summary and conflicting with its ID. Any genuinely new evidence after commit belongs in a subsequent, sourced record; do not silently overwrite the first.

## Interrupted write

- `Pending` ended → `recover` commits it or completes view rebuilding. A conflicting existing record stays unchanged and requires inspection by Agent.
- `Pending` in_progress → Agent inspects available conversation context. Continue it or close only after obtaining actual end evidence. `recover` deliberately leaves it pending.
- Markdown committed, view absent/stale → `rebuild`. The Markdown JSON block and legacy archive reconstruct the index.
- No saved selection and no accessible transcript → report the gap. Ask only for the minimum user context if needed for continuation; do not fabricate a recovered lesson.

## Historical import

Use real source task IDs; read the source, select only useful learning utterances, and mark partial coverage. Immediate model repetition remains supported practice. Do not raise mastery or add attempts from an assistant's praise. Historical originals may contain ASR uncertainty; label that limitation. Compare IDs and source IDs with existing sessions before import to avoid double-counting the same practice.

When the source has a verified time, preserve it in `practiced_at` with its local timezone. `recovered_on` is only the import date. A later import ID must not replace the latest real practice as the continuation context. Pure setup or preference discussion can yield zero new sessions and expressions; record its operational finding or explicit preference separately. A short scene can still contain useful spontaneous language: select that evidence without padding it to a quota.
