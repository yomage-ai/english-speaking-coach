Standalone local companion / 独立本地伴随程序

- No Python, Node.js or Go installation is needed to use the Skill. The Agent downloads the pinned, checksum-verified program for the user's OS and CPU.
- Source transcripts, translation and written reviews run independently. A translation outage preserves new English and offers retry.
- Existing selected Markdown/JSON learning records and SQLite caption caches remain compatible. Backup/restore retains original sources and detaches machine-specific work.
- Full reviews retain source checks, per-turn word assessment, optional reading guidance and early provisional expression previews.
- Runtime/platform tests cover macOS, Windows and Linux; six release targets build without cgo. Native Voice behavior and availability still depend on the host and the user's account.

无需安装开发环境；Agent 自动准备。原文、翻译、复盘分别运行，原有学习档案继续使用。实时双语仍需要宿主提供双方转写，并使用用户现有 ChatGPT 登录及额度。

Binaries include Go and SQLite. macOS executables are not Developer ID notarized; Windows executables are not Authenticode signed. System execution prompts, if shown, require the user's normal OS approval; the Skill does not bypass them.
