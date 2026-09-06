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

维护者按失败所在层验证：改了语音输出规范，就检查完整回应；改了存储，再检查写入与恢复。不能拿更多文件测试来替代没做的情景验收，也不能把程序未证明的事说成绝对保证。
