# Review without interrupting conversation / 不打断对话的复习

The primary outcome is that the learner can communicate an intended meaning. Revisit words and chunks in meaningful exchanges, rather than accumulating a vocabulary total.

核心是表达意图是否实现。词汇和句块通过真实交流重访，不追求累计词数。

| Observed state | Interpretation / 含义 | Next useful evidence / 下一个观察 |
| --- | --- | --- |
| `not_tested` | Collected only / 只收集，尚未尝试 | Try using it in a real question |
| `source_text` | Needed the full sentence / 看原句说出 | Try later with less support |
| `keywords` | Used keyword support / 借关键词说出 | Try after a delay without words shown |
| `independent` | Answered without a prompt / 曾无提示说出 | Use on a different occasion |
| `transfer` | Used in a changed context / 曾换场景使用 | Revisit less often, with another purpose |

These are observations, not permanent badges or CEFR levels. Repeating a supplied answer does not prove independent retrieval. A natural spontaneous response may count when the source establishes no supplied answer. A delayed independent use is stronger evidence than immediate repetition; record timing and support in `note`.

这些是有日期的观察，不是永久掌握证明。跟读不等于脱稿，曾脱稿不等于一直会。判断有无独立使用时写清提示和延时情况。

Agent selects at most the saved `review_limit` of relevant due items. Default to 1–2 and weave them into the conversation. Do not read the whole overdue queue or force a quiz at the start. Respect the user's chosen topic. Offer a short model only when needed; if the learner struggles, add support and simplify. No mandatory repetition count.

Suggested initial intervals: collected/full text → next session (around 1 day); keywords → around 3 days; independent → around 7 days; transfer → around 14 days. These are practical defaults, not a validated personalized algorithm. Failure brings the item closer; repeated success in the same minute does not lengthen it. A conversation may close without new scored attempts.

默认间隔是实用起点，不是已验证的个性化算法。提示依赖高则下次再聊，关键词约 3 天，脱稿约 7 天，迁移约 14 天；本分钟反复成功不单独延长间隔。用户没有产生新测评证据时照样可以结束并保存课次。

For requested weekly reflection, compare dated records: less support, clearer meaning, or use in another situation. Quote short selected examples with session links; distinguish observation from interpretation. Never infer improvement merely from more sessions, more words or streak length. Store only actual review evidence using the session format if the user practices; a generated summary is not a practice attempt.
