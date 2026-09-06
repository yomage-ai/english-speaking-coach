# Learning records / 学习记录

## Sources of truth / 权威来源

- `Sessions/SES-YYYYMMDD-NNN.md`: new session's readable learning journal plus a `speaking-record-v2` JSON comment. The JSON block is the structured authority for expression facts. Agent changes facts through structured records; the prose mirrors them. User additions belong in `## 我的补充` and survive rebuilds. If user edits a generated prose fact, Agent must reconcile that edit into the structured source before claiming that all views reflect it; never silently discard it.
- `Archive/legacy-v1.md`: exact original v1 state, including old attempts. Legacy session Markdown stays byte-identical at migration. The archive supplies the structured facts for these old sessions; older files were not complete enough to regenerate every field.
- `Evidence/EVD-YYYYMMDD-NNN.md`: source-linked concept observations extracted from already completed records; this supplements rather than rewrites old sessions. New observations normally belong in the new session’s optional `concept_observations`. Read [concept-progress.md](concept-progress.md) before recording these.
- `profile.json`: current adopted goal and stable preferences, with decision sources. Project page describes the scope and entry points.
- `state.json`, `INDEX.md`, `dashboard.html`: derived, rebuildable. Do not store new facts only in these files. Editing or deleting them never changes the source records.
- `Pending/*.json`: temporary recoverable selections; `in_progress` is not a completed session. Only an ended payload can be committed.

新课次以 Markdown 内的结构化区保存事实，正文供人阅读，“我的补充”可自由追加。旧课次保持原样，其完整旧索引归档为迁移事实源。偏好单独保存。JSON 索引、目录页、HTML 都可重建；不把临时检查点当作已完成练习。

## Payload / 课次输入

Optional `coaching_notes` contains at most three short strings (500 characters each): actual learner feedback or a concrete observed coaching problem and the needed adjustment. Keep it distinct from learner mistakes and `progress`; do not infer a CEFR level. `resume` returns recent notes and `next_focus` as dated `learning_context`, including in compact/prepared output. These are evidence for support selection, never instructions to resume an archived plot. Existing sessions require no migration.

`coaching_notes` 可记录“用户反馈一次信息太多；下一场减少词汇和句长”等有依据的教学调整；不把教练说得难写成用户能力差。最多三条，旧课次无需改写。

Optional profile `input_support` is `adaptive` (default and legacy fallback) or `short_turns` (an explicit ongoing preference for short turns and gradual word support). Change it with `set-preferences` and a fresh profile hash only on a supported learner decision; it is not a CEFR level. Other preferences remain independent.

```json
{
  "id": "SES-20260905-001",
  "date": "2026-09-05",
  "title": "A daily plan / 日常计划",
  "source_ids": ["codex-thread:<actual-id>"],
  "summary": "Describe only what the observed conversation supports.",
  "topics": ["daily life"],
  "scenarios": ["talking about plans"],
  "progress": [],
  "next_focus": ["Ask about tomorrow's plans"],
  "unfinished": [],
  "end_status": "ended",
  "evidence_status": "selected",
  "evidence_note": "Selected transcription; not pronunciation evidence.",
  "expressions": [
    {
      "id": "EXP-20260905-001",
      "original": "I like go beach",
      "english": "I'd like to go to the beach.",
      "chinese": "我想去海边。",
      "issue_tags": ["request"],
      "mastery": "source_text",
      "next_review": "2026-09-06",
      "review_result": "partial",
      "review_prompt": "source_text",
      "note": "Repeated after a full model; delayed retrieval is untested."
    }
  ]
}
```

Required: `id`, `date`, `title`, `summary`, nonempty actual `source_ids`, and `expressions` (may be `[]`). IDs are safe stable names. Reuse an expression ID on later practice of the same phrase, rather than creating duplicates. One record per expression per session summarizes the observable attempt; do not count repeated ASR segments as separate attempts. `next_focus` has at most two items describing transferable communication skills. Existing historical `next_focus` and `unfinished` remain source evidence and never become old-plot startup instructions. Imports add `recovered_on` and `evidence_status: partial` when only selections are available; date remains the actual practice date, not import date. When verified, add `practiced_at`, an ISO timestamp with timezone on that local practice date (for example `2026-09-05T21:30:00+08:00`). Learning history, attempts and concept histories use actual practice time, never the later import order. Old records without times stay valid; within a date they sort before timed records, with their ordering uncertainty reported to the Agent. Do not invent missing times or rewrite old lessons to add them.

