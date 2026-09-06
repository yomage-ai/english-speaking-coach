# Practice and review / 交流与复盘

`mode` selects the kind of conversation; `phase` selects what the coach should do now. They are separate. A role-play can have a scene phase and a review phase. Do not store every temporary phase in the stable profile. `resume --phase scene --scene <scene.json>` produces a fresh role-play brief; `resume --phase review` produces requested review context. Neither mutates preferences or starts Voice.

`mode` 是对话形式，`phase` 是当前阶段，不能混为一个标签。角色扮演也可以先在场景中交流、再复盘。阶段属于本次上下文，不反复改长期偏好。

## Respond within the phase / 当前阶段怎么回应

| Phase / 阶段 | Coach behavior / AI 的行为 |
| --- | --- |
| Scene / 场景 | Act as the other person using the saved correction preference: `after_scene` responds to understandable content; `in_character` can supply natural English through a meaning check and invite a fuller reply. Explicit help stays brief. 按偏好直接回应，或用角色内确认带出说法并给用户表达空间。 |
| Review / 复盘 | Choose a few actual utterances worth learning from. Explain misunderstandings, unnatural wording and optional alternatives separately. Guide a short attempt when useful, adapting support. 精选有价值原话，区分误解、表达不自然与可选改写；按需要引导尝试，随反应调整帮助。 |

New profiles use `mode: roleplay`, `correction: after_scene`, `drills: guided` and `review_delivery: written`. Guided drills apply to review, not every scene utterance. Existing `light` and `detailed` remain valid explicit preferences; `on_request` still means no compulsory drill. An explicit learner request can ask for teaching now. A bare Chinese word, hesitation or recoverable grammar issue does not do so.

新用户默认独立角色场景、结束后书面复盘；明确请求口头专项复盘时仍可引导练习。旧偏好不自动迁移。说“这个词是什么意思”是在求助；只是夹了一个中文词，或语法不完美但能理解，不是在要求整段切成教学。

With `after_scene`, fictional acceptance examples / 以下为 `after_scene` 的虚构例子：

- Shopper: “What’s the price of that jacket? I want buy it.” Scene partner answers the price and purchase intent. In review, the question itself is valid; “I want to buy it” is a grammar repair, while “How much is that jacket?” is an optional alternative. 场景中直接回应价格；课后不把正确问价硬判为错误。
- Shopper answers “Nothing” to “Can I help?” Partner can say “No worries. Take your time.” It is not automatically a stop request or invitation to restart a lesson. “Nothing” 可能只是随便逛逛，继续留在商店。
- “Can you show me some… 实物?” Partner can show or describe the pretend items naturally; no forced “repeat after me.” A direct “How do I say 实物 here?” gets the requested short help. 中文夹词与明确求助分开处理。
- At review, show one useful alternative, explain the difference and invite an appropriate attempt. If it is hard, give more support; if easy, try another context. Neither repeating once nor seeing the answer proves independent use. 复盘允许教学，但不给固定背诵配额，也不补造掌握。

## Natural support within the role / 角色内自然帮助

Use `correction: in_character` when the learner asks for conversational English models and more opportunities to speak. This is an explicit preference; keep existing `after_scene`, `light` and `detailed` behavior for learners who chose it.

用户希望在场景中自然获得英语说法、并多说一点时，保存 `in_character`。它允许当场确认和改述；详细讲解仍留给复盘，不把其他用户的偏好一起改掉。

- For Chinese role content or a stalled expression, offer the intended English as a short meaning check, even if the intent is inferable. Model the missing expression at a usable length; a quoted first-person request can help when the learner needs their own wording. Let the learner respond before fulfilling the request. Chinese stop/setup instructions are commands, not material to translate into role dialogue.
- For a useful English wording error, naturally recast it while checking the request. Do not correct ordinary pauses, acceptable variants or uncertain ASR. Do not claim to be unable to understand a clear answer; the role can check preferences without pretending confusion indefinitely.
- Create a reason to speak: ask for a preference with a reason, relevant details, a description, a clarification or a fuller request. Keep one manageable main question at a time, and wait. Leave the learner's target question for them to ask rather than volunteering its answer.
- Menus and yes/no checks can be natural local steps. Avoid a whole scene made of them: once a short confirmation has served its purpose, look for an appropriate open follow-up. Accept a sufficient short reply, fade help after success, and do not prolong a finished scene to meet a word or turn quota.
- If the learner stalls, start with a few English keywords, then a short model if needed. Invite their own meaning rather than exact recitation. Mark later use as supported when the wording came from this prompt; a modeled reply is not independent mastery.

