# Review without interrupting conversation

The primary outcome is that the learner can communicate an intended meaning. Revisit words and chunks in meaningful exchanges, rather than accumulating a vocabulary total.

| Observed state | Interpretation | Next useful evidence |
| --- | --- | --- |
| `not_tested` | Collected only | Try using it in a real question |
| `source_text` | Needed the full sentence | Try later with less support |
| `keywords` | Used keyword support | Try after a delay without words shown |
| `independent` | Answered without a prompt | Use on a different occasion |
| `transfer` | Used in a changed context | Revisit less often, with another purpose |

These are observations, not permanent badges or CEFR levels. Repeating a supplied answer does not prove independent retrieval. A natural spontaneous response may count when the source establishes no supplied answer. A delayed independent use is stronger evidence than immediate repetition; record timing and support in `note`.

Agent selects at most the saved `review_limit` of relevant due items. Default to 1–2. In the scene, let the situation create a natural chance to use them; with `after_scene`, do not supply a model or turn the reply into a drill. In review, explain, model or guide a focused attempt when useful, adapting support rather than requiring a fixed sequence. Respect the user's chosen topic and clear ending; unfinished review belongs in the page or a later requested session. See [practice-phases.md](practice-phases.md).

Suggested initial intervals: collected/full text → next session (around 1 day); keywords → around 3 days; independent → around 7 days; transfer → around 14 days. These are practical defaults, not a validated personalized algorithm. Failure brings the item closer; repeated success in the same minute does not lengthen it. A conversation may close without new scored attempts.

For requested weekly reflection, compare dated records: less support, clearer meaning, or use in another situation. Quote short selected examples with session links; distinguish observation from interpretation. Never infer improvement merely from more sessions, more words or streak length. Store only actual review evidence using the session format if the user practices; a generated summary is not a practice attempt.

## Coverage before priorities

Review the full available conversation, including English structure problems the partner understood but did not teach. Rank explicit help and meaning problems first, then recurring useful structures, forgotten learned language, and the learner’s everyday goals. Correct optional variants seldom need cards. This is Agent judgment, not a frequency-ranking algorithm.

Keep one entry per distinct need, linking multiple relevant source turns when the same pattern recurs. The page may highlight up to three priorities; keep the other valuable entries accessible. `review_limit` never truncates newly collected expressions. Normal Voice closeout queues the local worker with `review-begin`; the worker uses the contract and submits through `finish-review`. Manual fallback uses `review-begin --manual`. Omissions need brief reasons. A structural coverage pass cannot certify the quality of those reasons.

When a correct sentence is first proposed during review, record it as `not_tested`; do not claim it was repeated or independently used during the scene. Save insufficient coach follow-up in `coaching_notes`, not the learner error count.
