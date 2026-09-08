# Learning records

## Sources of truth

- `Sessions/SES-YYYYMMDD-NNN.md`: new session's readable learning journal plus a `speaking-record-v2` JSON comment. The JSON block is the structured authority for expression facts. Agent changes facts through structured records; the prose mirrors them. User additions belong in the existing personal-additions section and survive rebuilds. If user edits a generated prose fact, Agent must reconcile that edit into the structured source before claiming that all views reflect it; never silently discard it.
- `Archive/legacy-v1.md`: exact original v1 state, including old attempts. Legacy session Markdown stays byte-identical at migration. The archive supplies the structured facts for these old sessions; older files were not complete enough to regenerate every field.
- `Evidence/EVD-YYYYMMDD-NNN.md`: source-linked concept observations extracted from already completed records; this supplements rather than rewrites old sessions. New observations normally belong in the new session’s optional `concept_observations`. Read [concept-progress.md](concept-progress.md) before recording these.
- `profile.json`: current adopted goal and stable preferences, with decision sources. Project page describes the scope and entry points.
- `state.json`, `INDEX.md`, `dashboard.html`: derived, rebuildable. Do not store new facts only in these files. Editing or deleting them never changes the source records.
- `Pending/*.json`: temporary recoverable selections; `in_progress` is not a completed session. Only an ended payload can be committed.

## Payload

Optional `coaching_notes` contains at most three short strings (500 characters each): actual learner feedback or a concrete observed coaching problem and the needed adjustment. Keep it distinct from learner mistakes and `progress`; do not infer a CEFR level. `resume` returns recent notes and `next_focus` as dated `learning_context`, including in compact/prepared output. These are evidence for support selection, never instructions to resume an archived plot. Existing sessions require no migration.

Optional profile `input_support` is `adaptive` (default and legacy fallback) or `short_turns` (an explicit ongoing preference for short turns and gradual word support). Change it with `set-preferences` and a fresh profile hash only on a supported learner decision; it is not a CEFR level. Other preferences remain independent.

```json
{
  "id": "SES-20260905-001",
  "date": "2026-09-05",
  "title": "A daily plan",
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
      "chinese": "A request to visit the beach.",
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

Optional `source_quotes: [{quote, source_turn_ids}]` preserves the exact linked need and later attempt when duplicate canonical expressions are coalesced. Each quote is checked against this Voice before saving; it does not create extra attempts or promote mastery.

`original` is the learner's selected wording, `english` is the suggested form, `note` explains the observed support and limits. A scored attempt needs both `review_result` and `review_prompt`. `independent` requires `success / none`; `transfer` requires `transfer_success / changed_context`. Structural validation cannot verify that an utterance really happened; Agent must check the source. Do not promote historical mastery without actual evidence.

## Preference update

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

Legacy language fields remain readable for archive compatibility. They do not override the mandatory English-only practice rule. Agent prepares an English scene JSON using [scenario-orchestration.md](scenario-orchestration.md).

Latest explicit preference supersedes old session-specific requests. Do not turn a temporary request for Chinese into a permanent language change.

`after_scene` defers proactive language teaching until review while still allowing minimal explicit help and natural clarification. `mode: focused` starts in review; conversation/roleplay start in scene. `resume --phase review` changes only this invocation. Old profiles retain their existing `light`/`detailed` and drill choices. See [practice-phases.md](practice-phases.md).

`in_character` supports English meaning checks/recasts during the scene and adaptive prompts for fuller learner replies, without changing phase or enabling compulsory drills. Choose it only for an explicit preference; it does not migrate other profiles. Detailed review still uses `review_delivery`.

## Writes and repairs

At an observed end, `review-context --with-transcript` returns the matched records and available unique text for the exact Voice. It is read-only and does not mark anything saved. Without that flag, catalog queries remain compact. Supply `--today` with the actual practice date for a historical import; the snapshot's start time is source evidence, not a replacement for the lesson date. A source lookup failure is returned explicitly and must not become invented speech.

`resume --event user_end` or `host_closed` returns a separate `closeout` requirement even in compact output: spoken activity stops, record checking/saving remains. Pause and ordinary help do not create that requirement. The Agent still verifies the real end and sources before committing.

Agent stages an ended payload, writes the Markdown atomically, rebuilds the index and HTML, then removes the matching pending file. Same ID plus same payload is idempotent; a different payload with that ID fails without overwriting the existing journal. Writes are serialized. Run `recover` for ended pending files; `rebuild` repairs views. Neither procedure invents missing speech. Read-only validation reports missing/stale state and changed legacy notes.

Normal skill operation does not retroactively rewrite completed sessions. If a factual correction is needed, inspect the source and preserve a backup before changing the canonical JSON and its prose together, then rebuild and validate. Never edit the hidden block alone while leaving contradictory visible text.

The additive `concepts` field in `state.json` is derived from session observations and Evidence files. It is not a second place to edit mastery. Data-root resolution and the bundled viewer are described in [storage-and-library.md](storage-and-library.md).

Optional `record_metadata` is described in [storage-and-library.md](storage-and-library.md). Only provide it when the selected knowledge base requires it.

## Normal Voice closeout

Normal closeout queues the local worker with `review-begin --thread-id … --voice-id …`. For verified manual fallback only, use `review-begin --manual --thread-id … --voice-id … --with-transcript`, then `finish-review --thread-id … --voice-id … --input draft.json`. The returned `finish_contract` is the complete compact draft contract. Do not hand-assign IDs or copy canonical concept values during normal closeout. `finish-review` verifies the closed source, checks that every available learner turn was selected or explicitly omitted, allocates IDs under the writer lock, preserves exact selected quotes, and validates the committed record. Existing saved records win on repeated callbacks; matching ended pending records recover. An in-progress pending selection still requires explicit reconciliation.

A draft expression requires `source_turn_ids`, `original`, `english`, `chinese`, `note`; `expression_ref` may replace the canonical English/Chinese. Concept observations reference `concept_id` without term/meaning for existing senses; new senses provide term/meaning without an ID. `expression_indices` optionally refers to zero-based draft expressions. Code supplies observation IDs, modality, quote kind and scene context. Evidence classification remains an Agent judgment.

`omitted_turns` maps other learner segment IDs to brief reasons, such as greeting, correct response, self-repair or coaching feedback. This is accounting, not a guarantee that a model chose well. It stores no full transcript. `priority_indices` selects up to three expression positions; all expressions are retained. Canonical optional `review_priority_ids` links these page highlights; `review_coverage` records available/selected counts and reasons. Legacy records need no migration. Source-unavailable recovery continues to use the explicit partial `add-session` contract with accurate evidence limits.

## Optional reading guide

An expression may have `reading_guide` with exactly five fields: `kind: suggestion`, `groups: [{text, stress: [word]}]`, `tone` (`rise`, `fall`, `level`, `fall-rise`, `context`), `tone_note` and `memory: [{text, meaning}]`. See [reading-and-chunks.md](reading-and-chunks.md) for teaching decisions. The normal finish contract includes this shape; no separate generation round is needed. Validation preserves the clean English word order and requires stress words to occur in their group. One to six groups and one to four memory parts keep the annotation readable. Legacy records can omit it.
