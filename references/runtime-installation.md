# Standalone runtime

The Agent owns installation, diagnosis, initialization, service setup and verification. The learner supplies only their practice intent and any real login/system permission that cannot be delegated. Do not turn these instructions into user homework.

## Entry and supported surface

- macOS / Linux: `<skill>/scripts/coach <command>`.
- Windows: `& <skill>/scripts/coach.ps1 <command>`.
- The entry reads `runtime-version.txt`, downloads the exact release artifact over HTTPS, verifies its SHA-256, and caches it in `<skill>/bin/`. Data remains outside the Skill. Subsequent calls need no download or development runtime.
- Published targets are macOS Intel/Apple Silicon, Linux x64/ARM64 and Windows x64/ARM64. Host features remain separate: local files, a Codex app-server CLI, existing ChatGPT login, and source-bound Voice transcript events. A compiled binary does not add unsupported Voice features to mobile, ChatGPT web or another agent.
- Downloads can fail on a restricted network. The Agent may obtain the same pinned release through an allowed network path and verify the official checksum. Do not silently substitute an unknown executable, disable Gatekeeper/SmartScreen, or install a global language runtime as a fallback.

## Capability checks

`coach doctor` checks the archive and discovers the Codex executable without making a model request. `coach doctor --probe` additionally checks the existing ChatGPT login, requested model and tool-disabled connection. Use the probe for setup/repair, not repeatedly before healthy practice.

`ENGLISH_COACH_CODEX` selects a verified host CLI when normal discovery cannot find it. It does not select an API key. The Agent may inspect the installed Codex application's resources/PATH and pass that path. Never copy authentication files or expose their contents.

The product has four independent states: local archive/page, bound source ingestion, translation, and written review. State them separately. New English continues during a translation outage; the page offers retry after bounded automatic attempts. A missing host transcript is different from a model/login/network failure. No endpoint claims actual microphone or spoken-instruction control.

## Service ownership

`coach service start` reuses a matching healthy instance on fixed `127.0.0.1:8897`. A foreign listener, a different archive or an older build is preserved and reported. `prepare --service-url <verified-origin>` supports an existing project manager and checks the identity and archive API before reuse.

On a new machine the bundled manager uses a current-login macOS launchd job, Linux user systemd unit, or Windows demand-start Scheduled Task. It does not request login startup. A Linux environment without a user systemd session needs the Agent to use an already available, verified native supervisor for `coach serve --workspace --port 8897`; do not leave a terminal-only process and promise continued availability. A headless environment may use the archive without native Voice.

Prefer the machine's existing manager when one already owns the service. Do not install a second supervisor. `service stop` verifies instance identity and idle work before stopping its own native job. Explicit `service resume` restores a deliberately stopped job. Unavailable registered jobs need owner/log inspection, not duplicate startup. Do not stop unrelated practice.

Upgrades: download/cache the new pinned binary first. Check the current listener, manager, identity and active Voice/review. Preserve a verified backup, stop the exact old instance through its manager, update its executable command, start and verify identity plus `/api/overview` and `/api/live`. A page refresh does not reload embedded Go code/assets. Do not delete learning files or change saved preferences during runtime replacement.

## Local records and migration

`coach paths` returns the authoritative `data_root`, config path and optional project page. First use creates `~/.codex/english-speaking-coach/data` (or `$CODEX_HOME/english-speaking-coach/data`) without a directory questionnaire. Existing machine configuration wins; missing configured storage is never replaced with a fresh empty archive. Saved correction choices are preserved; new users default to useful in-character English wording help.

The page's storage entry supports opening the directory, complete ZIP backup, restore, adoption and copy-and-switch. `coach storage` exposes the same verified operations for the Agent. Old sources remain. A migration detaches machine-specific live watchers and unfinished model jobs. It does not migrate Codex login or the native app's complete conversation history.