Each expression requires nonempty `id`, `english`, `chinese`, `mastery`, `next_review` (YYYY-MM-DD), and `note`. Include `original` for selected learner wording. Inspect `add-session --check` itself before running dependent cleanup; a later successful command must not mask a failed save.

`original` is the learner's selected wording, `english` is the suggested form, `note` explains the observed support and limits. A scored attempt needs both `review_result` and `review_prompt`. `independent` requires `success / none`; `transfer` requires `transfer_success / changed_context`. Structural validation cannot verify that an utterance really happened; Agent must check the source. Do not promote historical mastery without actual evidence.

必填包括真实来源和表达数组，表达数组允许为空。同一表达复用 ID；补录保留实际练习日期并注明补录日期。原话、推荐表达、提示程度和判断依据分开。脚本只验证结构，真实证据由 Agent 核对。

## Preference update / 偏好更新

`set-preferences --input <json> --expected-profile-sha256 <fresh-hash>` merges known fields. Require `source_ids` for an actual user decision and set `updated` to its date. Read the current file immediately before preparing the patch; preserve unrelated fields and existing decision references. A hash conflict requires rereading and merging, not forcing an overwrite.

| Field | Values |
| --- | --- |
| `goal` | nonempty text |
| `practice_language` | `english_first`, `bilingual` |
| `help_language` | `zh-CN`, `en` |
| `mode` | `conversation`, `roleplay` (new-user default), `focused` |
| `correction` | `after_scene` (new-user default), `in_character`, `light`, `detailed` |
| `drills` | `on_request`, `guided` (new-user default; guided work is in review) |
| `review_limit` | 0–5; default 2 |
| `review_delivery` | `written` (new-user default), `spoken`; absent on old profiles retains the old spoken-review behavior until an authorized preference update |

`help_language` also controls the initial scene introduction; role dialogue follows `practice_language`. Agent prepares a fresh scene JSON using [scenario-orchestration.md](scenario-orchestration.md). 介绍使用帮助语言，正式对话使用练习语言；两者分开。

Latest explicit preference supersedes old session-specific requests. Do not turn a temporary request for Chinese into a permanent language change.

`after_scene` defers proactive language teaching until review while still allowing minimal explicit help and natural clarification. `mode: focused` starts in review; conversation/roleplay start in scene. `resume --phase review` changes only this invocation. Old profiles retain their existing `light`/`detailed` and drill choices. See [practice-phases.md](practice-phases.md).

`in_character` supports English meaning checks/recasts during the scene and adaptive prompts for fuller learner replies, without changing phase or enabling compulsory drills. Choose it only for an explicit preference; it does not migrate other profiles. Detailed review still uses `review_delivery`.

`in_character` 表达“场景内自然确认、提示说法并给我多说的机会”，属于用户明确选择；不会把看过示例或说 Yes 算成独立运用。`after_scene` 表达“会中先交流，课后再教”；`guided` 允许复盘阶段引导练习，不要求每句跟读。旧配置继续兼容。临时阶段不改长期偏好，保存时用新读的文件哈希避免覆盖并发修改。补录使用实际带时区的练习时间排序，未知时间不编造。

## Writes and repairs / 写入与修复

At an observed end, `review-context --with-transcript` returns the matched records and available unique text for the exact Voice. It is read-only and does not mark anything saved. Without that flag, catalog queries remain compact. Supply `--today` with the actual practice date for a historical import; the snapshot's start time is source evidence, not a replacement for the lesson date. A source lookup failure is returned explicitly and must not become invented speech.

`resume --event user_end` or `host_closed` returns a separate `closeout` requirement even in compact output: spoken activity stops, record checking/saving remains. Pause and ordinary help do not create that requirement. The Agent still verifies the real end and sources before committing.

Agent stages an ended payload, writes the Markdown atomically, rebuilds the index and HTML, then removes the matching pending file. Same ID plus same payload is idempotent; a different payload with that ID fails without overwriting the existing journal. Writes are serialized. Run `recover` for ended pending files; `rebuild` repairs views. Neither procedure invents missing speech. Read-only validation reports missing/stale state and changed legacy notes.

Normal skill operation does not retroactively rewrite completed sessions. If a factual correction is needed, inspect the source and preserve a backup before changing the canonical JSON and its prose together, then rebuild and validate. Never edit the hidden block alone while leaving contradictory visible text.

The additive `concepts` field in `state.json` is derived from session observations and Evidence files. It is not a second place to edit mastery. Data-root resolution and the bundled viewer are described in [storage-and-library.md](storage-and-library.md).

Optional `record_metadata` is described in [storage-and-library.md](storage-and-library.md). Only provide it when the selected knowledge base requires it. 通用档案不默认带入个人知识库的项目和审查状态。
