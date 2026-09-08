v0.2.2 — English-only practice and open questions / 全英文口语与开放提问

- Every coaching response during practice stays in English, including explanations and confirmations after non-English input.
- The coach asks open questions without answer choices and waits for the learner to formulate an answer.
- Meaning checks resolve once; clear pause and stop requests are acknowledged in English and followed immediately.
- Useful English structure errors still receive the selected correction style. No answer menus does not mean no wording help.
- Chinese page translations, written model meanings and bilingual installation instructions remain available. Private learning records and saved preferences are unchanged.
- The standalone runtime and Skill instructions use the same coaching policy; existing learning records remain compatible.

练习对话全英文，用开放问题引导用户自己组织表达；需要时保留纠错与说法帮助。网页中文翻译和书面复盘继续保留，暂停、结束立即执行。

Standalone local companion

v0.2.1 also preserves literal `#`, `%` and other supported filename characters in a chosen learning directory. v0.2.0 is superseded and should not be used for custom paths containing URI syntax.

- No Python, Node.js or Go installation is needed to use the Skill. The Agent downloads the pinned, checksum-verified program for the user's OS and CPU.
- Source transcripts, translation and written reviews run independently. A translation outage preserves new English and offers retry.
- Existing selected Markdown/JSON learning records and SQLite caption caches remain compatible. Backup/restore retains original sources and detaches machine-specific work.
- Full reviews retain source checks, per-turn word assessment, optional reading guidance and early provisional expression previews.
- Runtime/platform tests cover macOS, Windows and Linux; six release targets build without cgo. Native Voice behavior and availability still depend on the host and the user's account.

Binaries include Go and SQLite. macOS executables are not Developer ID notarized; Windows executables are not Authenticode signed. System execution prompts, if shown, require the user's normal OS approval; the Skill does not bypass them.
