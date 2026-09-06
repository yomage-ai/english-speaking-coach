# Concept progress / 知识点成长记录

Track a meaning, not only a spelling. `work out = exercise` and `work out = solve` need separate concept IDs. A word, phrase or reusable pattern can be a concept; a full conversation sentence remains an expression card. Extract a concept only when the source supports a useful teaching point, not for every word.

追踪的是具体义项，不只是拼写。同一义项跨课次复用 `CON-...`；同一词的不同意思分开。用户问词义、需要提示、后来成功使用或再次卡住，都是可记录的变化。只精选有价值的证据，不给所有词逐个建档。

## What to observe / 分开观察什么

| Dimension | What counts / 判定依据 | What does not / 边界 |
| --- | --- | --- |
| `meaning` 理解词义 | Learner explains or interprets the meaning without a supplied answer / 无答案提示下理解或说明意思 | Receiving an explanation is `explained`, not verified understanding / 听过解释不等于验证理解 |
| `reading` 顺畅朗读 | Agent actually hears the learner produce the word or phrase clearly in audio / Agent 实际听到清楚、顺畅的发音 | Transcript alone, TTS, or seeing written text / 文字转写、AI 朗读和打开卡片都不算 |
| `use` 自主运用 | Learner uses the sense appropriately in an actual response with no language model supplied / 实际回应中无语言提示且用法合适 | Reading/repeating a shown sentence is `supported` / 照读或即时跟读只记有提示完成 |

Record each genuine observation even if it is not a promotion. Celebrate specific gains: “This time you used it without my sentence,” or “You read this phrase smoothly.” Do not claim an entire concept is permanently mastered from a fluent read-aloud. If only transcription is available, record meaning/use evidence and leave reading unassessed.

进步不必等到“全会了”才能肯定。具体说明本次少了什么帮助、完成了什么。后来又卡住时保留之前的里程碑，并注明需要重访；不把历史成功删除，也不继续显示已经稳定。

## Derived levels / 页面状态

- `encountered`: an actual encounter, question, explanation or other initial evidence.
- `supported`: completed with help; no latest independent-use success.
- `independent`: latest use observation succeeded without a language prompt.
- `stable`: independent-use successes on at least two different practice dates and in at least two meaningful contexts, with the latest use observation still successful.

这些是产品的可解释判定口径，不是经过验证的语言考试分数。一次会用、同一分钟重复多次、不同字符串描述的同一场景，都不能包装成跨日迁移成功。上下文由 Agent 如实描述。页面将“表达已较稳定”和理解、朗读的各自状态并列展示，不称为永久掌握或 CEFR 等级。

## Session payload / 随课次保存

Add optional `concept_observations` to the normal session payload. The date, session ID and actual source IDs come from that session. Each observation needs:

```json
{
  "id": "OBS-20260905-001-001",
  "concept_id": "CON-commute-travel-to-work",
  "term": "commute",
  "meaning": "通勤；往返上下班",
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

## Old records / 已完成的旧课次

Do not rewrite a completed session merely to add this structure. Agent may extract only source-supported evidence into `Evidence/EVD-YYYYMMDD-NNN.md` through:

```sh
python3 <skill>/scripts/practice_store.py add-evidence --input <evidence.json>
```

The input contains `id`, `session`, the original practice `date`, actual `source_ids`, `reason`, and `concept_observations`. A same-ID retry is idempotent; a conflict fails. The old session stays unchanged. If the original question, timing, assistance or audio was not saved, mark the limitation rather than reconstructing it from memory.

## Start and close / 开始与结束

Inspect explicit word-meaning questions as well as complete learner sentences. Useful vocabulary from the partner's speech can be saved with the learner's actual question as evidence; ASR uncertainty must remain explicit. No expression card is required for a concept to appear in the flashcard view. Predicted scene terms alone are not observations. Apply the shared word/expression collection guidance in [listening-and-vocabulary.md](listening-and-vocabulary.md); do not duplicate the same sense merely to fill both lists.

`resume` returns compact concept review candidates alongside expression candidates. They share one total budget of 1–2 natural reviews; do not double the review load. Match spontaneous later use to an existing sense ID. At an observed session end, save the new evidence with the session, run validation and open its summary. The archive shows the resulting concept timeline automatically.
