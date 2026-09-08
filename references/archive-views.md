# Archive views / 学习档案视图

Three layers answer different questions:

1. **Reflection / 统计回顾:** period activity, at most three expression summaries and two suggested revisits. No expanded history. Period observations may compare against earlier evidence but never use later evidence. First observations are labelled as such.
2. **Progress index / 词句进展:** 20 items per page, text and stage filters, practice-date range. With an end date, status is derived as of that date. Without one it is the latest recorded state. Date filtering selects concepts actually observed in the interval.
3. **Expression detail / 词句详情:** latest recorded state and a bounded set of genuine first milestones; newest-first history has a month filter and 10 events per page. The month changes the history, not the explicitly labelled current status. Notes and utterances expand on demand. Source links lead to original sessions.

词句包括有学习价值的词、短语、具体义项和句型。闪卡数、跟踪词句数和观察次数不是同一个指标，也不是已掌握词汇量。同一个词的不同义项使用不同 ID；原始整句卡和抽取短语可分别回顾。

`progress.go` derives snapshots without mutating sources. API list and summary responses exclude full histories; `/api/progress/<id>` returns only the requested history page. Months are a compact index of available history. Raw records remain local. Period comparison is a product convention, not a proficiency score.

Tests use synthetic evidence to check a 1,201-item index and 1,500-event history, date boundaries, first observations, later difficulty, search and pagination. These are bounded-response checks, not a claim of production performance at every scale. The current source reader rebuilds an in-memory index when source files change. Add disk indexing only after a measured bottleneck justifies it.
