# Read in meaning groups

Give a learner a usable start, audible grouping and a small focus, without turning ordinary conversation into continuous pronunciation instruction. Read this reference when the learner asks how to say/read a full phrase, reports speech running together, or needs a written reading guide.

## Model useful speech

- Group by meaning and grammatical relationships, not fixed word counts or every printed line break. Keep small coherent phrases together. A short sentence may need no internal pause. Speaking pace, emphasis and intention allow more than one natural grouping.
- Stress a few words that carry the current message. Function words are often lighter in a neutral reading, but contrast can change this. Stress is not shouting. Don't demand an accent or infer actual pronunciation from ASR.
- Choose a context-appropriate contour; a question mark does not always mean rising pitch, and “or” does not always introduce a closed choice. Explain only the one cue currently helpful.
- On explicit reading help, model one or two meaning groups at a comfortable pace. Optional practice can build a troublesome phrase, then reconnect it into the whole sentence; no mandatory repetition gate. After a response, continue the life situation. Don't add a long explanation and a second assignment to the same spoken turn.
- Written slashes, bold words and arrows are teaching annotations. They are not SSML, timing controls or instructions injected into a separate native Voice model. Never read the marks aloud or claim precise playback control without supported, verified tools.

For example, a learner asking about a shop item may use “Could you tell me / when this will be available?” A light boundary can separate the request from its detail. Memory can separately use “Could you tell me” and “when + clause”; a memory boundary is not a required spoken pause. Coach questions must remain open and must not append candidate answers. Explain reading cues in English only.

## Save one reusable guide

When saving the normal review, include `reading_guide` for expressions where grouping or starting help is useful, particularly an explicit reading request or a difficult priority expression. Don't annotate every short familiar reply or add a separate model call per sentence. These annotations are part of the existing draft: browsing and expanding them reads saved data only.

Each guide contains `kind: suggestion`, `groups` (each `text` and a list of `stress` words), `tone` (`rise`, `fall`, `level`, `fall-rise` or `context`), a concise `tone_note`, and `memory` (each reusable `text` and its `meaning`). Group texts must preserve all the expression's words in order; punctuation may stay in the clean original. Keep explanations in the user's written-review language. The complete format is also returned by `review-begin --manual`.

## Basis

- [Iowa State University: Thought Groups](https://iastate.pressbooks.pub/oralcommunication/chapter/overview-4/) — coherent meaning/grammar groups and flexible boundaries.
- [Cambridge: Intonation](https://dictionary.cambridge.org/grammar/british-grammar/intonation) — rising, falling and fall-rise patterns vary with use.

These principles guide a contextual example; neither source certifies a generated guide or the learner's speech.

## Conservative short-question default

The review worker keeps a short, single-clause question in one reading group, leaving memory patterns separate. This is a product default for accessibility, not a word-count rule for all speech. A neutral wh-question may use a fall; confirming, checking and surprise can change its tune. Do not teach that all questions rise, and do not break “How much is” away from its complement just to create visible chunks.

Background: [Cambridge: intonation](https://dictionary.cambridge.org/grammar/british-grammar/intonation) describes common wh/yes-no patterns and variation; [British Council: chunks](https://www.teachingenglish.org.uk/professional-development/teachers/teaching-knowledge-database/c/chunks) explains reusable lexical/grammatical groups. Neither says every memory chunk must be a breathing pause. The numeric threshold in the worker is our conservative UI default, not a linguistic law.
