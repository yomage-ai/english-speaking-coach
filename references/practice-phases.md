# Practice decisions

This reference explains the turn cycle in `SKILL.md`. It is for the Agent responding to the learner; it is not text to forward as instructions to a different model. Voice delivery follows [voice-delivery.md](voice-delivery.md).

## Mode, phase and support

`mode` selects roleplay, conversation or focused review. `phase` says whether this turn belongs to the scene or review. Help within a scene does not itself change phase. `resolve_phase` and `transition` in the program report these distinctions; they do not operate the microphone or prove what the host said.

| Saved correction | During the scene |
| --- | --- |
| `in_character` | For non-English content, give one English restatement and confirmation. For missing English or useful unresolved English structure errors, give one usable phrase even if intent is clear. Wait for explicit help or ongoing formulation; a completed turn may receive a short repair plus role response and one next cue. |
| `after_scene` (new-user default) | Respond to understandable content; clarify real ambiguity and answer explicit help requests briefly. Leave proactive wording repair for review. |
| `light` | Brief selective recasts according to the saved preference, without compulsory drills. |
| `detailed` | Give the detail the learner explicitly chose while preserving the conversation; do not silently replace this with another mode. |

`drills: guided` permits useful targeted work in requested review, not mandatory repetition during every scene. `review_delivery: written` leaves the review on the page. `spoken` permits spoken review when the user is still practicing; an explicit end always wins. Old profiles retain their explicit settings.

## Identify help and feedback before role content

An English-only “how do I say…?” already requests help. Give one useful phrase or short model and wait, without an extra meaning check or a new content question. For any non-English or mixed input, restate its meaning in English and check it once before proceeding, as required in `SKILL.md`. For a missing word, a full sentence is optional; do not turn its ordinary hesitant use into another take. Use English for every explanation, including requests for help in another language. Do not quote non-English wording in the reply.

Learner describes hiking using another language inside an unfinished English request.

Partner: “You mean, ‘I'd like to go hiking.’ Have I understood you correctly?”

Learner: “I'd like to go hiking with my friend.”

Partner: “What kind of trail are you looking for?”

If the learner instead says “Why do you keep asking me to repeat?”, address the coaching feedback itself. “You're right. Your meaning was clear already.” is enough. Do not require a corrected complaint, announce another drill or resume before the user indicates they want to continue. Keep the practice language through this repair, including when the complaint is Chinese. A request for another language receives a simpler English explanation, with no language exception. Confirm clear coaching controls by acknowledging the action in English and complying immediately.

## Preserve the whole interaction

For an in-character meaning check, the useful unit is **learner intent → natural English → learner reply → a relevant opportunity to express content**. Sending the model sentence alone completes only the support step. A sufficient short reply is accepted; the next opportunity comes from the situation, not a demand to repeat. Resolve a pending check before treating the next Chinese yes as a new meaning.

The following examples are fictional illustrations, not scripts to replay. Each partner line is one turn, followed by waiting.

### A non-English request

Learner says in another language that they are unsure and want a recommendation.

Partner: “Do you mean, ‘I'm not sure. What would you recommend?’”

Learner: “Yes.”

Partner: “What kind of food do you usually enjoy?”

Learner: “I like something light. I don't want too much food.”

Partner: “Our soup might suit you. What would you like to know about it?”

A confirmation resolves the meaning; the food preference supplies learner-owned content. If the learner asks what is in the soup, answer it. Do not withhold requested information just to force a predetermined exercise. If they already said what they like, respond to that detail instead of asking again.

### A stalled description

Learner starts an English request and describes light food with little oil in another language.

Partner: “Something light, without too much oil?”

Learner: “Yes, something light.”

Partner: “What would you like it to come with?”

If they stall again, use a neutral cue such as “Describe the food you want with it.” If they need wording, a small model such as “I'd like it with…” can help. Do not supply an ingredient or preference for them. Use only the amount of help needed; do not supply a complete preference and reason for them. First-person models help when the learner needs request wording; a natural second-person recast works when they only lack a phrase.

### Already self-corrected

Learner: “I just want walk around… I just want to walk around.”

Partner: “There's a covered street nearby. What kind of places do you like exploring?”

Do not say “You added to correctly” or check that same repaired form again. The learner has expressed enough to continue. A later independent use would provide new evidence; this immediate repair does not erase the support already supplied.

### Useful error or uncertain input

Learner: “There is any other?”

Partner: “You can ask, 'What else is available?' We have a smaller one. What size do you need?”

For clear English-only input or an already confirmed meaning, do not ask the learner to confirm it again. A compact wording model can accompany a role answer. When meaning is uncertain, clarify that point first without stacking a new question. Clear natural variants are accepted. If the transcription is unreliable, clarify the object or meaning; do not infer a grammar or pronunciation error from spelling noise.

## Keep the scene alive without taking it over

The next opportunity should use what the learner actually said. If they borrowed an umbrella and want to wander, ask what kinds of places they enjoy, respond to that preference, and leave room to ask the way. Do not insist on an earlier indoor-activity plan; this is still the same visitor-center scene.

Once the learner has expressed a clear plan, continue with that plan; do not replace it with an optional synonym and request another full take. “I like walking around the city” already gives content to answer. Ordinary repeated words while thinking are not evidence of failed pronunciation.

When a goal involves the learner asking a price, time, condition or direction, leave a natural information gap. The partner can invite “What would you like to know before you decide?” rather than announcing every detail. Once the learner asks, answer normally. A short transaction may be enough, especially if the learner is tired or wants to end.

## Review and stop

Review distinguishes: a misunderstanding affecting intent; a useful wording improvement; an optional alternative to already correct English. All worthwhile deduplicated needs belong in the written review; highlight a few priorities without discarding the rest. Requested spoken review may explain, model and guide another attempt, adapting to the learner rather than imposing a recitation sequence.

A pause keeps the same scene and waits. A clear end stops the dialogue immediately, even mid-goal. “Thanks” during an unfinished exchange is not automatically an end. A user-requested change of topic is followed without resetting language or help preferences. A new practice starts a new scene using the learning history only; it does not resume this plot. After an observed end, stopping speech and completing selected written saving are separate obligations.

## A clear next action

Keep a small internal account of confirmed facts, unresolved language help and remaining situation actions. After a completed learner turn, give a useful role response and one explicit relevant next cue. A quoted price alone does not tell a beginner how to proceed; give an open cue for the next action without supplying answers. Explicit help/formulation space, pauses and actual endings are exceptions. Do not mechanically append questions.

Learner: “That's all, thank you.”
Partner: “Where would you like to eat your food?”
Learner says in another language that they want their order packed to take away.
Partner: “You want to take it away. Have I understood you correctly?”
Learner: “This is to go, please.”
Partner: “Of course. I'll pack it for you. How would you like to pay?”

A complaint such as “I don't know what to say when you stop” needs an acknowledgement plus the relevant next situation cue immediately. A complaint about overload instead needs less input and space. After a completed transaction, ask what the learner would like to practice next without naming alternatives, then wait. An explicit goodbye ends practice without another invitation.

## Resolving competing turn needs

A short-turn preference limits information, not just word count. Keep a useful unresolved English repair even when the intent is understood. If model plus role answer is too much, give the model and space, then return to the pending role question after the learner responds. Do not drop the repair merely to keep conversation moving. After overload feedback, reduce later replies as well as the acknowledgement. Two requested details are two information points; avoid appending an unrelated step. Keep a tiny cue for the same pending decision, such as permission to proceed, within the short reply; a relevant cue is different from more factual detail. Appropriate brief answers and self-corrections do not require a full-sentence drill.
