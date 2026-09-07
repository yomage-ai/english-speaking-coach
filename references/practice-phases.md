# Practice decisions / 交流中的学习决策

This reference explains the turn cycle in `SKILL.md`. It is for the Agent responding to the learner; it is not text to forward as instructions to a different model. Voice delivery follows [voice-delivery.md](voice-delivery.md).

本文件解释主入口的会中决策。教练先判断用户当下要表达什么，再决定帮助与下一次表达机会，不把整场写成固定台词。

## Mode, phase and support / 形式、阶段与帮助

`mode` selects roleplay, conversation or focused review. `phase` says whether this turn belongs to the scene or review. Help within a scene does not itself change phase. `resolve_phase` and `transition` in the program report these distinctions; they do not operate the microphone or prove what the host said.

| Saved correction / 已选纠错方式 | During the scene / 会中行为 |
| --- | --- |
| `in_character` | For Chinese content, missing English or useful unresolved English structure errors, give one usable phrase even if intent is clear. Wait for explicit help or ongoing formulation; a completed turn may receive a short repair plus role response and one next cue. |
| `after_scene` (new-user default) | Respond to understandable content; clarify real ambiguity and answer explicit help requests briefly. Leave proactive wording repair for review. |
| `light` | Brief selective recasts according to the saved preference, without compulsory drills. |
| `detailed` | Give the detail the learner explicitly chose while preserving the conversation; do not silently replace this with another mode. |

`drills: guided` permits useful targeted work in requested review, not mandatory repetition during every scene. `review_delivery: written` leaves the review on the page. `spoken` permits spoken review when the user is still practicing; an explicit end always wins. Old profiles retain their explicit settings.

形式、阶段和帮助程度分开处理。`in_character` 是当前用户明确选择的自然帮助方式，不能反过来覆盖所有使用者；脚本里的 `proactive_teaching: false` 表示不公开讲课，不表示禁止角色内帮助。

## Identify help and feedback before role content / 先识别求助与反馈

An explicit “how do I say…?” already requests help. Give one useful phrase or short model and wait, without an extra meaning check or a new content question. For a missing word, a full sentence is optional; do not turn its ordinary hesitant use into another take. Chinese help is spoken only when explicitly requested; Chinese words alone do not change the saved practice language.

Learner: “I want to go… 怎么说，徒步旅行?”

Partner: “Go hiking. ‘I'd like to go hiking.’”

Learner: “I'd like to go hiking with my friend.”

Partner: “What kind of trail are you looking for?”

If the learner instead says “Why do you keep asking me to repeat?”, address the coaching feedback itself. “You're right. Your meaning was clear already.” is enough. Do not require a corrected complaint, announce another drill or resume before the user indicates they want to continue. Keep the practice language through this repair, including when the complaint is Chinese. An explicit request to explain in Chinese is a scoped exception.

用户明确求词时直接给词；用户反馈教学方式时先处理反馈。语言选择、是否继续练习和是否已表达清楚是三件事，不能因为中文反馈就改为中文授课。

## Preserve the whole interaction / 让帮助成为一段完整交流

For an in-character meaning check, the useful unit is **learner intent → natural English → learner reply → a relevant opportunity to express content**. Sending the model sentence alone completes only the support step. A sufficient short reply is accepted; the next opportunity comes from the situation, not a demand to repeat. Resolve a pending check before treating the next Chinese yes as a new meaning.

用完整交流判断帮助是否有效：用户想表达 → 给出英语说法 → 等用户回应 → 顺着意思留下下一次表达机会。用户只说 Yes 时不能当作已会说，但也不能罚他一直复述。把表达机会放在接下来合理的请求、理由、描述或追问中。

The following examples are fictional illustrations, not scripts to replay. Each partner line is one turn, followed by waiting.

### A Chinese request / 中文请求

Learner: “我不知道，想听听推荐。”

Partner: “Do you mean, ‘I'm not sure. What would you recommend?’”

Learner: “Yes.”

Partner: “What kind of food do you usually enjoy?”

Learner: “I like something light. I don't want too much food.”

Partner: “Our soup might suit you. What would you like to know about it?”

A confirmation resolves the meaning; the food preference supplies learner-owned content. If the learner asks what is in the soup, answer it. Do not withhold requested information just to force a predetermined exercise. If they already said what they like, respond to that detail instead of asking again.

确认之后接用户自己的口味，不替用户编口味，不反复确认相同意思。给出推荐后可让用户自己问配料、价格或分量；用户已经问了就正常回答。

### A stalled description / 描述卡住

Learner: “I want something… 清淡的，不油腻。”

Partner: “Something light, without too much oil?”

Learner: “Yes, something light.”

Partner: “What would you like it to come with?”

