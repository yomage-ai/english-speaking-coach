# Validate a whole practice / 完整体验验收

Use this when auditing a real practice or revising the coaching workflow. Program tests, independent rehearsals and actual host behavior answer different questions. Do not merge them into one “all passed” claim.

| Level / 层次 | Evidence / 可用依据 | What it cannot establish / 不代表 |
| --- | --- | --- |
| Program | Actual CLI/API results, preserved source data, correct page updates, duplicate/end handling | That a model followed the coaching approach |
| Independent rehearsal | A fresh evaluator receives the skill, a realistic profile, scene and chronological learner turns; inspect all replies | Audio timing, frontend paraphrasing or real learning gains |
| Actual practice | Loaded skill/profile, delivered backend messages, unique spoken turns, page evidence, saved lesson | Every future session will behave identically |

A normal rehearsal can use fictional input in a temporary workspace with no microphone, real lessons or external sends. Do not give the evaluator the suspected defect or desired answer. Mark the result as a rehearsal. A tool-less rehearsal cannot pass browser or save checks.

## Review the actual session / 核对真实会话

Read the full available public conversation, deduplicate cumulative transcript tails, and distinguish what was generated, delivered and actually spoken. A skill embedded by the host may already be fully loaded without a `cat SKILL.md` command; compare the supplied body/version before diagnosing a missed read. Prefer source logs and actual records to a retrieval summary.

| Stage / 阶段 | Passing observation / 通过依据 | Failure or missing evidence / 失败或未观察到 |
| --- | --- | --- |
| Preparation | Current preferences read; scene and exact active binding verified; intended page visible | Missing execution, wrong session, queued-only display; distinguish unavailable tools from skipped recovery |
| Introduction | Setting, both roles and learner goal introduced once, followed by English opening | Only “ready?”, incomplete setup, old plot, repeated introduction |
| Scene language | All speech-facing messages and spoken role turns follow the language preference | Chinese process/teacher commentary or unsolicited spoken translation; explicit help and end acknowledgements are evaluated in their own scope |
| Natural support | A Chinese/stalled-expression opportunity receives usable English, with a pause for the learner | Silently completing the request, teaching announcement, answering the check in the same turn, repetitive checks after resolution |
| Learner expression | Appropriate reasons, details, descriptions or learner-originated questions occur; supplied wording is identified | Partner supplies both sides; repeated menus; every successful reply gets another forced drill |
| Ending | Actual user end honored; no further exercise | Continuing or restarting after a clear end; treating a pause as completed practice |
| Review | Correct source quotes/support, successful save+validation and visible matching lesson | Supported wording labeled independent, ASR treated as pronunciation, a waiting link described as saved/shown |

If a relevant opportunity never occurred, say “not observed,” not “passed” or “learner failed.” The user may end early; that is not an evaluation failure. Label coach behavior separately from learner ability. A missing open question in a short scene is assessed in context, not against a numeric quota.

## Rehearsal cases / 规范重构后的检查情境

Use varied fictional situations and supported modes. Include: a fresh start with history; Chinese intent; a useful English error; an already self-corrected sentence; yes-only confirmation; continued difficulty; a natural learner question; a sufficient short answer; explicit Chinese explanation; pause versus end; a queued browser; duplicate end/tail. Inspect ordinary progress messages as well as final replies. Do not require exact wording or a predetermined number of turns.

Changes to speaking rules need a speaking-level check. Changes to storage need a storage check. A release can be source-synchronized and program-tested while actual Voice behavior remains unverified; report those statuses plainly. Before sending the learner to retry a known failure, complete the checks the Agent can perform itself, and explain what the real trial alone can resolve.

For listening and vocabulary changes, include supported short speech on a worthwhile adult topic, an unfamiliar multiword phrase, a request for two details, an explicit overload complaint, a later continuation and an independently chosen question. Inspect the total spoken turn, number of information points, predicted versus actually queried words, simpler explanations, and the saved word evidence. Check that recent coaching needs survive compact preparation while the old plot stays archived. Test both legacy scenes and scenes with a few preparation terms. Do not infer listening ability from pauses, subtitle use or ASR alone.

