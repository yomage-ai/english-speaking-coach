# Read in meaning groups / 按意思念，按结构记

Give a learner a usable start, audible grouping and a small focus, without turning ordinary conversation into continuous pronunciation instruction. Read this reference when the learner asks how to say/read a full phrase, reports speech running together, or needs a written reading guide.

普通交流按意思自然分段、保留轻重和语调；不逐词断开，不强制每句讲发音。用户问怎么念、听不清或难以组织新表达时，才给一小段清楚示范，并让出回应空间。

## Model useful speech / 示范可用的读法

- Group by meaning and grammatical relationships, not fixed word counts or every printed line break. Keep small coherent phrases together. A short sentence may need no internal pause. Speaking pace, emphasis and intention allow more than one natural grouping.
- Stress a few words that carry the current message. Function words are often lighter in a neutral reading, but contrast can change this. Stress is not shouting. Don't demand an accent or infer actual pronunciation from ASR.
- Choose a context-appropriate contour; a question mark does not always mean rising pitch, and “or” does not always introduce a closed choice. Explain only the one cue currently helpful.
- On explicit reading help, model one or two meaning groups at a comfortable pace. Optional practice can build a troublesome phrase, then reconnect it into the whole sentence; no mandatory repetition gate. After a response, continue the life situation. Don't add a long explanation and a second assignment to the same spoken turn.
- Written slashes, bold words and arrows are teaching annotations. They are not SSML, timing controls or instructions injected into a separate native Voice model. Never read the marks aloud or claim precise playback control without supported, verified tools.

句子可先按“主要意思＋补充信息”听；记忆则可以按“起句＋可替换内容＋可选补充”组织。这两个划分不必一样。斜杠代表可轻停，不是必须吸气或交还话轮；网页换行不代表停顿。用户明确要求中文讲解时再用中文解释，普通角色交流保持其语言偏好。

For example, a shop question may have a light boundary after the requested item, followed by examples: “Do you have any other colors / like blue or green?” This asks whether more colors are available; the examples do not automatically turn it into a blue-versus-green choice. A gentle final rise is one possible reading. Memory can separately use “Do you have…?”, “any other + plural item”, and “like A or B”. Do not impose a pause after “have” merely because it is a useful memory boundary.

## Save one reusable guide / 保存可反复查看的提示

When saving the normal review, include `reading_guide` for expressions where grouping or starting help is useful, particularly an explicit reading request or a difficult priority expression. Don't annotate every short familiar reply or add a separate model call per sentence. These annotations are part of the existing draft: browsing and expanding them reads saved data only.

Each guide contains `kind: suggestion`, `groups` (each `text` and a list of `stress` words), `tone` (`rise`, `fall`, `level`, `fall-rise` or `context`), a concise `tone_note`, and `memory` (each reusable `text` and its `meaning`). Group texts must preserve all the expression's words in order; punctuation may stay in the clean original. Keep explanations in the user's written-review language. The complete format is also returned by `review-begin --manual`.

读法提示与学习表现分别保存。新增参考读法不改变原话、课次日期、提示依赖或掌握状态。旧课次可以没有标注；后补时明确这是新的学习辅助，不能伪装成当时说过或音频中测量到的节奏。

## Basis / 依据

- [Iowa State University: Thought Groups](https://iastate.pressbooks.pub/oralcommunication/chapter/overview-4/) — coherent meaning/grammar groups and flexible boundaries.
- [Cambridge: Intonation](https://dictionary.cambridge.org/grammar/british-grammar/intonation) — rising, falling and fall-rise patterns vary with use.

These principles guide a contextual example; neither source certifies a generated guide or the learner's speech. 资料支持教学原则，不证明生成结果、真实语音或学习成效。

## Conservative short-question default / 简短问句的保守默认

The review worker keeps a short, single-clause question in one reading group, leaving memory patterns separate. This is a product default for accessibility, not a word-count rule for all speech. A neutral wh-question may use a fall; confirming, checking and surprise can change its tune. Do not teach that all questions rise, and do not break “How much is” away from its complement just to create visible chunks.

Background: [Cambridge: intonation](https://dictionary.cambridge.org/grammar/british-grammar/intonation) describes common wh/yes-no patterns and variation; [British Council: chunks](https://www.teachingenglish.org.uk/professional-development/teachers/teaching-knowledge-database/c/chunks) explains reusable lexical/grammatical groups. Neither says every memory chunk must be a breathing pause. The numeric threshold in the worker is our conservative UI default, not a linguistic law.
