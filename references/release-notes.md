# v0.2.9 — Ready-to-run Codex plugin / 开箱即用的 Codex 插件

- 新增正式 Codex 插件安装包，包含 Skill 和 macOS、Windows、Linux 各支持架构的程序；首次练习无需再次下载后台，也无需用户安装语言环境。
- 插件包提供逐文件校验清单，Windows 启动入口也会核对已有程序的 SHA-256。
- 更新中英文安装说明：Agent 完成安装、启动和更新；用户只在真实需要时处理登录或系统批准。

This release adds a Codex plugin bundle containing the Skill and prebuilt programs for all six supported desktop OS/architecture targets. First practice needs no extra backend download or user-installed language runtime. The bundle includes per-file checksums, and the Windows launcher now verifies cached executable receipts. Bilingual instructions keep installation and service management with the Agent.

The backend remains Go. This packaging update retains the existing bilingual caption, independent review and system-reading behavior; it does not claim a Node migration, native Voice integration or improved model translation speed.
