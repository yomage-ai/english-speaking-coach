# Validate a whole practice

Use this when auditing a real practice or revising the coaching workflow. Program tests, independent rehearsals and actual host behavior answer different questions. Do not merge them into one “all passed” claim.

| Level | Evidence | What it cannot establish |
| --- | --- | --- |
| Program | Actual CLI/API results, preserved source data, correct page updates, duplicate/end handling | That a model followed the coaching approach |
| Independent rehearsal | A fresh evaluator receives the skill, a realistic profile, scene and chronological learner turns; inspect all replies | Audio timing, frontend paraphrasing or real learning gains |
| Actual practice | Loaded skill/profile, delivered backend messages, unique spoken turns, page evidence, saved lesson | Every future session will behave identically |

A normal rehearsal can use fictional input in a temporary workspace with no microphone, real lessons or external sends. Do not give the evaluator the suspected defect or desired answer. Mark the result as a rehearsal. A tool-less rehearsal cannot pass browser or save checks.

## Review the actual session

Read the full available public conversation, deduplicate cumulative transcript tails, and distinguish what was generated, delivered and actually spoken. A skill embedded by the host may already be fully loaded without a `cat SKILL.md` command; compare the supplied body/version before diagnosing a missed read. Prefer source logs and actual records to a retrieval summary.

| Stage | Passing observation | Failure or missing evidence |
| --- | --- | --- |
| Preparation | Current preferences read; scene and exact active binding verified; intended page visible | Missing execution, wrong session, queued-only display; distinguish unavailable tools from skipped recovery |
| Introduction | Setting, both roles and learner goal introduced once, followed by English opening | Only “ready?”, incomplete setup, old plot, repeated introduction |
| Scene language | All coach responses use English, including scene setup, help and closing acknowledgements; maintenance follows the user’s language | A non-English exercise reply without a current user instruction; English confirmation of a maintenance request instead of acting on it |
| Natural support | Non-English or mixed input receives one English restatement and check; stalls receive minimal English help and space | Silently completing the request, teaching announcement, answering the check in the same turn, repetitive checks after resolution |
| Learner expression | Appropriate reasons, details, descriptions or learner-originated questions occur; supplied wording is identified | Partner supplies both sides; repeated menus; every successful reply gets another forced drill |
| Ending | Actual user end honored; no further exercise | Continuing or restarting after a clear end; treating a pause as completed practice |
| Review | Correct source quotes/support, successful save+validation and visible matching lesson | Supported wording labeled independent, ASR treated as pronunciation, a waiting link described as saved/shown |

If a relevant opportunity never occurred, say “not observed,” not “passed” or “learner failed.” The user may end early; that is not an evaluation failure. Label coach behavior separately from learner ability. A missing open question in a short scene is assessed in context, not against a numeric quota.

## Rehearsal cases

Use varied fictional situations and supported modes. Include: a fresh start with history; non-English and mixed-language intent; a useful English error; an already self-corrected sentence; yes-only confirmation; continued difficulty; a natural learner question; a sufficient short answer; an explicit request to leave practice and diagnose a fault in the user’s language; pause versus end; a queued browser; duplicate end/tail. Inspect ordinary progress messages as well as final replies. Do not require exact wording or a predetermined number of turns.

Changes to speaking rules need a speaking-level check. Changes to storage need a storage check. A release can be source-synchronized and program-tested while actual Voice behavior remains unverified; report those statuses plainly. Before sending the learner to retry a known failure, complete the checks the Agent can perform itself, and explain what the real trial alone can resolve.

For listening and vocabulary changes, include supported short speech on a worthwhile adult topic, an unfamiliar multiword phrase, a request for two details, an explicit overload complaint, a later continuation and an independently chosen question. Inspect the total spoken turn, number of information points, predicted versus actually queried words, simpler explanations, and the saved word evidence. Check that recent coaching needs survive compact preparation while the old plot stays archived. Test both legacy scenes and scenes with a few preparation terms. Do not infer listening ability from pauses, subtitle use or ASR alone.

## Delivery-boundary rehearsal

