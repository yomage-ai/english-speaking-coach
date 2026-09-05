# Storage and bundled archive / 数据位置与内置档案

The skill owns the tools and templates; the learner owns the records. The HTML viewer is bundled in `assets/library`, served by `scripts/library_server.py`. No learner profile, dialogue, transcript, concept evidence, local machine configuration or recovery archive belongs in a published skill package.

Skill 提供程序和规范，用户拥有学习档案。网页、样式、脚本随 Skill 分发，数据由真实练习生成。不要打包、上传或提交 `data/` 和本机配置；`.gitignore` 是辅助措施，压缩包或其他分发方式仍需 Agent 检查。

## Resolve one root / 唯一读取位置

Agent runs `practice_store.py paths` or `workspace_config.py show`:

1. Explicit `--root` or backward-compatible `--vault` for a one-off operation.
2. Saved `workspace.json` under `$CODEX_HOME/english-speaking-coach` (default `~/.codex/english-speaking-coach`).
3. For a new learner, `<installed-skill>/data`.

配置文件只保存数据路径和可选项目页，不存课程内容。不同窗口先读取同一配置；配置路径不可用时先恢复或重新连接，不另起一份空档案。新用户不需要理解目录结构，也不需要先装 Obsidian；Agent 运行 `init` 完成初始化。

`Sessions`, `Evidence`, `Archive`, `Pending` and `profile.json` live in the data root. `state.json`, `INDEX.md` and the legacy `dashboard.html` are rebuildable. The newer archive reads source files directly through a local API. Browsing, flipping cards and opening explanations never count as an ability attempt.

## Custom location and migration / 自定义与迁移

The user can name a local folder or an Obsidian vault subfolder. Obsidian is optional, not a second data source. Agent inspects destination rules and verifies access, then runs:

```sh
python3 <skill>/scripts/workspace_config.py configure --data-root <dedicated-folder> --copy-existing
```

The script refuses nonempty destinations, nested source/destination paths and unavailable configured sources. It copies and checks the source, then updates the single current path; the original folder remains. Pointing to the same current location needs no copy flag. Use `--project-page` only for an actual relevant project entry.

迁移成功后 Agent 关闭自己管理的旧档案服务、为新数据位置启动服务并验证显示的真实路径。不得按端口杀进程，不得让两份数据都继续被当成当前档案。

## Updates, uninstall and recovery / 更新、卸载与恢复

The requested default `<skill>/data` is portable but sits inside a replaceable program directory. After a successful CLI write, skill-internal data is also atomically backed up to `$CODEX_HOME/english-speaking-coach/backups/latest.zip` outside the skill. This is a latest recovery copy, not automatic cloud synchronization or unlimited backup history. Custom paths use the owner's existing backup strategy; this skill does not silently copy an external knowledge base elsewhere.

Agent 更新或卸载前检查实际数据路径和备份：数据在 Skill 内时，先把数据独立复制、校验，再替换程序文件，绝不能删除私人 data。第三方安装器、用户手动删除整个 `.codex` 或磁盘损坏不受此脚本保护。恢复时检查备份，Agent 负责解包与校验；不要悄悄用一个空 data 代替丢失记录。

## Open the actual archive / 打开实际页面

```sh
python3 <skill>/scripts/open_library.py --no-browser
python3 <skill>/scripts/open_library.py --session <saved-session-id> --no-browser
python3 <skill>/scripts/open_library.py --page stats --no-browser
```

The opener resolves the root, validates the requested saved session and uses the existing local-service-manager when installed. Agent loads that manager's instructions before service operations, verifies the returned URL and opens it in the host UI. Without `--no-browser`, the script requests the system browser. It never claims the browser visibly opened merely from that request.

On macOS without this manager, `open_library.py` uses the bundled `library_service.py` launchd manager for the current login session. It checks job identity, PID, loopback socket ownership and the archive API, preserves occupied ports and reuses healthy instances. It does not install login startup or compete with an existing manager. Its `status|stop --root <data-root>` operations identify this exact archive.

On Linux/Windows without an existing manager, the helper returns `needs_host_supervisor` and a server command. Agent uses the host's existing systemd user service or Windows Task Scheduler arrangement, verifies the actual process and listener, and calls `open_library.py --service-url http://127.0.0.1:<actual-port>`. The helper checks archive identity and data readability. Native Linux/Windows desktop supervision is not yet verified on real devices. Agent handles this work, not the learner. Python 3 is needed; Agent checks the runtime. There is no public website, account, remote hosting, cloud database, or paid dependency. Listen only on loopback and serve the allowed assets and APIs.

## Voice records / Voice 沉淀

Default to selected learning utterances, explanations, prompt conditions and source identifiers. Do not store an entire private conversation or background speech by default. Raw audio is stored only when the user requests it and the host actually makes the file available. No background recording, guaranteed session-end callback or cross-device memory is installed. When a real host end signal or explicit learner stop is observed, Agent saves, validates and opens the session page. If tools or source material are unavailable, preserve the real limitation and recover only available evidence later.

## Optional note metadata / 可选笔记元数据

Generic records use `type: english-practice` and private sensitivity. If the selected knowledge base requires project IDs, candidate status or domains, Agent reads its rules and supplies `record_metadata` on that session or historical supplement. Allowed keys: `type`, `status`, `primary_project`, `related_projects`, `domains`, `sensitivity`. Values are strings or lists of strings. IDs, dates and source identifiers cannot be overridden. Existing saved notes remain unchanged.

旧版目录迁移通过明确的 `--root` 或兼容 `--vault` 输入进行；不扫描其他用户的个人知识库路径。已有机器配置继续生效。
