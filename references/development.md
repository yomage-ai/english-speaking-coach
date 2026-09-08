# Developer checks / 开发验证

Ordinary Skill use executes `scripts/coach` or `scripts/coach.ps1`, which download the pinned Go release. Source builds use Go only as a developer dependency.

- `go test -race ./...` checks canonical records, mastery evidence, exact-source binding, UTF-8 tails, failure isolation, JSON-RPC restrictions, backups, storage switching and a separately built executable with an empty PATH.
- `go vet ./...` checks Go code. The two `node tests/*updates.cjs` suites check the existing web behavior; Node is a development test dependency only.
- `ENGLISH_COACH_REAL_MODEL_TEST=1 go test -run TestRealModelTranslation -v .` and `ENGLISH_COACH_REAL_REVIEW_TEST=1 go test -run TestRealReviewIntegration -v .` are explicit account integration tests using fictional sources in temporary archives. They consume account quota, do not open a microphone and do not certify native Voice behavior.
- `go run ./internal/release -out dist` builds six standalone targets with `CGO_ENABLED=0`, embedded page/instruction assets, checksums and a content revision. `-revision` prints that revision. Do not publish binaries built while source files are changing.
- The previous Python scripts and Python tests are frozen development comparison material. They are never invoked by the installed entry or Go program. Do not restore a Python fallback to fix installation. Compare actual archive/API behavior before changing the data contract.

Reviewed model transport schemas live in `assets/runtime/contracts.json`; preserve property order for early streaming suggestions. Speaking prose is split by purpose/mode in `assets/runtime/speaking.json`; the runtime composes the selected policy. Skill instructions remain the Agent's behavioral entry point. These are explicit local contracts, not a mechanism for overriding another native Voice model.

A release tag must equal `runtime-version.txt`. The release workflow waits for native OS tests before publishing. Keep private data, config files, logs, auth state, local binaries and test archives out of Git. Runtime replacement must preserve the existing service manager and wait for its archive to be idle.
