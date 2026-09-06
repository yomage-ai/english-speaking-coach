# Voice and page delivery / 语音与页面交付

Read this once for the active Voice host. The responding Agent owns every message it produces. A separate speech model may speak or paraphrase those messages and may handle turns without delegating. The companion reads transcripts for display; it does not generate or control dialogue audio.

## Keep the spoken language stable

Use the conversation rules at the top of `SKILL.md` for all speech-facing messages. With English-first practice, preparation updates and coaching feedback are English too. Only the complete scene introduction uses the saved help language; an explicit Chinese explanation is brief. Chinese wording in the learner's turn does not change the response language. Technical diagnostics and the written review belong on the host's actual visible text surface.

For the initial preparation, a brief result can describe the restored preference naturally: “Your practice is set to English conversation, with a written review afterward.” Do not read out files, tool names or a setup checklist. After the complete Chinese scene introduction, a learner-facing “Let's talk in English” and the English role line establish the conversation boundary. These are ordinary words addressed to the learner, not commands to another model.

For a host requiring a `[STATUS]` item for each delegation, use a short English fact grounded in the current meaning. The `[COMPLETE]` item supplies the useful response. Neither should grade the learner, announce a lesson or add a second main question. Do not emit these tags on a host that does not require them.

| Situation | Required STATUS, when applicable | Completed response example |
| --- | --- | --- |
| A missing word in a request | “You're asking about the return time.” | “You can ask, ‘When should I return it?’” Then wait. |
| An already clear preference | “You prefer a quiet place.” | “There's a small garden nearby. What would you like to know about it?” |
| A complaint about repetition | “Your meaning was clear already.” | “You're right. I kept asking you to repeat.” Stop assigning practice in that turn. |

If no interim item is required, an ordinary short turn needs no progress narration. Adapt the examples to the actual intent and saved correction mode.

## Reply and configuration are separate

`context.voice_brief` is a short local reminder for the responding Agent. Read and act on it; do not paste it into an ordinary reply as instructions to another model. A host may have a documented, permitted instruction interface, but ordinary backend messages are not that interface. Never simulate roles or disguise prompts to bypass host rules.

Before completing a prepared reply, check the latest learner input. If they interrupted with a pause, refusal or coaching feedback, drop the pending exercise and address that intent. Do not append an older full model after a newer correction.

Use the permitted conversational path when a learner turn is delegated. A missing configuration interface does not prevent a helpful reply. If the actual spoken reply departs from the compliant backend reply, record both with the exact utterance and time. Correct the next delegated response naturally; do not repeatedly lecture the learner about host limitations. Assess turns handled without a backend call separately. No callback, exact repetition or language guarantee is implied by a correct local reminder.

语音端可能改述后台文字，也可能自行接话。Agent 先把自己的全部回复写对，再按实际转写核对交付；字幕就绪、后台英文和真正说出的英文分别取证。

<a id="page-delivery"></a>
## Show the correct page

1. Automatically open the prepared exact live URL for each new Voice. An explicit caption disable opens the overview instead; text practice also opens the overview. At closeout, open the exact matching review route.
2. Inspect after opening. A capture before opening, HTTP 200, promoted tool item or `queued` response is not visible-page evidence.
3. If queued or wrong, use one available permitted recovery route: reuse/navigate a visible tab or the host's required browser executor. Follow its routing rules and recheck the exact run or saved lesson. Do not repeatedly submit the same queued open.
4. If still unavailable, retain the unresolved display status and provide the usable link plus the specific issue on the written surface. Preserve the review even if the page cannot be shown.

The waiting review page checks saved records about once per second while visible, for at most five minutes. It does not create a lesson. After saving, verify this Voice's lesson is visible. If the learner navigated elsewhere, do not repeatedly pull them back.

## After the microphone closes

Honor the end tool's timing and response contract. Do not delay hanging up to write a review. Where the host supplies an end/tail callback, reconcile the ended Voice immediately through `review-context --with-transcript`, then save and show the selected review on the written/tool surface. Ending audio does not finish those actions. Reuse matching saved or pending selections; do not create a second lesson from a repeated tail.

If the host forbids further work in that execution, mark the exact unfinished closeout for [record-recovery.md](record-recovery.md). Do not call an acknowledgement a saved review. Use the host's documented inline display mechanism when written content is required; ordinary backend output may be spoken and does not prove text was shown.

For a Codex host that specifies the bare inline Markdown directive, the exact output form is:

```text
::codex-realtime-inline{}
The written review goes here as ordinary Markdown.
```

The directive starts at byte zero. Put the content after the newline, never inside a guessed `content` attribute, and do not prefix it with STATUS or COMPLETE. This example applies only when that documented host contract is present. If the host contract is unavailable, report the display step as unresolved instead of inventing syntax.

For caption preparation and drain errors, use [live-companion.md](live-companion.md). Caption translation and learning-record selection finish independently.
