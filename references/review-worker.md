# Local review jobs / 本地复盘任务

The archive service owns one bounded worker per learning root. This avoids coupling report delivery to a parent Agent's reasoning effort, repeated schema reads or knowledge-base cleanup.

## Lifecycle / 生命周期

- prepare_practice registers only the exact practice Voice and source file. A late Voice start gets a scoped watch. Ordinary maintenance never binds Voice.
- The worker sees a confirmed close, queues that Voice, reads its unique public transcript, and makes one tool-disabled ephemeral model request through the existing ChatGPT login. It does not read hidden reasoning or arbitrary other tasks.
- Current model: gpt-5.6-sol, low effort. Generation has a 120-second request timeout. One validation repair is allowed, not endless automatic retries. Connection/account failures preserve an actionable error; no API-key fallback.
- Short temporary turn IDs reduce repeated output tokens; the program restores exact source IDs before validation and saving. The JSON schema fixes the transport. Deterministic checks require exact quotes, all learner turns accounted for, separate word-help assessments, and reading help or a reason to omit it for priorities. A short-question default avoids artificial internal pauses. Redundant omissions of already-selected turns are removed by code. Invalid optional reading annotations are withheld with an explicit note and omission reason; they do not trigger regenerating a correct core lesson. Semantic judgments are still model judgments.
- The selected draft is written before commit. The writer lock owns final IDs and canonical deduplication. Worker process death releases a separate OS lock; a restart can reuse a draft. A pending model call may need one new generation after process loss because no draft was returned.
- Newly arrived final segments are rechecked before saving. An explicit retry uses the same source identity. Arbitrarily late or changed source logs after a completed save need the documented record recovery flow, not a second lesson.
- Source logs must remain readable until review completion. The transient draft contains selected material only; successful saves remove it. Runtime stores job metadata, not a second learning database.

## Agent handoff / Agent 交接

Use `review-begin --thread-id … --voice-id …` once on an actual end callback. It returns saved or queued state and the exact page. Open that page immediately. Do not produce a competing draft or wait for knowledge maintenance.

For a failed worker, inspect its error and source availability, then use the page's **重试本场复盘** or `enqueue(..., retry=True)`. For manual recovery, verify no worker owns the job before using `review-begin --manual --with-transcript` and `finish-review`. Duplicate saved sources reuse the canonical lesson.

A displayed stage is real progress, not an invented percentage or a completion promise. Page rendering, model generation and final file writing have separate timings. A parent task can finish its other duties while the local worker continues; no scheduled AI polling task is needed.

## Verification / 验证

Use temporary archives for closed/active Voice, two-worker exclusion, saved-draft restart, corrupt evidence, explicit retry, separate vocabulary coverage and source-tail arrival. A real structured model trial checks semantic output and latency; deterministic tests alone do not. Existing native Voice remains responsible for turn detection and actual audio language.
