English-only practice and open questions

- Every coaching response during practice stays in English, including explanations and confirmations after non-English input.
- The coach asks open questions without answer choices and waits for the learner to formulate an answer.
- Meaning checks resolve once; clear pause and stop requests are acknowledged in English and followed immediately.
- The standalone runtime and Skill instructions use the same coaching policy; existing learning records remain compatible.

Standalone local companion

- No Python, Node.js or Go installation is needed to use the Skill. The Agent downloads the pinned, checksum-verified program for the user's OS and CPU.
- Source transcripts, translation and written reviews run independently. A translation outage preserves new English and offers retry.
- Existing selected Markdown/JSON learning records and SQLite caption caches remain compatible. Backup/restore retains original sources and detaches machine-specific work.
- Full reviews retain source checks, per-turn word assessment, optional reading guidance and early provisional expression previews.
- Runtime/platform tests cover macOS, Windows and Linux; six release targets build without cgo. Native Voice behavior and availability still depend on the host and the user's account.

Binaries include Go and SQLite. macOS executables are not Developer ID notarized; Windows executables are not Authenticode signed. System execution prompts, if shown, require the user's normal OS approval; the Skill does not bypass them.