维护者按失败所在层验证：改了语音输出规范，就检查完整回应；改了存储，再检查写入与恢复。不能拿更多文件测试来替代没做的情景验收，也不能把程序未证明的事说成绝对保证。

## Delivery-boundary rehearsal / 交付边界演练

For an English-first profile, include setup progress, an English introduction with a separate written Chinese scene card, a Chinese coaching complaint, a user-requested topic change and an explicit Chinese explanation. Inspect every output item. For content, include direct word help, a Chinese yes resolving a check, a clear sentence with pauses and an optional alternative that does not need repetition. Follow the actual answers across turns, not isolated ideal examples.

When the host uses a separate speech model, a second isolated rehearsal can receive only the ordinary backend outputs and the learner turns under that host's available protocol. Inspect the resulting speech-facing text without telling the evaluator which failure to look for. This is a delivery simulation, not actual Voice. If it still translates or adds drills, keep that failure visible and revise the evidence-based response path; do not treat a shorter prompt as a proven cure.

For closeout, include an ended callback with a generic acknowledgement hint. Verify exact-Voice record lookup, deduplication, write validation and written display independently. Repeated tails must reuse the saved record; missing or active-source evidence must not be labeled a verified closed transcript.

## Whole-flow regressions / 整体回归

- Repeated starts: reuse an exact binding on retries; consecutive unsaved openings still participate in scene diversity. Due cards never select the scene by themselves.
- Missing English: Chinese intent, a Chinese noun and “I don't know how to say…” each receive one usable phrase before role content. Confirmed meaning moves forward; support does not force a repeat. Include a recap after several agreed items to check that none disappear.
- Captions: test 40→41→42 utterances, delayed Chinese, viewport resize, explicit pause/resume and a run change. The document has no vertical overflow in live view; only the feed scrolls. Following stays on by default.
- Review: exercise exact-Voice waiting, preparing, delayed and saved states; saved redirects once to the matching lesson. Distinguish total end-turn latency from local command duration.
- Vocabulary: session card count, theme counts and pager share the same scope; all-history is one clear action away. Test rapid reverse flips and reduced motion; only one face is visible and no text is mirrored. Chinese prompts should not contain the English answer.
- Runtime: compare source, installed files and loaded service revision after Python changes. Agent uses the existing owner/manager for a necessary restart after Voice ends. A page refresh alone is insufficient.

Run `python3 -m unittest discover -s tests`, `node tests/test_page_updates.cjs`, and `node tests/test_live_updates.cjs` from the skill source. These are Agent maintenance commands, not learner setup steps. Verify actual viewport/keyboard interactions with the available browser tools. An independent textual rehearsal checks the generated coaching responses; it does not certify native Voice latency or paraphrasing.

## English form, continuity and closeout coverage / 英文句型、推进与复盘覆盖

Include understandable but unresolved English structure errors; a reply that only fulfills the role request fails that opportunity in in-character mode. Ordinary hesitations, self-repair and correct variants still need no forced correction. After a completed ordinary exchange, inspect an explicit situation-based cue or action, not just a question-mark count. Help/formulation space and explicit pauses remain valid. Check the response after the learner accepts help, and after a complete transaction while practice continues.

Storage verification includes five or more different useful needs in one lesson, exact source quote links, canonical concept references without copied meaning text, omitted-turn accounting, conservative support, concurrent IDs and duplicate callbacks. Browser verification leaves the review route, waits for a save while viewing an old lesson, opens the exact result from the persistent entry, and finds both priority and remaining expressions plus coach adjustments. A long timer does not by itself prove interruption.

记录所有实际生成的演练回应，包括失败版本；修订后另做演练，不回写旧结果伪装首次通过。真实 Voice 的延迟和改述仍需实际语音证据。
