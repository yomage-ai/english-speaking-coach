# Codex plugin installation / Codex 插件安装

The Agent performs this workflow. The learner supplies the installation/practice request, not shell commands, runtime setup or a directory choice. Use their current language. Keep an existing authoritative learning directory and its preferences intact.

## Install the released bundle

1. Inspect the repository's current `runtime-version.txt` and matching GitHub release. Download `english-speaking-coach_<version>_plugin.zip` and `SHA256SUMS` from that exact release; verify the archive hash before extraction. Do not use a source ZIP as the ready-to-run plugin.
2. The archive contains an `english-speaking-coach/` plugin root, `.codex-plugin/plugin.json`, `package-manifest.json`, and `skills/english-speaking-coach/`. Validate the package manifest's per-file hashes. It includes six Go programs (macOS, Windows, Linux; Intel/x64 and ARM64), their hash receipts and licenses. There is no Python or Node installation step. Go source and legacy Python remain in the development repository, outside the installed plugin.
3. Add the verified plugin to the user's personal local marketplace using the available plugin-creator workflow. Its standard source is `~/plugins/english-speaking-coach`; preserve other marketplace entries. Install with the host's `codex plugin add english-speaking-coach@<validated-marketplace-name>`. Do not publish to the universal directory or add unrequested hooks/MCP connections.
4. Confirm the plugin is enabled and its skill is discoverable through the host's plugin/skill listing. New plugins are picked up in a new task; do not claim the current task has reloaded its tools. Run the bundled `scripts/coach version` and `doctor` with the actual installed skill root. Initialization and native service setup belong to the Agent. First-use `prepare` only binds a verified active Voice; installation itself must not fabricate one or call the microphone.

An installed plugin is a package, not built-in Voice. It retains a Go backend. Codex/OS approval policies still apply to local file access and execution. Reusing an existing Node runtime could avoid distributing a business executable, but a Node port does not inherently remove those permissions or improve model translation. Do not promise universal third-party access to a bundled Node without a verified host contract.

## Update without losing the working archive

Prepare and validate the new release before switching. Read the current service identity, its manager and active Voice/review state. Reuse the existing manager; update its exact program path only after idle work is verified. Keep a restorable copy of the old installation. If a legacy `~/.codex/skills/english-speaking-coach` entry is required by a local routing rule, preserve that path as a compatibility link to the installed plugin skill and check discovery for duplicates. Do not copy learning files into a plugin cache.

After installing, compare package hashes, runtime version/revision and the running service identity. Check both page and API health. Keep remote source, formal release, marketplace source and installed package aligned. No force-push, security bypass, global model change or website deployment is part of installation.

中文：使用正式插件包完成安装，包内已带各平台程序；Agent 校验、登记插件、检查学习档案并启动后台。用户只在真正需要时处理登录、麦克风或系统批准，不读安装教程、不安装开发环境。更新时保留原数据和现有服务管理器，核对远程发布与实际安装版本。它是插件封装 Go 后台，不是 Codex 原生 Voice 或 Node 迁移。