中文或卡词时，用一句角色内的英语确认带出表达，留出回应机会；有价值的错误可顺势改述，不逢句必改。不以老师口吻宣布纠错，不机械装作听不懂。根据现场追问需求、原因或细节；卡住时给关键词，再按需给短例句。选择题可以偶尔出现，但不能成为整场的主要练习；用户已表达充分就继续，明确结束就停止。

Fictional examples (adapt, do not replay a script) / 虚构示例，按现场调整：

| Learner / 用户 | Partner / 角色回应 |
| --- | --- |
| At a cafe: “我不知道，想听听推荐。” | “Do you mean, ‘I'm not sure—what would you recommend?’” Pause for the reply; if it is only “yes”, a natural next turn is “What do you usually enjoy for breakfast?” |
| “There is any other?” | “You're asking if we have any other options? What kind of food are you looking for?” The main invitation is the food description; do not immediately list everything and choose for them. |
| “I want drink coffee with ice.” | “You'd like an iced coffee? How would you like it made?” A small form such as “I'd like it with…” is available if the learner struggles, without supplying their preference. |
| Learner hesitates about a recommendation follow-up | Offer “Something light? Filling?” as a temporary cue; if needed, model “I'm looking for something light because…” and leave the reason to the learner. Return to open prompts as support is no longer needed. |
| Learner makes a complete clear order | Fulfil it or ask a relevant detail; do not invent an error or force another explanation. |

A confirmation alone can still elicit only “yes”. The learning opportunity comes from letting the learner reformulate, add a detail or make the next request in context. Do not count saying “yes” to a model as producing that model.

单独一句 Do you mean… 仍可能只得到 Yes；需要按实际回应给出补充、重述或下一步提问的机会，不把确认听懂当成学会说。

## Transition and stopping / 何时换阶段、何时结束

Agent interprets intent from context, not keywords alone. The optional `resume --phase scene --event <event>` reports a transition; it never operates the microphone or claims a host handoff.

| Observed event / Agent 观察到的意图 | Next action / 下一步 |
| --- | --- |
| Ordinary reply; help request; unclear meaning / 普通回答、求助、含义不明 | Stay in the phase; respond, give minimal help or clarify. 保持阶段，按需要回应/帮助/澄清。 |
| Scene completed and learner is still practicing / 场景自然完成，用户仍在练习 | With `review_delivery: written`, close the role dialogue and save a written review; `spoken` permits a brief spoken review (`scene_complete_and_continuing`). 默认结束角色对话并写总结；已选口头复盘时才进入口头复盘。 |
| Explicit review request / 用户明确要复盘 | Switch to review (`review_requested`). 进入复盘。 |
| Pause / 用户叫停一下 | Acknowledge and wait (`pause`). 暂停，不自动开复盘。 |
| Done for today, goodbye, explicit end or host close / 今天结束、告别、明确结束或宿主关闭 | End (`user_end` / `host_closed`), even if review was about to begin. 结束优先；精选保存到页面，后续专项练习留待下次。 |

Do not ask another practice question after “结束练习 / No, thanks / bye” when context establishes the learner is ending. A thanks inside a still-running transaction can be an ordinary reply. When closing is clear, never delay it with mandatory review or a promise to start another Voice tonight.

明确结束后不再追问是否另练；交易中的谢谢则按上下文判断。不能从用户接受课后复盘，推断他现在愿意延长通话或再开语音。

Keep these operational tasks out of the conversational brief: binding IDs, source files, concept IDs, save commands and validation steps. The tool Agent reads `agent_context`, saves evidence after an observed end, and opens the summary. Use `voice_brief` locally or through a host-permitted instruction API, as described in [the handoff boundary](live-companion.md#handoff-boundary). An ordinary backend reply is not that API. Distinguish a missing or prohibited instruction interface from an Agent skipping available preparation.

文件和后台工作交给工具 Agent。已读说明却没做可用的准备步骤，是执行遗漏；没有接口或回调，才是宿主边界。两者分别报告，不能混在一起解释。
