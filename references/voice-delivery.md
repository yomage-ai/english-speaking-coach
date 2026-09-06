# Voice and page delivery / 语音与页面交付

Read this once when handling an active Voice practice. Inspect the actual host protocol; tool names, routing permissions and output channels vary. Follow host requirements rather than assuming a universal Voice API.

The responding Agent is responsible for every message it produces, including commentary. A separate Voice model may paraphrase those messages. The companion page reads transcripts and adds translations; it does not control the spoken dialogue.

Agent 对自己输出的全部内容负责。语音模型可能转述过程消息，也可能自行组织语言；字幕页只显示原话和翻译，不负责控制语音。不能把网页双语、帮助语言或后台报告语言当作角色对话语言。

## Speech-facing messages / 可能被说出来的内容

During the scene, the saved practice language applies to **every ordinary output item**, not only the final reply. With English-first practice, an English final answer accompanied by Chinese progress commentary is an invalid delivery. No item contains a running grade, grammar appraisal, storage status or narration about what another assistant is doing.

If the host requires a `[STATUS]` item for each delegation, keep it a short grounded statement of the understood in-scene meaning, in English. Do not omit a required channel, fake progress, address instructions to Voice, or fill it with “I am checking.” The `[COMPLETE]` item supplies one useful conversational response. Both items should remain suitable if closely paraphrased together; do not put a second main question in STATUS.

Fictional example after the learner asks in Chinese to borrow an umbrella:

- Required status content: “You're asking to borrow an umbrella.”
- Completed response content: “Do you mean, ‘Can I borrow an umbrella?’”

After the learner has already repaired “I want to walk around”:

- Required status content: “You just want to walk around.”
- Completed response content: “There's a covered street nearby. What kind of places do you like exploring?”

These are ordinary scene content, not instructions for another model. Adapt them; do not emit protocol tags on a host that does not require them. When no interim message is required, a short conversation turn needs no separate progress narration.

宿主要求状态消息时仍须发，但内容用英文表达已理解的现场意思，不评价“用户已经学会了”“刚才补上了 to”。最终回复给出一句自然回应。所有可能进入听觉的内容一起审查，不能把 STATUS 当成用户听不到的日志。

For setup, the help language can report a necessary readiness fact briefly. Deliver the full scene introduction only once at the opening; do not scatter it across preparation updates. During explicit Chinese help, answer the requested point minimally and then return to the English scene. Written review belongs to the host's visible text/artifact surface, not ordinary speech context. Use its documented inline directive when required; do not guess a directive or claim an ordinary backend reply is visible text.

## Replying is distinct from configuring / 回应与设置分开

`context.voice_brief` is local guidance for the responding Agent. A documented callable instruction-update interface may accept it if the host permits that use. A normal backend reply is not such an interface. Never paste raw prompts, simulate role messages, encode instructions or disguise commands as facts to bypass a prohibition.

A missing instruction-update interface does **not** remove the ordinary conversational path. When the host sends a learner turn, use the restored preferences and the turn cycle to supply appropriate natural content through that permitted reply. Do not send a limitations lecture during each scene turn or declare improvement impossible merely because there is no instruction API.

没有设置接口，不等于不能接好眼前这一句。宿主把用户话语交给 Agent 时，Agent 可以按已读规范提供自然回应；也必须把自己的状态消息写对。是否每轮都回调、语音端是否原样采用，仍要从实际语音检查，不能仅从后台正确回答推定成功。

If the actual spoken reply departs from an otherwise compliant backend response, record that specific observation separately from backend mistakes. Do not claim control you do not have or keep inventing global prompts. The next diagnosis targets the demonstrated delivery boundary, with exact utterance evidence. No new product, automatic model change or permanent background control is implied.

<a id="page-delivery"></a>
## Page delivery / 网页显示

The intended result is the correct local page visible to the learner, not a submitted request. Keep backend readiness, open request, visible route and actual transcript/lesson content as separate facts in the current task context.

1. Open the exact prepared live/review URL through an allowed visible host surface.
2. Inspect that surface after the open. A screen capture taken before opening, HTTP 200, promoted tool item or `queued` response is insufficient.
3. If queued or wrong, use one available permitted recovery path: navigate/reuse a visible browser tab, or the host's required delegated browser executor. Follow its actual routing rules; do not declare the browser unavailable before checking the permitted route. Recheck the exact route and relevant live run or saved lesson.
4. After this bounded attempt, if the surface is still unavailable, mark display unresolved and place the usable link plus the specific display issue on the written surface. Do not repeat the same queued request indefinitely, ask the learner to run commands, or claim the page was opened.

初次打开后必须接着验证。排队就走已有的可见浏览器恢复路径；需要委派浏览器的宿主由 Agent 按规则委派。正常对话不反复重开页面。实在无法显示才单独报告那一步，不能用“后台已就绪”代替。

At closeout, show this Voice's waiting route early; the page polls local saved records about once per second while visible, for at most five minutes. After a successful save, verify it displays the matching lesson. If the learner navigated elsewhere, do not repeatedly pull them back. Page failure does not justify discarding the review; saving failure does not become success because the waiting page exists.

For initial enablement, backend errors, drain and recovery, use [live-companion.md](live-companion.md). The page does not start the microphone, save mastery, or force Voice instruction adoption.
