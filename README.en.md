Copy this request to Codex to install:

> Install the English Speaking Coach plugin from https://github.com/yomage-ai/english-speaking-coach and complete the initial setup.

[简体中文](README.md)

# English Speaking Coach

Practice English in travel, restaurant, interview and other everyday situations. Afterward, review useful expressions, flashcards and your progress. Tell Codex what you want to practice; it handles preparation and saves your records.

Practice dialogue stays in English. For non-English or mixed input, the coach helps check the meaning in English. Open questions invite your own answers, without supplied choices; wording help remains available when needed. The page keeps Chinese translations and written reviews.

## Get started

After installation, open Voice, then send this message to start practicing English:

> /$english-speaking-coach Help me practice English. Reply only in English during practice, even when I use Chinese; keep Chinese help on the page.

You can also select **English Speaking Coach** from the skill picker and send it with the same practice request. Use a newly installed plugin in a new task. An ordinary text task starts text practice; live bilingual captions require an active Voice call.

For troubleshooting, ask directly, for example: “Check why the bilingual page has no translations.” Codex pauses practice, handles the issue in your current language and resumes practice when you ask.

Each practice starts with a brief introduction to the setting, both roles and your goal, then begins the dialogue. The AI helps you form useful expressions according to your chosen correction style and guides the next step, with opportunities to explain needs, give reasons and ask questions. New practices use your learning history to choose a fresh scene.

## Pages you can use

Codex automatically opens the local learning page at the start of every practice and shows your session review afterward. The page includes:

| Page | What you can do |
| --- | --- |
| Bilingual companion | Follow both speakers' original transcript and Chinese translations, without a predicted next-reply card |
| Session review | Distinguish actual practice from suggestions for later; find the review again after switching pages |
| Learning home / Review | Start the next activity on Home; inspect changes over time in Review |
| Local learning data | Open the folder, download a full backup, restore a backup or use another copied archive |
| Flashcards | Recall before flipping; expand grouping, stress, intonation and memory tips |

The official plugin bundle includes programs for all supported platforms. Codex verifies, selects and starts the matching program; first practice needs no additional backend download. **No Python, Node.js or Go installation or manual program startup is required.** Older standalone Skill installations still let Codex fetch the matching program automatically. Desktop support and limits are described below.

The Web library no longer exposes browser system speech. Real-device checks found that Web Speech could report completion without audibly finishing, while voice quality and completion could not be guaranteed across browsers and systems. The page keeps complete English, Chinese meaning and written reading guidance. Flipping cards or reading along does not create practice evidence or change mastery. This release does not add Web recording, speech recognition or a new practice log.

## Before you use it

- Use Codex on macOS, Windows or Linux with skill installation and local file access. Live bilingual captions additionally require the host to expose both sides of the transcript during a call; ordinary web chat and mobile apps do not automatically have this capability.
- The bilingual companion and independent session reviews use your existing ChatGPT login and account quota, without a separate API key. Caption availability depends on the Voice transcript.
- You only handle Codex login, Voice microphone permission or a system-required execution/file-access approval when actually needed. The plugin does not bypass system restrictions; Codex explains the specific need without asking you to install a development environment.
- Learning records are separate from the Skill program. New users automatically start in `~/.codex/english-speaking-coach/data`, outside the Skill; installation does not require choosing a folder. Use “Open learning folder” to view the data. On a new computer, restore a backup or use the copied learning folder; Codex can handle this for you, and the old folder is retained. AI conversation and translation still use the connected model services; the bilingual companion temporarily keeps recent transcripts and translations.

The local service generates reviews independently, so leaving the current chat does not interrupt them. The page first shows source-checked expression suggestions, then completes and saves the full review. The model now returns only semantic judgments; the program derives and validates exhaustive per-turn coverage and word bookkeeping, avoiding long mechanical output that previously pushed longer reviews into the timeout. Failures preserve their source and can be retried. Model generation still has no fixed-time guarantee.

If translation disconnects, new original text still appears; the page explains the failure and offers retry. A healthy backend does not prove that the host exposes live transcripts, so Codex checks these separately.

Native Voice can respond autonomously or paraphrase the Agent’s English. The Skill therefore cannot guarantee that Voice always speaks English or handles pauses correctly; captions cannot control speech either. This is a current host limitation.

## License

Source is publicly available. Personal noncommercial learning is free; selling the software, paid services, commercial product integration, employer-provided training and other commercial uses require a separate written license. Independent personal interview preparation or learning work-related English remains free. [Full license](LICENSE) · [Commercial licensing contact](https://github.com/yomage-ai/english-speaking-coach/issues)

The new license is supplied from v0.2.10 onward. It does not revoke MIT rights in v0.2.9 and earlier releases or previously MIT-licensed code. Third-party components retain their own licenses.
