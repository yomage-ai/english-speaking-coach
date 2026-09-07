Copy this request to Codex to install:

> Install english-speaking-coach from https://github.com/yomage-ai/english-speaking-coach, complete the initial setup, and confirm it appears in the skill list.

[简体中文](README.md)

# English Speaking Coach

Practice English in travel, restaurant, interview and other everyday situations. Afterward, review useful expressions, flashcards and your progress. Tell Codex what you want to practice; it handles preparation and saves your records.

## Get started

After installation, open Voice, then send this message to start practicing English:

> /$english-speaking-coach Help me practice English.

You can also select **English Speaking Coach** from the skill picker in the message box.

Each practice introduces the setting, both roles and your goal before the dialogue begins. The AI helps you form useful expressions according to your chosen correction style and guides the next step, with opportunities to explain needs, give reasons and ask questions. New practices use your learning history to choose a fresh scene.

## Pages you can use

Codex automatically opens the local learning page at the start of every practice and shows your session review afterward. The page includes:

| Page | What you can do |
| --- | --- |
| Bilingual companion | Follow the original transcript, Chinese translations and a current expression hint |
| Session review | Read expressions, suggestions and priorities; find the review again after switching pages |
| Learning home / Review | Start the next activity on Home; inspect changes over time in Review |
| Local learning data | Open the folder, download a full backup, restore a backup or use another copied archive |
| Flashcards | Recall before flipping; expand saved reading and memory tips when useful |

## Before you use it

- Use Codex with skill installation and local file access.
- The bilingual companion and independent session reviews use your existing ChatGPT login and account quota, without a separate API key. Caption availability depends on the Voice transcript.
- Learning records are separate from the Skill program. New users automatically start in `~/.codex/english-speaking-coach/data`, outside the Skill; installation does not require choosing a folder. Use “Open learning folder” to view the data. On a new computer, restore a backup or use the copied learning folder; Codex can handle this for you, and the old folder is retained. AI conversation and translation still use the connected model services; the bilingual companion temporarily keeps recent transcripts and translations.

The local service generates reviews independently, so leaving the current chat does not interrupt them. The page first shows source-checked expression suggestions, then completes and saves the full review; failures can be retried. Model generation still takes time; there is no fixed-time guarantee.

Native Voice can respond autonomously or paraphrase the Agent’s English. The Skill therefore cannot guarantee that Voice always speaks English or handles pauses correctly; captions cannot control speech either. This is a current host limitation.

[MIT License](LICENSE)
