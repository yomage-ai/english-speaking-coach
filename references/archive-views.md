# Archive views

Three layers answer different questions:

1. **Reflection:** period activity, at most three expression summaries and two suggested revisits. No expanded history. Period observations may compare against earlier evidence but never use later evidence. First observations are labelled as such.
2. **Progress index:** 20 items per page, text and stage filters, practice-date range. With an end date, status is derived as of that date. Without one it is the latest recorded state. Date filtering selects concepts actually observed in the interval.
3. **Expression detail:** latest recorded state and a bounded set of genuine first milestones; newest-first history has a month filter and 10 events per page. The month changes the history, not the explicitly labelled current status. Notes and utterances expand on demand. Source links lead to original sessions.

`progress.go` derives snapshots without mutating sources. API list and summary responses exclude full histories; `/api/progress/<id>` returns only the requested history page. Months are a compact index of available history. Raw records remain local. Period comparison is a product convention, not a proficiency score.

Tests use synthetic evidence to check a 1,201-item index and 1,500-event history, date boundaries, first observations, later difficulty, search and pagination. These are bounded-response checks, not a claim of production performance at every scale. The current source reader rebuilds an in-memory index when source files change. Add disk indexing only after a measured bottleneck justifies it.

Flashcard counts, tracked concepts and observations are different measures; none is a mastered-vocabulary count. Track different senses with different IDs. A full-sentence card can coexist with an extracted phrase.
