# Concept progress

Track a meaning, not only a spelling. `work out = exercise` and `work out = solve` need separate concept IDs. A word, phrase or reusable pattern can be a concept; a full conversation sentence remains an expression card. Extract a concept only when the source supports a useful teaching point, not for every word.

## What to observe

| Dimension | What counts | What does not |
| --- | --- | --- |
| `meaning` | Learner explains or interprets the meaning without a supplied answer | Receiving an explanation is `explained`, not verified understanding |
| `reading` | Agent actually hears the learner produce the word or phrase clearly in audio | Transcript alone, TTS, or seeing written text |
| `use` | Learner uses the sense appropriately in an actual response with no language model supplied | Reading/repeating a shown sentence is `supported` |

Record each genuine observation even if it is not a promotion. Celebrate specific gains: “This time you used it without my sentence,” or “You read this phrase smoothly.” Do not claim an entire concept is permanently mastered from a fluent read-aloud. If only transcription is available, record meaning/use evidence and leave reading unassessed.

## Derived levels

- `encountered`: an actual encounter, question, explanation or other initial evidence.
- `supported`: completed with help; no latest independent-use success.
- `independent`: latest use observation succeeded without a language prompt.
- `stable`: independent-use successes on at least two different practice dates and in at least two meaningful contexts, with the latest use observation still successful.

These are explainable product criteria, not validated language-exam scores. Repetition within one minute and renamed versions of the same scene do not prove transfer across dates or contexts. Report meaning, reading and use separately; do not claim permanent mastery or a CEFR level. If a later attempt needs help, retain earlier milestones while marking the need to revisit.

## Session payload

Add optional `concept_observations` to the normal session payload. The date, session ID and actual source IDs come from that session. Each observation needs:

```json
{
  "id": "OBS-20260905-001-001",
  "concept_id": "CON-commute-travel-to-work",
  "term": "commute",
  "meaning": "Travel regularly between home and work",
  "dimension": "use",
  "result": "supported",
  "support": "model",
  "modality": "transcript",
  "context": "describing the journey to work",
  "quote_kind": "utterance",
  "quote": "The actual learner wording from the source goes here.",
  "note": "Explain the observed support and the limits of this evidence.",
  "expression_ids": []
}
```

This example illustrates the schema, not a practice record to import. Replace its facts with actual evidence. `result`: `needs_help | explained | supported | success`; `support`: `model | keywords | none`; `modality`: `text | transcript | audio`; `quote_kind`: `utterance | session_note`. Use increasing, padded observation IDs within a session. Repeated source tails must not become new observations.

`quote_kind=session_note` explicitly identifies an existing summary rather than a verbatim learner utterance; it cannot support a newly scored success. Actual audio is required for reading success. Independent meaning/use success requires `support=none`. Structural checks do not prove that an event happened: Agent verifies the source before saving.

## Old records

Do not rewrite a completed session merely to add this structure. Agent may extract only source-supported evidence into `Evidence/EVD-YYYYMMDD-NNN.md` through:

```sh
<skill>/scripts/coach add-evidence --input <evidence.json>
```

The input contains `id`, `session`, the original practice `date`, actual `source_ids`, `reason`, and `concept_observations`. A same-ID retry is idempotent; a conflict fails. The old session stays unchanged. If the original question, timing, assistance or audio was not saved, mark the limitation rather than reconstructing it from memory.

## Start and close

Inspect explicit word-meaning questions as well as complete learner sentences. Useful vocabulary from the partner's speech can be saved with the learner's actual question as evidence; ASR uncertainty must remain explicit. No expression card is required for a concept to appear in the flashcard view. Predicted scene terms alone are not observations. Apply the shared word/expression collection guidance in [listening-and-vocabulary.md](listening-and-vocabulary.md); do not duplicate the same sense merely to fill both lists.

`resume` returns compact concept review candidates alongside expression candidates. They share one total budget of 1–2 natural reviews; do not double the review load. Match spontaneous later use to an existing sense ID. At an observed session end, save the new evidence with the session, run validation and open its summary. The archive shows the resulting concept timeline automatically.
