# Storage and local library / 存储与本地学习页

The Skill contains rules, generic examples, scripts and web assets. Personal learning facts live in the configured data root.

## Location / 位置

New users default to `~/.codex/english-speaking-coach/data` (or its CODEX_HOME equivalent). Agent initializes a pristine default on first preparation/text resume. Installation does not force a folder-choice dialog. Machine-only workspace.json in the parent folder records the active directory and optional project page.

Existing configuration wins. Missing configured storage never creates an empty replacement; the storage page remains reachable for restoration. The learner can keep the default, ask the Agent to change it, or use **本地学习数据** after practice and review finish.

## Authoritative files / 哪些是真正数据

| Files | Meaning |
| --- | --- |
| profile.json | Learning goal and adopted preferences |
| Sessions/*.md | Selected lesson evidence and expressions; speaking-record-v2 fact block |
| Evidence/*.md | Additional sourced word/concept observations |
| Archive/legacy-v1.md | Preserved legacy learning baseline |
| Pending/*.json | Recoverable unfinished selections |
| Runtime/scene-history.json | Recent scene choices, including unsaved starts |
| Runtime/Reviews | Durable review job metadata; not mastery evidence |
| Context/project-*.md, when imported | Portable copy of an associated project page |
| state.json, INDEX.md, dashboard.html | Derived views rebuilt from facts |
| Live/companion.sqlite3 | Recent bilingual transcript cache, SQLite; optional in backup |

Long-term memory is Markdown plus JSON, not the Live SQLite cache. Flipping cards does not change mastery. Codex's own logs, recordings, account/login and unrelated linked documents are outside this archive.

## Working backup and migration / 备份和迁移

After saving selected records in the managed default or legacy Skill-internal directory, the runtime updates `$CODEX_HOME/english-speaking-coach/backups/latest.zip` with a verified manifest. A failed recovery copy is reported separately from the saved original. Custom external directories retain their own backup policy. This local recovery copy is separate from the portable backup/migration controls below and is not an off-device backup.

The web page provides four actions:
- **下载完整备份 ZIP**: verified manifest, file hashes/counts, core files, custom notes, pending selections, scene history and the configured project-page text. Recent bilingual cache is opt-in and uses SQLite's consistent backup.
- **把当前档案复制到新目录，并使用新目录**: verify before switching, keep the source.
- **从备份 ZIP 恢复**: inspect, show counts/destination, restore into an empty dedicated directory, then activate.
- **使用已复制到本机的学习目录**: validate and adopt an existing archive, including when the old drive is missing. No archive merge.

No operation overwrites a nonempty destination or follows symlinks out of the archive. Files and canonical records are verified before configuration changes. Machine-side location-history receipts retain the previous configuration. Imported jobs never automatically call old-machine sources. Selected Pending material remains recoverable. Project-page text is included; unrelated attachments and Codex raw logs are not.

On a new computer, install the Skill, then restore the ZIP or ask Agent to adopt the copied directory. Agent handles setup, dependency and integrity checks. Copying only a web page, state.json or Live SQLite is not a complete migration.

## Agent tools / Agent 工具

`coach storage backup --file <new.zip> [--include-live]`, `inspect --file <zip>`, `restore --file <zip> --destination <empty-folder>`, `adopt --destination <existing-archive>`, and `move --destination <empty-folder>` are internal maintenance tools, not learner setup commands. Apply the same idle/ownership checks before CLI changes. `coach export` produces a reading snapshot, not a full backup.

## Service ownership / 服务归属

Normal installed use runs `coach serve --workspace` under the existing manager. Its service identity follows the machine workspace; the data root comes from workspace.json at each start. An idle instance can rebind after a verified page operation; restart still uses the new root.

Explicit `--root` is a bound preview/test service. It permits opening/backing up that root but cannot switch the global workspace. Keep existing supervisors; verify /api/identity and code revision. Never kill foreign listeners. open_library reuses matching healthy instances. library_service is the macOS fallback only when no host manager owns an instance, without login startup.

Backups are local, not cloud synchronization. Dialogue, translation and review use the connected account/service. Learning files and machine configuration stay out of public Skill packages.