Include both legacy English-first and bilingual profiles. Test English setup and introduction, non-English coaching feedback, a requested topic change and a request for another language. Every in-exercise coach reply follows the English practice contract; maintenance replies use the user’s current language without a meaning check or automatic exercise restart. Non-English exercise content receives one English check, while clear pacing controls receive an English action acknowledgement. Include a request for the coach to choose the next scene: it should act without a confirmation loop or topic menu. Inspect every output item. For content, include direct word help, a non-English acknowledgement resolving a check, a clear sentence with pauses and an optional alternative that does not need repetition. Test shopping and payment prompts, stalls and scene completion: no response may supply answer choices. Follow a confirmation with an open opportunity for the learner to formulate content. Follow the actual answers across turns, not isolated ideal examples.

When the host uses a separate speech model, a second isolated rehearsal can receive only the ordinary backend outputs and the learner turns under that host's available protocol. Inspect the resulting speech-facing text without telling the evaluator which failure to look for. This is a delivery simulation, not actual Voice. If it still translates or adds drills, keep that failure visible and revise the evidence-based response path; do not treat a shorter prompt as a proven cure.

For closeout, include an ended callback with a generic acknowledgement hint. Verify exact-Voice record lookup, deduplication, write validation and written display independently. Repeated tails must reuse the saved record; missing or active-source evidence must not be labeled a verified closed transcript.

## Whole-flow regressions

- Repeated starts: reuse an exact binding on retries; consecutive unsaved openings still participate in scene diversity. Due cards never select the scene by themselves.
- Missing English: Chinese intent, a Chinese noun and “I don't know how to say…” each receive one usable phrase before role content. Confirmed meaning moves forward; support does not force a repeat. Include a recap after several agreed items to check that none disappear.
- Captions: test 40→41→42 utterances, delayed Chinese, viewport resize, explicit pause/resume and a run change. The document has no vertical overflow in live view; only the feed scrolls. Following stays on by default.
- Review: exercise exact-Voice waiting, preparing, delayed and saved states; saved redirects once to the matching lesson. Distinguish total end-turn latency from local command duration.
- Vocabulary: session card count, theme counts and pager share the same scope; all-history is one clear action away. Test rapid reverse flips and reduced motion; only one face is visible and no text is mirrored. Chinese prompts should not contain the English answer.
- Runtime: compare source, installed files and loaded service revision after Go or embedded page changes. Agent uses the existing owner/manager for a necessary restart after Voice ends. A page refresh alone is insufficient.

Run `go test -race ./...`, `go vet ./...`, `node tests/test_page_updates.cjs`, and `node tests/test_live_updates.cjs` from the skill source. These are Agent maintenance commands, not learner setup steps. Verify actual viewport/keyboard interactions with the available browser tools. An independent textual rehearsal checks the generated coaching responses; it does not certify native Voice latency or paraphrasing.

## English form, continuity and closeout coverage

Include understandable but unresolved English structure errors; a reply that only fulfills the role request fails that opportunity in in-character mode. Ordinary hesitations, self-repair and correct variants still need no forced correction. After a completed ordinary exchange, inspect an explicit situation-based cue or action, not just a question-mark count. Help/formulation space and explicit pauses remain valid. Check the response after the learner accepts help, and after a complete transaction while practice continues.

Storage verification includes five or more different useful needs in one lesson, exact source quote links, canonical concept references without copied meaning text, omitted-turn accounting, conservative support, concurrent IDs and duplicate callbacks. Browser verification leaves the review route, waits for a save while viewing an old lesson, opens the exact result from the persistent entry, and finds both priority and remaining expressions plus coach adjustments. A long timer does not by itself prove interruption.

## Startup and maintenance regression / 启动与维护回归

Include a plain text task, an ended Voice, conflicting task metadata, host-active state without source identity and a damaged complete line. None may create a live binding, watcher, scene history or supervisor through prepare. Pair them with an active Voice that ingests valid segments and survives an exact retry. Check legacy empty bindings in the page: a model connection alone must not claim captions are ready. Test a copied shell entry and cached binary with lost executable bits, and reject changed bytes with an existing checksum receipt. Record Intel cross-compilation separately from native Intel execution.

Rehearse a practice → Chinese page-fault report → technical discussion → explicit return to practice sequence. No diagnostic request needs an English meaning check, and repairs do not resume the exercise on their own. Preserve practice wording help and pacing controls on either side of the maintenance interval.
