# Practice and review / 交流与复盘

`mode` selects the kind of conversation; `phase` selects what the coach should do now. They are separate. A role-play can have a scene phase and a review phase. Do not store every temporary phase in the stable profile. `resume --phase scene|review` produces the corresponding context without mutating preferences or starting Voice.

`mode` 是对话形式，`phase` 是当前阶段，不能混为一个标签。角色扮演也可以先在场景中交流、再复盘。阶段属于本次上下文，不反复改长期偏好。

## Respond within the phase / 当前阶段怎么回应

| Phase / 阶段 | Coach behavior / AI 的行为 |
| --- | --- |
| Scene / 场景 | Act as the other person. Answer understandable content. Clarify an actual ambiguity naturally. Explicit help gets a short answer, then return to the situation. 回应内容，真实不明白时澄清；明确求助才最小帮助，然后回角色。 |
| Review / 复盘 | Choose a few actual utterances worth learning from. Explain misunderstandings, unnatural wording and optional alternatives separately. Guide a short attempt when useful, adapting support. 精选有价值原话，区分误解、表达不自然与可选改写；按需要引导尝试，随反应调整帮助。 |

New profiles use `correction: after_scene` and `drills: guided`. Guided drills apply to review, not every scene utterance. Existing `light` and `detailed` remain valid explicit preferences; `on_request` still means no compulsory drill. An explicit learner request can ask for teaching now. A bare Chinese word, hesitation or recoverable grammar issue does not do so.

新用户默认把纠正留到课后，并允许复盘引导练习。旧偏好不自动迁移。说“这个词是什么意思”是在求助；只是夹了一个中文词，或语法不完美但能理解，不是在要求整段切成教学。

Fictional acceptance examples / 虚构验收例子：

- Shopper: “What’s the price of that jacket? I want buy it.” Scene partner answers the price and purchase intent. In review, the question itself is valid; “I want to buy it” is a grammar repair, while “How much is that jacket?” is an optional alternative. 场景中直接回应价格；课后不把正确问价硬判为错误。
- Shopper answers “Nothing” to “Can I help?” Partner can say “No worries. Take your time.” It is not automatically a stop request or invitation to restart a lesson. “Nothing” 可能只是随便逛逛，继续留在商店。
- “Can you show me some… 实物?” Partner can show or describe the pretend items naturally; no forced “repeat after me.” A direct “How do I say 实物 here?” gets the requested short help. 中文夹词与明确求助分开处理。
- At review, show one useful alternative, explain the difference and invite an appropriate attempt. If it is hard, give more support; if easy, try another context. Neither repeating once nor seeing the answer proves independent use. 复盘允许教学，但不给固定背诵配额，也不补造掌握。

## Transition and stopping / 何时换阶段、何时结束

Agent interprets intent from context, not keywords alone. The optional `resume --phase scene --event <event>` reports a transition; it never operates the microphone or claims a host handoff.

| Observed event / Agent 观察到的意图 | Next action / 下一步 |
| --- | --- |
| Ordinary reply; help request; unclear meaning / 普通回答、求助、含义不明 | Stay in the phase; respond, give minimal help or clarify. 保持阶段，按需要回应/帮助/澄清。 |
| Scene completed and learner is still practicing / 场景自然完成，用户仍在练习 | Brief review may start (`scene_complete_and_continuing`). 可简短复盘，不重开固定教学流程。 |
| Explicit review request / 用户明确要复盘 | Switch to review (`review_requested`). 进入复盘。 |
| Pause / 用户叫停一下 | Acknowledge and wait (`pause`). 暂停，不自动开复盘。 |
| Done for today, goodbye, explicit end or host close / 今天结束、告别、明确结束或宿主关闭 | End (`user_end` / `host_closed`), even if review was about to begin. 结束优先；精选保存到页面，后续专项练习留待下次。 |

Do not ask another practice question after “结束练习 / No, thanks / bye” when context establishes the learner is ending. A thanks inside a still-running transaction can be an ordinary reply. When closing is clear, never delay it with mandatory review or a promise to start another Voice tonight.

明确结束后不再追问是否另练；交易中的谢谢则按上下文判断。不能从用户接受课后复盘，推断他现在愿意延长通话或再开语音。

Keep these operational tasks out of the conversational brief: binding IDs, source files, concept IDs, save commands and validation steps. The tool Agent reads `agent_context`, saves evidence after an observed end, and opens the summary. Pass only `voice_brief` plus essential situation context to Voice when an actual handoff is available. Absence of that interface is a host limitation; reading instructions but skipping available preparation is an Agent execution omission.

文件和后台工作交给工具 Agent。已读说明却没做可用的准备步骤，是执行遗漏；没有接口或回调，才是宿主边界。两者分别报告，不能混在一起解释。
