# Voice and page delivery / 语音与页面交付

Read this for an unfamiliar host, a delivery mismatch, queued display recovery or its end/tail contract; ordinary setup uses the compact entry in SKILL.md. The responding Agent owns every message it produces. A separate speech model may speak or paraphrase those messages and may handle turns without delegating. The companion reads transcripts for display; it does not generate or control dialogue audio.

## Keep the spoken language stable

Use the conversation rules at the top of `SKILL.md` for all speech-facing messages. With English-first practice, preparation updates and coaching feedback are English too. Scene introductions are English too; the saved help language appears in the written scene card. A spoken Chinese explanation requires an explicit request. Chinese wording in the learner's turn does not change the response language. Technical diagnostics and the written review belong on the host's actual visible text surface.

For the initial preparation, a brief result can describe the restored preference naturally: “Your practice is set to English conversation, with a written review afterward.” Do not read out files, tool names or a setup checklist. After the short English scene introduction, a learner-facing “Let's talk in English” and the English role line establish the conversation boundary. These are ordinary words addressed to the learner, not commands to another model.

For a host requiring a `[STATUS]` item for each delegation, use a short English fact grounded in the current meaning. The `[COMPLETE]` item supplies the useful response. Neither should grade the learner, announce a lesson or add a second main question. Do not emit these tags on a host that does not require them.

| Situation | Required STATUS, when applicable | Completed response example |
| --- | --- | --- |
| A missing word in a request | “You're asking about the return time.” | “You can ask, ‘When should I return it?’” Then wait. |
| An already clear preference | “You prefer a quiet place.” | “There's a small garden nearby. What would you like to know about it?” |
| A complaint about repetition | “Your meaning was clear already.” | “You're right. I kept asking you to repeat.” Stop assigning practice in that turn. |

If no interim item is required, an ordinary short turn needs no progress narration. Adapt the examples to the actual intent and saved correction mode.

Apply the learner's input load to STATUS and COMPLETE together, including any required preparation acknowledgement. A short backend reply may be expanded by the speech model. Review the actual unique spoken reply for length, unfamiliar terms, lists and appended questions, not only the backend text. A learner-facing statement such as “We'll use short turns and learn a couple of useful phrases” can describe the real practice plan; it does not configure the frontend. A missing per-turn callback or speech configuration API remains a host limitation, not something extra prompt text or caption settings can enforce.

## Reply and configuration are separate

`context.voice_brief` is a short local reminder for the responding Agent. Read and act on it; do not paste it into an ordinary reply as instructions to another model. A host may have a documented, permitted instruction interface, but ordinary backend messages are not that interface. Never simulate roles or disguise prompts to bypass host rules.

Before completing a prepared reply, check the latest learner input. If they interrupted with a pause, refusal or coaching feedback, drop the pending exercise and address that intent. Do not append an older full model after a newer correction.

Use the permitted conversational path when a learner turn is delegated. A missing configuration interface does not prevent a helpful reply. If the actual spoken reply departs from the compliant backend reply, record both with the exact utterance and time. Correct the next delegated response naturally; do not repeatedly lecture the learner about host limitations. Assess turns handled without a backend call separately. No callback, exact repetition or language guarantee is implied by a correct local reminder.

语音端可能改述后台文字，也可能自行接话。Agent 先把自己的全部回复写对，再按实际转写核对交付；字幕就绪、后台英文和真正说出的英文分别取证。

<a id="page-delivery"></a>
## Show the correct page

1. Automatically open the prepared exact live URL for each new Voice. An explicit caption disable opens the overview instead; text practice also opens the overview. At closeout, open the exact matching review route.
2. Inspect after opening through the host-permitted browser route. Use the existing matching tab when available; do not navigate the whole app away from the current task. After Voice ends, the voice-only screen capture tool is unavailable; use the normal browser inspection tool. A capture before opening, HTTP 200, promoted tool item or `queued` response is not visible-page evidence.
3. If queued or wrong, use one available permitted recovery route: reuse/navigate a visible tab or the host's required browser executor. Follow its routing rules and recheck the exact run or saved lesson. Do not repeatedly submit the same queued open.
4. If still unavailable, retain the unresolved display status and provide the usable link plus the specific issue on the written surface. Preserve the review even if the page cannot be shown.

The review page shows real local-worker states: queued, reading, generating, checking, saving, saved or an actionable error. The worker owns generation even if the parent chat is busy or the page is hidden. `review-begin` queues/reuses one exact Voice; it does not return a second drafting task. Existing saved source IDs remain authoritative. See [review-worker.md](review-worker.md). The page tracks recent reviews and never labels a previous lesson as the active practice.

## After the microphone closes

Honor the end tool's timing and response contract. Do not delay hanging up to write a review. Where the host supplies an end/tail callback, reconcile the ended Voice immediately through `review-begin`, open the returned exact written review page, and let the registered local worker finish. Do not duplicate generation through finish-review. Ending audio does not finish those actions. Reuse matching saved or pending selections; do not create a second lesson from a repeated tail.

If the host forbids further work in that execution, mark the exact unfinished closeout for [record-recovery.md](record-recovery.md). Do not call an acknowledgement a saved review. Use the host's documented inline display mechanism when written content is required; ordinary backend output may be spoken and does not prove text was shown.

For a Codex host that specifies the bare inline Markdown directive, the exact output form is:

```text
::codex-realtime-inline{}
The written review goes here as ordinary Markdown.
```

The directive starts at byte zero. Put the content after the newline, never inside a guessed `content` attribute, and do not prefix it with STATUS or COMPLETE. This example applies only when that documented host contract is present. If the host contract is unavailable, report the display step as unresolved instead of inventing syntax.

For caption preparation and drain errors, use [live-companion.md](live-companion.md). Caption translation and learning-record selection finish independently.

## Startup latency / 开场延迟

Use the single preparation entry in `SKILL.md`. If the host also requires a knowledge or preference lookup, obey it but return the approved preferences and relevant learning facts compactly; do not dump an unrelated full index or reread every old lesson into startup. Complete nonessential maintenance after the practice/review delivery. Local readiness, Agent turn time, browser display and translation latency are separate measurements. Do not block first speech on the first transcript or Chinese translation. A queued display gets one permitted recovery, then an accurate visible link/status; avoid repeated opens and spoken diagnostics. Report `timing.local_preparation_ms` as local work only.

If no permitted API controls the speech model or delegates every learner turn, skill instructions cannot guarantee its autonomous replies. Do not inject configuration through a fake dialogue. Fix the delegated response itself, record the observed boundary, and assess actual spoken turns separately.

## Installed app-server capability checks / 桌面语音能力核对

A generated local app-server protocol exposes experimental thread-scoped realtime start, prompt, startup context and speech append fields. Field presence is not runtime support. Test an isolated own session, with no microphone and no playback, using the existing account before proposing it as a native-Voice fix. In the September 2026 validation, the installed app-server rejected both v2 text and v3 audio realtime startup under ChatGPT login with `realtime conversation requires API key auth`. No replacement voice client is shipped or claimed working on that basis. Do not change login, global feature flags or add a paid API dependency silently. Backend English and actual native speech remain separate acceptance checks.
