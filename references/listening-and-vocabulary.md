# Listening, speaking and word load / 听说与生词负担

Keep the topic worthwhile while making each turn manageable. A learner can discuss a real preference, constraint or concern with familiar words. Topic interest is not evidence of vocabulary knowledge, and a successful short answer is not permission to add a long explanation.

保留用户感兴趣的真实问题，降低每次需要处理的语言量。听力理解、组织表达和词汇知识分别观察；不要从目的地、职业或一次流利复述判断等级。

## Prepare a small foothold / 少量铺垫

Read the dated `learning_context` from startup; it retains recent `next_focus` and `coaching_notes`. Extract transferable support needs, not old plot instructions. More recent feedback and the current request take priority. No recorded evidence for a word means unknown familiarity, not proven ignorance. A word used in a supplied sentence is not automatically available for independent use.

An explicit ongoing request for shorter turns can be saved as `input_support: short_turns` through the normal preference writer. Default/legacy `adaptive` uses current evidence. This preference selects delivery support, not a permanent ability label; preserve the learner's interests, correction and language settings. With `short_turns`, proactively offer one or two useful scene phrases before the role opening unless the learner declines or available evidence shows that preparation is unnecessary. Keep it optional for the learner, without a recitation gate. A single hesitation does not authorize a permanent preference change.

用户明确希望以后用短轮次、逐渐引入词汇时，可保存 `input_support: short_turns`；默认 `adaptive` 按现场证据调整。该偏好不是固定英语等级，也不意味着只问基础寒暄。

Choose one meaningful task and predict only the language needed for its first few turns. Optional scene `key_terms` contains up to three candidates with `term`, `meaning` and a short `example`. This is a temporary preparation plan, not a record of learning. Omit an unnecessary rare term by saying it more simply; do not teach every term the character could possibly use.

When vocabulary support is useful, briefly preview one or two items within the help-language scene introduction: say the English phrase and its concise meaning. With an English help language, give an easy English meaning. Do not read all examples or an itinerary. Then begin with one easy role line and listen. If the learner already knows an item, skip it. A third useful item can wait until it becomes relevant. The learner does not need to pass a vocabulary test to enter the scene.

场景已确定后，Agent 先判断接下来几轮真正需要哪些表达。开场只带一两个可能有用的词组，例如订房情景中的 `late checkout`（延迟退房），再让用户开口。不是先发一张大词表，也不把预测出来的所有词自动当成生词入库。中文说明放在开场铺垫中；角色对话仍保持英语。

## Make each exchange usable / 每次只处理一点

For a learner currently needing support, aim for 1–2 short sentences, about 10–20 words total, one new piece of information and at most one likely unfamiliar item. A turn longer than about 25 words is a cue to cut or defer detail. Count any spoken acknowledgement, explanation, model and follow-up together. This is a starting heuristic: a fluent learner or an explicit request for detail can justify more. Never cut off an essential qualification just to hit a count.

Use frequent concrete language, direct syntax and consistent names. Prefer “How long?” to a new abstract noun when the latter is not the learning target. Explain a whole requested phrase, not just its easiest component; use simpler words or a concrete example instead of repeating the unknown term. If the explanation still fails, simplify again; use a brief help-language explanation when the learner explicitly asks. Do not introduce several synonyms in one explanation.

Answer the actual question with the smallest complete useful answer. Two questions from the learner can receive two very short answers without an extra question. Defer optional lists and background. In roleplay, do not invent absolute guarantees about safety, health or other uncertain real-world outcomes. A simple qualification can remain short.

Avoid asking “Do you understand?” after every line. A meaningful response often shows enough comprehension to proceed. Alternate naturally between short input and learner output: offer a fact they can use, wait for their choice or question, then let them add a reason or detail. Choice questions can help when stuck, but should not become the only conversation. Do not supply both sides of the dialogue.

A brief fictional example; each partner line is followed by a real learner turn:

- Partner: “You can keep the room until two. What time is your flight?”
- Learner: “At six. Can I leave my bag here?”
- Partner: “Yes, we can keep your bag. What will you do this afternoon?”

The learner listens for a useful detail and asks their own question; no recitation is required. Keep captions available as chosen. Looking at Chinese support is not a failure, but it does not prove unaided listening. Do not hide captions, change their defaults, or claim audio speed was adjusted unless the actual host supports and verifies that action. The Agent can still choose shorter chunks and natural pauses.

听和说在小轮次里交替：听到一个有用信息，表达自己的选择，再逐渐增加原因、限制或追问。不要先讲一段长听力，再连续考试；不要因用户回答简短就代替他讲完所有内容。生词、句式、信息数量，每次只增加其中一个难点。

## Respond to overload immediately / 当轮减负

Explicit “too hard”, “too many words” or repeated word-meaning trouble is a reason to reduce input now. Normal hesitation alone does not diagnose poor listening. For coaching feedback, acknowledge in one short sentence and wait: “You're right. I'll keep it shorter.” Do not follow the acknowledgement with another lesson or menu. An explicit request to repeat or simplify gets that short repair directly.

When the learner chooses to continue, use one very short concrete point and no new target vocabulary until the current problem clears. After several meaningful responses without help, tentatively add one small challenge. Do not use an invented comprehension percentage or a single “yes” as a promotion threshold. Record persistent support needs for the next scene, without treating a difficult coach reply as a learner deficit.

## Preserve useful words without flooding the deck / 生词沉淀

During the conversation retain a small encounter list in task context: term and sense, actual quote, whether the learner asked, which help was supplied, and whether understanding or use was observed. Explicitly requested words take priority over the Agent's predicted vocabulary. A displayed gloss or successful repeat is supported exposure, not independent knowledge. Match existing concept IDs by sense rather than spelling alone.

At closeout inspect this list as well as sentence corrections. A starting collection target is 2–3 useful items total across new word and expression cards, reduced when review is already difficult; it is not a quota or a cap on saving explicitly requested items. A zero-card session is valid. Keep additional unresolved needs in the written notes for later selection rather than dumping every uncommon word into the deck. Existing `review_limit` still controls the combined natural review workload.

Save an actual word-help encounter with `concept_observations`; the existing archive includes these in the flashcards even without an expression. Use `needs_help` when the difficulty remains unresolved, `explained` when an explanation was provided, and independent `success` only with appropriate learner evidence. A bad explanation must not become success. Save learner/coaching feedback in `coaching_notes`; neither becomes a permanent language level. For old completed sessions use the source-linked evidence supplement described in [concept-progress.md](concept-progress.md).

AI 预测的备用词、用户实际求助的词、得到解释的词、能独立用出的词要区分。闪卡保留具体意思、简短用法、来源与提示状态；下次在不同场景里自然再用。卡片翻面、看过中文和跟读成功都不等于已经掌握。
