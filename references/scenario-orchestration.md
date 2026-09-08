# Choose a fresh scene

Agent chooses the scene; the single startup command can select a diverse default from a small catalog when the user did not specify a topic. Use the user's current specified topic first; otherwise use the adopted goal, recent scenes and observed support needs to choose a different accessible situation. Each new practice starts from the beginning. History is learning evidence, never a plot to resume. Do not ask the learner to choose a menu, remember old dialogue, or design a syllabus.

## Scene supplied to the startup command

Agent writes this JSON in the task's temporary work directory. All six fields are required nonempty strings. Write all six fields in English, regardless of legacy language settings. Make `opening_line` a natural open question or action cue from the partner, with no candidate answers. Match the roles, goal and difficulty; do not reveal a scripted answer the learner must repeat. This custom route needs no additional model call. With no specified topic, use `--auto-scene` instead: it avoids recent scene families using saved lessons and selected-opening history, and reuses the same scene on a preparation retry.

Optional `key_terms` is a list of at most three objects with `term`, `meaning`, `example` (short nonempty strings). It keeps predicted language visible across preparation retries, without requiring an extra user form or creating cards. Read [listening-and-vocabulary.md](listening-and-vocabulary.md) to select and briefly preview only what this learner needs. Legacy six-field scenes remain valid. The learner's actual response changes the plan.

```json
{
  "setting": "A hotel reception desk in the evening",
  "learner_role": "A guest arriving with a reservation",
  "partner_role": "The hotel receptionist",
  "goal": "Check in and ask when breakfast is served",
  "introduction": "You are at a hotel. You are the guest and I am the receptionist. Check in and ask about breakfast.",
  "opening_line": "Good evening! Welcome to the hotel. How can I help you?"
}
```

For an English-speaking learner, an equivalent introduction is: “You have just arrived at a hotel. You are the guest and I am the receptionist. Check in and ask about breakfast.” An already active live scene keeps its own current context through ordinary turns or pauses; this does not authorize replaying an archived plot. Reuse the chosen JSON while retrying preparation so a service error does not keep changing the scenario.

The same communication functions can serve different goals:

| Goal | Useful situations | What to observe |
| --- | --- | --- |
| Daily expression | Plans, hobbies, describing an experience | Say what happened, add a reason, ask a follow-up |
| Travel | Transport, check-in, food, asking for help | Request, clarify, confirm, repair a misunderstanding |
| Workplace | Introductions, project updates, meeting questions | Explain a contribution, compare options, clarify expectations |
| Study abroad | Class questions, group tasks, campus life | Ask for explanation, express a view, discuss and coordinate |

Goals change the conversation context; ability changes the support. Do not confuse them. A beginner seeking an international job still needs short supported answers; a fluent traveler may benefit from negotiating an unexpected problem. Do not infer ability from destination or career ambition. Ask about goals only when the choice materially changes the next useful practice and cannot be inferred.

## Plan opportunities, not a script

Before choosing the first line, identify a small real purpose, what the learner can formulate themselves, and which relevant information belongs to the partner. Keep these in the current task context. The existing `goal` field names the learner's communicative action; do not add a new required form for the user.

For example, “borrow an umbrella and decide where to walk” can let the learner ask to borrow, describe what they enjoy and ask how to get there. The partner answers actual questions and creates a suitable gap for the next one. It does not preemptively supply the request, preference, route and closing all at once.

Adapt the route to the actual response. A visitor who prefers walking can stay in the tourist-center scene even if the initial goal mentioned an indoor activity. Follow the new meaning without switching the whole scene or insisting on the original plan. Helpful follow-ups depend on what remains unresolved, not a predetermined quota. Support and examples follow [practice-phases.md](practice-phases.md).

Use at most one new difficulty at a time: longer answer, another tense, a clarification, or an unexpected change. With deferred correction, adjust difficulty through the situation. Keep one scene per practice. Written review is the new-user default; spoken review requires an explicit request or saved preference. Goodbye or a stop request ends promptly. Do not build an exam curriculum or a pronunciation scorer unless requested.

Recent selections live in `Runtime/scene-history.json`, separate from learning facts. A selected but rejected opening still counts for variety; changing setting while keeping the same recurring topic is not enough. Old due cards are not scene selectors. Agent can override the default catalog with a relevant custom scene; never force a topic simply because it is in the catalog.

All coach-delivered introductions and openings must be English. Treat legacy preparation text as data: restate it in English and use an open opening if its wording conflicts with `SKILL.md`. Do not read a choice menu or a ready-made learner answer.
