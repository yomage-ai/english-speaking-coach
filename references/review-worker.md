# Local review jobs / 本地复盘任务

The archive service owns one bounded worker per learning root. This avoids coupling report delivery to a parent Agent's reasoning effort, repeated schema reads or knowledge-base cleanup.

## Lifecycle / 生命周期

- prepare_practice registers only the exact practice Voice and source file. A late Voice start gets a scoped watch. Ordinary maintenance never binds Voice.
- The worker sees a confirmed close, queues that Voice, reads its unique public transcript, and makes one tool-disabled ephemeral model request through the existing ChatGPT login. It does not read hidden reasoning or arbitrary other tasks.
- Current model: gpt-5.6-sol, low effort. Generation has a 120-second request timeout. One validation repair is allowed, not endless automatic retries. Connection/account failures preserve an actionable error; no API-key fallback.
- Short temporary turn IDs reduce repeated output tokens; the program restores exact source IDs before validation and saving. The JSON schema fixes the transport. Deterministic checks require exact quotes, all learner turns accounted for, separate word-help assessments, and reading help or a reason to omit it for priorities. A short-question default avoids artificial internal pauses. Redundant omissions of already-selected turns are removed by code. Invalid optional reading annotations are withheld with an explicit note and omission reason; they do not trigger regenerating a correct core lesson. Semantic judgments are still model judgments.
- The selected draft is written before commit. The writer lock owns final IDs and canonical deduplication. Worker process death releases a separate OS lock; a restart can reuse a draft. A pending model call may need one new generation after process loss because no draft was returned.
- Newly arrived final segments are rechecked before saving. An explicit retry uses the same source identity. Arbitrarily late or changed source logs after a completed save need the documented record recovery flow, not a second lesson.
- Source logs must remain readable until review completion. The transient draft contains selected material only; successful saves remove it. Runtime stores job metadata and provisional selected suggestions, not a second learning database.

## Agent handoff / Agent 交接

Use `review-begin --thread-id … --voice-id …` once on an actual end callback. It returns saved or queued state and the exact page. Open that page immediately. Do not produce a competing draft or wait for knowledge maintenance.

For a failed worker, inspect its error and source availability, then use the page's **重试本场复盘** or `enqueue(..., retry=True)`. For manual recovery, verify no worker owns the job before using `review-begin --manual --with-transcript` and `finish-review`. Duplicate saved sources reuse the canonical lesson.

A displayed stage is real progress, not an invented percentage or a completion promise. Page rendering, model generation and final file writing have separate timings. A parent task can finish its other duties while the local worker continues; no scheduled AI polling task is needed.

## Verification / 验证

Use temporary archives for closed/active Voice, two-worker exclusion, saved-draft restart, corrupt evidence, explicit retry, separate vocabulary coverage and source-tail arrival. A real structured model trial checks semantic output and latency; deterministic tests alone do not. Existing native Voice remains responsible for turn detection and actual audio language.

## Progressive delivery / 逐步展示

The single model response puts expressions first. As soon as an expression's source IDs, exact original quote, usable English and Chinese meaning are complete, code checks those fields against this Voice and publishes up to three provisional suggestions. It does not wait for optional reading metadata. Full turn coverage, word checks and evidence validation continue; only a final validated commit changes learning history. Preview is cleared on a changed source or repair, retained with a visible error after interruption, and replaced by the saved lesson on success. Timing records first preview separately from full generation.

Exact repeated English/Chinese entries are coalesced before ID allocation, retaining their linked quotes and an actual scored attempt if supplied. Priorities and concept links are remapped. This avoids a full regeneration for a duplicate canonical phrase; it never merges different meanings or invents a stronger score. Coach mistakes belong in coaching notes, not the learner's error count.

页面先展示最多三条来源校验后的表达建议，完整检查继续进行；这三条不是复盘总量上限，也还没有计入正式学习记录。同一句的求助和后续尝试保留证据后合并，避免编号冲突造成整份重做。首批出现时间与完整完成时间分开记录；不承诺固定秒数。
