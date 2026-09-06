# Choose a fresh scene / 选择全新场景

Agent chooses the scene. Use the user's current specified topic first; otherwise use the adopted goal, recent scenes and observed support needs to choose a different accessible situation. Each new practice starts from the beginning. History is learning evidence, never a plot to resume. Do not ask the learner to choose a menu, remember old dialogue, or design a syllabus.

Agent 优先按用户指定话题选场景；没有指定时，结合目标、近期场景和实际困难，选择有区别且容易进入的新情境。每次从头建立地点、双方角色和目标，不续接旧剧情，不要求用户回忆上次台词或先选菜单。

## Scene supplied to the startup command / 提交给启动命令的场景

Agent writes this JSON in the task's temporary work directory. All six fields are required nonempty strings. Write `introduction` in the saved `help_language` (Chinese or English), and `opening_line` as natural English spoken by the partner. Match the roles, goal and difficulty; do not reveal a scripted answer the learner must repeat. No model call or scene catalog is required by the script; the Agent makes this bounded creative choice.

Agent 在任务临时目录生成以下结构；六项必填。介绍使用已保存的帮助语言，英文第一句来自角色身份。程序只校验结构，场景合适程度和语言由 Agent 检查；无需用户制作文件。

```json
{
  "setting": "A hotel reception desk in the evening",
  "learner_role": "A guest arriving with a reservation",
  "partner_role": "The hotel receptionist",
  "goal": "Check in and ask when breakfast is served",
  "introduction": "今天练习酒店入住。你是刚到酒店的客人，我是前台。你要办理入住，并询问早餐时间。",
  "opening_line": "Good evening! Welcome to the hotel. Do you have a reservation?"
}
```

For an English-speaking learner, an equivalent introduction is: “You have just arrived at a hotel. You are the guest and I am the receptionist. Check in and ask about breakfast.” An already active live scene keeps its own current context through ordinary turns or pauses; this does not authorize replaying an archived plot. Reuse the chosen JSON while retrying preparation so a service error does not keep changing the scenario.

英语使用者的介绍同样交代三件事：地点、角色、目标。同一场正在进行的对话或临时暂停保留现场上下文；历史课次不作为续演入口。启动重试复用本次场景文件，不反复换题。

The same communication functions can serve different goals:

| Goal / 目标 | Useful situations / 场景 | What to observe / 沟通动作 |
| --- | --- | --- |
| Daily expression / 日常表达 | Plans, hobbies, describing an experience | Say what happened, add a reason, ask a follow-up |
| Travel / 旅行 | Transport, check-in, food, asking for help | Request, clarify, confirm, repair a misunderstanding |
| Workplace / 工作与外企 | Introductions, project updates, meeting questions | Explain a contribution, compare options, clarify expectations |
| Study abroad / 留学交流 | Class questions, group tasks, campus life | Ask for explanation, express a view, discuss and coordinate |

Goals change the conversation context; ability changes the support. Do not confuse them. A beginner seeking an international job still needs short supported answers; a fluent traveler may benefit from negotiating an unexpected problem. Do not infer ability from destination or career ambition. Ask about goals only when the choice materially changes the next useful practice and cannot be inferred.

目标决定场景，能力决定难度，两者分开调整。初学者也可能面向外企，高水平学习者也可能只想旅行。通过实际表达调整短句、追问和帮助程度，不从目的推断等级。

With `correction: in_character`, choose situations with a reason for the learner to formulate something: ask for a recommendation, describe a need, explain a preference or clarify a detail. The partner makes space for those actions and adapts to actual replies; do not script every next turn or take over the learner's question. A transaction finishing quickly is not itself evidence of speaking progress.

选择适合当前水平、需要用户自己组织话语的情境；在对方能接住时再追问理由或细节，不只给菜单，也不提前替用户问完、答完。根据真实回应调整，不预写固定问答链；流程走完不等于表达能力提升。

Use at most one new difficulty at a time: longer answer, another tense, a clarification, or an unexpected change. With deferred correction, adjust difficulty through the situation. Keep one scene per practice. Written review is the new-user default; spoken review requires an explicit request or saved preference. Goodbye or a stop request ends promptly. Do not build an exam curriculum or a pronunciation scorer unless requested.