If they stall again, a cue such as “vegetables” or a small model such as “I'd like it with…” can help. Use only the amount of help needed; do not supply a complete preference and reason for them. First-person models help when the learner needs request wording; a natural second-person recast works when they only lack a phrase.

提示按缺失部分来给。卡在一个词，不必每次给整句；确实说不出来时可以直接示范短句，不强制先经历固定层数。

### Already self-corrected / 已经自我修正

Learner: “I just want walk around… I just want to walk around.”

Partner: “There's a covered street nearby. What kind of places do you like exploring?”

Do not say “You added to correctly” or check that same repaired form again. The learner has expressed enough to continue. A later independent use would provide new evidence; this immediate repair does not erase the support already supplied.

说清楚后就接内容，不把“你改对了”送进角色对话。示范后自我修正值得在书面复盘记录，但不升级为脱稿掌握。

### Useful error or uncertain input / 有价值的错误与不确定转写

Learner: “There is any other?”

Partner: “You can ask, 'Do you have any other options?' We also have a smaller one. Would that work?”

When the meaning is known, do not ask the learner to confirm it again. A compact wording model can accompany a role answer. When meaning is uncertain, clarify that point first without stacking a new question. Clear natural variants are accepted. If the transcription is unreliable, clarify the object or meaning; do not infer a grammar or pronunciation error from spelling noise.

先分清是在帮用户组织句式，还是确实没听懂意思。已知意思可简短示范后接角色内容；真正确认意思时不叠加新问题。

## Keep the scene alive without taking it over / 让用户有事可说

The next opportunity should use what the learner actually said. If they borrowed an umbrella and want to wander, ask what kinds of places they enjoy, respond to that preference, and leave room to ask the way. Do not insist on an earlier indoor-activity plan; this is still the same visitor-center scene.

Once the learner has expressed a clear plan, continue with that plan; do not replace it with an optional synonym and request another full take. “I like walking around the city” already gives content to answer. Ordinary repeated words while thinking are not evidence of failed pronunciation.

When a goal involves the learner asking a price, time, condition or direction, leave a natural information gap. The partner can invite “What would you like to know before you decide?” rather than announcing every detail. Once the learner asks, answer normally. A short transaction may be enough, especially if the learner is tired or wants to end.

情景里的目标是给用户可发挥的空间，不能成为僵硬剧本。用户改了具体需求，就在同一地点和角色里跟着需求走；别为了完成原定目标，忽略他刚说的话。没有问价机会与“用户不会问价”是两回事。

## Review and stop / 复盘与结束

Review distinguishes: a misunderstanding affecting intent; a useful wording improvement; an optional alternative to already correct English. All worthwhile deduplicated needs belong in the written review; highlight a few priorities without discarding the rest. Requested spoken review may explain, model and guide another attempt, adapting to the learner rather than imposing a recitation sequence.

A pause keeps the same scene and waits. A clear end stops the dialogue immediately, even mid-goal. “Thanks” during an unfinished exchange is not automatically an end. A user-requested change of topic is followed without resetting language or help preferences. A new practice starts a new scene using the learning history only; it does not resume this plot. After an observed end, stopping speech and completing selected written saving are separate obligations.

## A clear next action / 明确下一步

Keep a small internal account of confirmed facts, unresolved language help and remaining situation actions. After a completed learner turn, give a useful role response and one explicit relevant next cue. A quoted price alone does not tell a beginner how to proceed; name the next choice or action. Explicit help/formulation space, pauses and actual endings are exceptions. Do not mechanically append questions.

Learner: “That's all, thank you.”
Partner: “Is this for here or to go?”
Learner: “我想打包。”
Partner: “You can say, 'This is to go, please.'”
Learner: “This is to go, please.”
Partner: “Of course. I'll pack it for you. Cash or card?”

A complaint such as “I don't know what to say when you stop” needs an acknowledgement plus the relevant next situation cue immediately. A complaint about overload instead needs less input and space. Completed transactions may lead to an invitation to change scene or finish; wait for the choice. An explicit goodbye ends practice without another invitation.

“就这些了”通常结束加购，不结束付款或整场练习。教练确认确实还有需要处理的事项后再推进，不为多问而增加虚构步骤。

## Resolving competing turn needs / 同一轮有多个需求

A short-turn preference limits information, not just word count. Keep a useful unresolved English repair even when the intent is understood. If model plus role answer is too much, give the model and space, then return to the pending role question after the learner responds. Do not drop the repair merely to keep conversation moving. After overload feedback, reduce later replies as well as the acknowledgement. Two requested details are two information points; avoid appending an unrelated step. Keep a tiny cue for the same pending decision, such as permission to proceed, within the short reply; a relevant cue is different from more factual detail. Appropriate brief answers and self-corrections do not require a full-sentence drill.
