Tell Codex: “Install this skill from https://github.com/yomage-ai/english-speaking-coach and practice English with me for ten minutes. Choose a fresh scene, briefly introduce it in my help language, then begin the English dialogue. Save a written review afterward and open my learning archive.”

Once installed, try “Start a fresh speaking practice,” “Open my flashcards and hide the answers,” or “Show me expressions I can now use independently.” [简体中文说明](README.md)

# English Speaking Coach

Start one independent scene from the beginning, with a short introduction of the setting, both roles and your goal, then practice in English. History informs ability and variety; old plots are never continued. Written review is the default after the scene; focused spoken review remains available on request. A local journal, flip cards and progress records support continued practice; vocabulary and grammar serve communication.

## Use it in your own words

- “Help me practice introducing myself for a job interview.”
- “I'm traveling abroad. Let's practice asking a hotel receptionist for information.”
- “I have two minutes. Open the vocabulary cards and let me guess the meanings first.”
- “Use my learning history to choose a different scene and start from the beginning. Help me in Chinese when I need it.”
- “Open the bilingual companion. Let us speak English, with Chinese translations on the page.”
- “Be the shop assistant. Talk naturally with me first, then review after the scene.”
- “Review what I just said, explain it in Chinese, then guide me through another attempt.”

Provide only the topic, goal, or review request. The agent handles installation checks, initialization, context recovery, saving, verification, and opening the viewer. You do not fill out a questionnaire, choose a scene menu or open the page manually; when the companion is enabled, the Agent opens and inspects it before dialogue.

New learners default to content responses during scenes, natural clarification when meaning is unclear, and minimal help when explicitly requested. Understandable sentences do not trigger routine rewrites or repetition. Written review separates misunderstandings, unnatural wording and optional alternatives. Requested spoken review can include useful explanations, demonstrations and guided attempts. If you say you are done for today or say goodbye, the AI ends promptly, leaves review in the journal, and saves further practice for another time. Existing explicit correction preferences remain supported.

If you want English wording during the scene, ask for natural in-character support: the agent saves that preference, uses short meaning checks or recasts, offers keywords or an example when needed, and invites needs, reasons and details. It avoids constant menus, grammar lectures, compulsory repetition and endless pretend confusion. Existing explicit preferences stay intact.

Routine startup reads preferences and the project page together, then returns only the context needed for preparation instead of repeatedly loading the whole archive. At the end, the agent opens this Voice's review page first; it automatically displays the actual quotes, suggestions and observations after the review is saved. It matches the exact Voice, never a previous lesson. The page checks local save status without extra model calls; the agent still selects evidence and validates the review.

These are the skill's practice behavior targets. A separate Voice model also depends on the host's permitted instruction interface; loading the skill, saving preferences or delivering the opening does not establish that Voice adopted its rules. If the host prohibits relaying model instructions, the agent reports that limitation instead of asking you to repeatedly test the same unavailable route. See [the handoff boundary](references/live-companion.md#handoff-boundary).

## Your learning archive

| View | Purpose |
| --- | --- |
| Bilingual companion (optional) | Both Voice speakers’ English and Chinese, with on-demand Chinese and review |
| Overview | Latest practice, topic notebooks, and quick review |
| Conversations | Selected wording, suggested expressions, summaries, and next steps |
| Words and expressions | Reversible cards: Chinese to English, English to Chinese, or bilingual reading |
| Reflection | Period activity, at most three expression summaries, and a small review suggestion |
| Expression progress | Search and filters, 20 items per page; individual histories have month filters and 10 events per page |

Period summaries use observations from that period and earlier, never later success. First observations are distinguished from improvements with a known baseline. Meaning, spoken reading, and independent use are tracked separately. Card flips are not mastery evidence. Success across days and contexts can support “more stable expression”; this is a product convention, not an exam score or proof of permanent mastery.

## Your data stays yours

The viewer ships with the skill; learning data is created by actual practice.

- New learners default to `<skill>/data`. Existing machine configuration takes priority; a new window does not create a second archive.
- Ask the agent to move records to a dedicated knowledge-base or Obsidian subfolder. It copies and verifies before switching, retaining the original.
- Source records are Markdown. Indexes and views are rebuildable. Obsidian is optional.
- Writes to embedded data produce one latest recovery copy outside the skill. The agent still preserves data before updates or removal. This is neither cloud sync nor complete backup history.
- Recovery across windows requires access to the same local configuration and records. Moving to another computer requires data migration and path configuration.

Learner records, machine configuration, backups, recordings, and private screenshots are excluded from this repository. Tests use explicitly synthetic samples.

## Environment and boundaries

Python 3.10+ and its standard library are required, with no external database or Node runtime dependency. The optional bilingual companion needs Python 3.11+, a Codex CLI supporting app-server, and the existing ChatGPT login. It uses account quota without a new API key. The agent checks the environment.

Fresh initialization, saving, recovery in a new process, local browsing, and the bundled launchd fallback have been verified on macOS without an additional service-manager skill. An existing host manager takes priority. The fallback lasts for the current login session and does not add login startup. Cross-platform CI checks storage and views on Linux and Windows; the agent uses the host's native supervisor for persistent serving there. Native desktop and Voice workflows on those platforms have not been tested on real devices.

Skill instructions and usage documentation support Simplified Chinese and English and follow the user's language. Viewer navigation is currently primarily Chinese, with English learning content.

Voice persistence requires transcripts, an observable end signal, and tool access from the host. Only learning-related excerpts are saved by default; there is no background recording. Reading judgments require actual accessible audio. Otherwise only observable meaning/use evidence is recorded. The skill cannot guarantee an automatic end callback in every Voice host.

## Bilingual companion boundaries

Speak through the existing Codex Voice interface. The fixed local page shows English first, then Chinese. The agent binds only the current practice task and Voice session; no per-sentence forwarding is required and idle time starts no model turns. The default translator is GPT-5.6 Luna with low reasoning, checked against the logged-in model list. It never silently switches models or purchases services.

Temporary transcripts and translations are stored in `Live/` inside the learning folder, separately from selected lessons and mastery evidence. The page shows up to 40 utterances at a time and supports recent-session review. Starting a new companion removes caches older than seven days. Say “Stop using the bilingual companion” and the agent disables future automatic activation.

Each Voice needs a fresh agent binding, including consecutive Voices in one task. If the host provides no execution opportunity, live captions may be missed. Say “Recover the bilingual conversation that just ended” and the agent verifies and translates the closed session; the page labels it as after-Voice recovery. This leaves another active run alone and does not count as live coverage. English examples quoted inside Chinese teaching text receive their own Chinese meaning.

The agent uses one preparation entry for context recovery, binding and backend checks, then opens and inspects the actual page. Backend readiness, page visibility and observed transcripts are separate results; generating a brief does not prove Voice received it. Skipping available preparation tools is an execution omission, not a missing host callback.

Incremental reading and actual Codex translation requests have been verified. **Transcript flush delay during Voice, end-to-end latency and missing utterances still require an actual Voice trial**; completed logs do not establish those properties. Skill instructions cannot guarantee that a host always loads them or provides an end callback. The agent reports actual readiness, waiting, end and error states. See [bilingual companion implementation and recovery](references/live-companion.md).

## Maintenance and acknowledgement

See [references](references/) for agent-facing details. Maintainers can run `python3 -m unittest discover -s tests -v`; ordinary learners do not need to run commands.

[MIT License](LICENSE)
