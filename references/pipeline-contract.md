# Pipeline correctness / 流程正确性

Use this contract when changing source ingestion, translation, review or live-page state. It describes observable guarantees; model meaning judgments and actual native Voice speech require separate evaluation.

维护转写、翻译、复盘或双语页面时读取。程序验证结构、身份和状态；AI 判断译意和教学，宿主控制实际语音，三者不能混为同一种保证。

| Boundary / 环节 | Invariant / 必须保持 | Failure and recovery / 失败与恢复 |
| --- | --- | --- |
| Host → transcript | Exact task + Voice + segment identity; original text remains evidence. Live and review use the same segment parser. / 核实任务、Voice 和片段身份，保留原话。 | Incomplete final bytes wait. Damaged complete rows or conflicting identities stop the unsafe read visibly; never silently skip them and claim complete coverage. / 半行等待，坏行报错，不冒充完整。 |
| Transcript → translation | A result belongs to the same full source text that was requested, including after revisions. Chinese spans remain intact. / 译文绑定具体版本原话，保留中文部分。 | Input limits, unsupported text and completed malformed model output affect only their utterance/request. Valid rows survive; a later conflicting/duplicate unit revokes only its affected source version. Each rejected row has at most two automatic attempts. / 句子问题只影响该句。 |
| Translation scheduling | Captions and written coaching use separate bounded lanes; complete validated utterances publish individually. / 字幕与教学分开，一句校验完立即显示。 | New or revised learner/coach transcript content cancels obsolete teaching; publication and display require the same exchange fingerprint. Translation-only updates do not invalidate help; no stale hint queue. Release previous ephemeral thread subscriptions, retain only bounded explicit context. / 取消过期提示，限制上下文与资源。 |
| Model connection | Account, model and protocol are verified; transcript instructions never become tool actions. / 验证账户与协议，不执行原话中的指令。 | Live and closed recovery both stop after three consecutive connection failures. User retry is explicit and scoped; no unlimited automatic loop. Chinese originals remain readable without a model. / 连续连接失败最多三次，中文原话不等待模型。 |
| Translation content | Every requested unit is accounted for. A name preserves exact spelling and is labeled as original name text. / 英文片段逐项核对，专名原样保留并标明。 | Capitalization cannot prove name semantics. Structural validation does not prove translation accuracy. Unknown words, ASR ambiguity, quantities and objects must not be silently invented or “corrected.” / 不用大小写猜词性，不把识别疑点改成确定事实。 |
| Review → archive | Exact source excerpts, complete available-turn accounting, English/Chinese fields and supported versus independent evidence are checked before commit. Preview uses the same language boundary. / 先核对证据与字段，再保存。 | Partial output is a provisional suggestion. Valid drafts/previews survive repair. Corrupt watch files retain diagnostics without stopping unrelated jobs. Existing saved Voice identity is reused. / 建议不冒充已保存，坏任务不拖停其他任务。 |
| Recovery | Compare source contents, not only row counts or completion labels. Scope recovery to one closed Voice. / 恢复核对内容，不能只数条数。 | A revised segment invalidates its old translation and errors; an older in-flight result cannot replace it. Recovery never takes over another active practice. / 新原话使旧译文失效，恢复不抢其他场次。 |
| Page | Default follow shows latest; pause keeps the reading window and visible utterance stable while translations update. / 跟随看最新，暂停保留阅读位置。 | Ended-but-pending captions offer retry. An asynchronous retry keeps the clicked Voice identity even after navigation. Imported captions do not pretend the old machine's source exists. / 状态与动作一致，不重试错场。 |

## Verification / 验证

Use synthetic archives and model protocol fixtures for corruption, UTF-8 partial writes, revised source text during a request, malformed output, mixed scripts, long input, connection outages, restart/recovery, exact Voice isolation and paused-page updates. Keep valid and invalid rows in the same scenario so a test establishes failure isolation, not just rejection. Real-account fictional requests assess wording and latency separately. Never write synthetic successes into a learner archive.

测试必须把正常句与异常句放在同一流程里，验证失败隔离、恢复和状态显示；不能只证明“坏输入被拒绝”。真实账户的虚构请求用于评估译意和耗时，不录入用户学习成绩。程序测试不能证明语音识别准确、原生 Voice 每轮遵守 Skill 或用户已经掌握。
