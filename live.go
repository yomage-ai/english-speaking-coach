package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	"log"
	_ "modernc.org/sqlite"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Live struct {
	root string
	db   *sql.DB
}

func openLive(root string) *Live {
	dir := filepath.Join(root, "Live")
	mkdir(dir)
	path := filepath.Join(dir, "companion.sqlite3")
	lock, ok := tryLock(filepath.Join(dir, ".sqlite-init.lock"))
	if !ok {
		must(lock.Lock())
	}
	defer lock.Unlock()
	// The chosen folder is a filesystem path, not URI syntax. Preserve literal
	// percent/hash/question-mark characters instead of opening a truncated path.
	uriPath := strings.NewReplacer("%", "%25", "#", "%23", "?", "%3F").Replace(filepath.ToSlash(path))
	db, e := sql.Open("sqlite", "file:"+uriPath+"?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_txlock=immediate")
	must(e)
	db.SetMaxOpenConns(1)
	_, e = db.Exec(`CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,desired TEXT NOT NULL,state TEXT NOT NULL);CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE IF NOT EXISTS segments(seq INTEGER PRIMARY KEY AUTOINCREMENT,run TEXT NOT NULL,id TEXT NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL,timestamp TEXT,ordinal INTEGER,ingested_at TEXT NOT NULL,chinese TEXT,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,translated_at TEXT,latency REAL,UNIQUE(run,id));CREATE INDEX IF NOT EXISTS segment_queue ON segments(run,status,seq);`)
	must(e)
	require(exists(path), "字幕数据库没有创建在指定目录；已停止，未采用其他路径。")
	_ = os.Chmod(path, 0600)
	return &Live{root, db}
}
func (l *Live) close() { l.db.Close() }

type sqlRunner interface {
	Exec(string, ...any) (sql.Result, error)
	Query(string, ...any) (*sql.Rows, error)
}

func query(db sqlRunner, q string, args ...any) A {
	r, e := db.Query(q, args...)
	must(e)
	defer r.Close()
	cols, e := r.Columns()
	must(e)
	out := A{}
	for r.Next() {
		vals := make([]any, len(cols))
		ptr := make([]any, len(cols))
		for i := range vals {
			ptr[i] = &vals[i]
		}
		must(r.Scan(ptr...))
		m := M{}
		for i, k := range cols {
			if b, ok := vals[i].([]byte); ok {
				m[k] = string(b)
			} else {
				m[k] = vals[i]
			}
		}
		out = append(out, m)
	}
	must(r.Err())
	return out
}
func sqlExec(db sqlRunner, q string, args ...any) sql.Result {
	r, e := db.Exec(q, args...)
	must(e)
	return r
}
func parseObject(s string) M { var m M; must(json.Unmarshal([]byte(s), &m)); return m }
func (l *Live) meta(key string) any {
	rows := query(l.db, "SELECT value FROM meta WHERE key=?", key)
	if len(rows) == 0 {
		return nil
	}
	return obj(rows[0])["value"]
}
func (l *Live) setMeta(key string, value any) {
	sqlExec(l.db, "INSERT OR REPLACE INTO meta VALUES (?,?)", key, value)
}
func stateRow(row M) M {
	if len(row) == 0 {
		return nil
	}
	return merge(parseObject(str(row["state"])), M{"desired": row["desired"]})
}
func (l *Live) active() M {
	rows := query(l.db, "SELECT runs.* FROM runs JOIN meta ON meta.value=runs.id WHERE meta.key='active'")
	if len(rows) == 0 {
		return nil
	}
	return stateRow(obj(rows[0]))
}
func (l *Live) run(id string) M {
	rows := query(l.db, "SELECT * FROM runs WHERE id=?", id)
	if len(rows) == 0 {
		return nil
	}
	return stateRow(obj(rows[0]))
}
func terminal(s any) bool { return has(stringsA("ended", "error", "expired", "stopped"), s) }
func (l *Live) patch(id string, fields M) M {
	tx, e := l.db.Begin()
	must(e)
	defer tx.Rollback()
	rows := query(tx, "SELECT * FROM runs WHERE id=?", id)
	require(len(rows) == 1, "Unknown binding")
	state := merge(stateRow(obj(rows[0])), fields)
	sqlExec(tx, "UPDATE runs SET desired=?,state=? WHERE id=?", state["desired"], compact(omit(state, "desired")), id)
	must(tx.Commit())
	return state
}
func (l *Live) bind(thread, source, model string, demo bool) M {
	source = absolute(source)
	require(sourceIdentity(source) == thread, "源文件身份与指定任务不一致；未绑定。")
	voice, cursor := lifecycle(source)
	require(voice != "", "没有活动 Voice，未创建伴随。文字练习使用 resume；语音开启后 Agent 再绑定当前场次。")
	tx, e := l.db.Begin()
	must(e)
	defer tx.Rollback()
	rows := query(tx, "SELECT runs.* FROM runs JOIN meta ON meta.value=runs.id WHERE meta.key='active'")
	if len(rows) > 0 {
		old := stateRow(obj(rows[0]))
		if old["desired"] != "stopped" && !terminal(old["status"]) {
			if old["source"] == source && (str(old["voice_id"]) == "" || old["voice_id"] == voice) && old["model"] == model {
				return old
			}
			panic(fmt.Errorf("另一场双语伴随尚未结束；未替换其他任务。"))
		}
	}
	if voice != "" {
		cursor = 0
	}
	id := uuid.NewString()
	var vid any
	if voice != "" {
		vid = voice
	}
	s := M{"id": id, "thread_id": thread, "source": source, "voice_id": vid, "cursor": cursor, "created_at": now(), "created_epoch": epoch(), "model": model, "effort": "low", "demo": demo, "status": "starting", "transcript_status": "waiting", "translation_status": "connecting", "translation_error": nil, "error": nil, "ready": false, "heartbeat": nil, "last_transcript_at": nil, "last_read_at": nil, "last_activity_epoch": epoch(), "close_epoch": nil, "invalid_lines": 0, "rewinds": 0, "has_partial_line": false}
	s["source_file_id"] = fileIdentity(source)
	sqlExec(tx, "INSERT INTO runs VALUES (?,?,?)", id, "running", compact(s))
	sqlExec(tx, "INSERT OR REPLACE INTO meta VALUES ('active',?)", id)
	if !demo {
		sqlExec(tx, "INSERT OR REPLACE INTO meta VALUES ('enabled','true')")
	}
	for _, v := range query(tx, "SELECT id,state FROM runs") {
		r := obj(v)
		old := parseObject(str(r["state"]))
		if r["id"] != id && epoch()-num(old["created_epoch"]) > 7*86400 {
			sqlExec(tx, "DELETE FROM segments WHERE run=?", r["id"])
			sqlExec(tx, "DELETE FROM runs WHERE id=?", r["id"])
			sqlExec(tx, "DELETE FROM meta WHERE key IN (?,?)", "hint:"+str(r["id"]), "scene:"+str(r["id"]))
		}
	}
	must(tx.Commit())
	return l.run(id)
}
func (l *Live) enabled() bool { return l.meta("enabled") == nil || l.meta("enabled") == "true" }
func companionPrefs(root string) M {
	if !exists(filepath.Join(root, "Live", "companion.sqlite3")) {
		return M{"enabled": true}
	}
	var enabled bool
	err := attempt(func() { l := openLive(root); defer l.close(); enabled = l.enabled() })
	if err != nil {
		return M{"enabled": false, "error": "双语缓存暂不可读；学习档案仍保留。"}
	}
	return M{"enabled": enabled}
}
func (l *Live) insertSegments(run string, rows A) bool {
	changed := false
	tx, e := l.db.Begin()
	must(e)
	defer tx.Rollback()
	for _, v := range rows {
		r := obj(v)
		prior := query(tx, "SELECT * FROM segments WHERE run=? AND id=?", run, r["id"])
		if len(prior) > 0 {
			old := obj(prior[0])
			merged := reconcileSegment(old, r)
			if merged["text"] != old["text"] {
				sqlExec(tx, "UPDATE segments SET text=?,chinese=NULL,status='pending',attempts=0,translated_at=NULL,latency=NULL WHERE run=? AND id=?", r["text"], run, r["id"])
				state := parseObject(str(obj(query(tx, "SELECT state FROM runs WHERE id=?", run)[0])["state"]))
				delete(obj(state["translation_rejected"]), str(r["id"]))
				sqlExec(tx, "UPDATE runs SET state=? WHERE id=?", compact(state), run)
				changed = true
			}
			continue
		}
		sqlExec(tx, "INSERT INTO segments(run,id,role,text,timestamp,ordinal,ingested_at) VALUES (?,?,?,?,?,?,?)", run, r["id"], r["role"], r["text"], r["timestamp"], r["ordinal"], now())
		changed = true
	}
	must(tx.Commit())
	return changed
}
func (l *Live) readTail(s M) {
	path := str(s["source"])
	require(sourceIdentity(path) == s["thread_id"], "源日志身份变化，读取已停止。")
	stat, e := os.Stat(path)
	must(e)
	cursor := int64(num(s["cursor"]))
	identity := fileIdentity(path)
	if stat.Size() < cursor || (str(s["source_file_id"]) != "" && s["source_file_id"] != identity) {
		require(str(s["voice_id"]) != "", "等待期间源日志被重写，请重新绑定。")
		cursor = 0
		s["rewinds"] = integer(s["rewinds"]) + 1
	}
	rows := A{}
	fields := pick(s, "voice_id", "rewinds", "close_epoch", "voice_started_at", "voice_closed_at")
	fields["source_file_id"] = identity
	next, partial := scanLines(path, cursor, 2*maxLine, func(row M) {
		if row["type"] != "realtime_item" {
			return
		}
		p := obj(row["payload"])
		voice := str(p["realtime_session_id"])
		if p["type"] == "realtime_session_started" && str(fields["voice_id"]) == "" && voice != "" {
			fields["voice_id"] = voice
			fields["last_activity_epoch"] = epoch()
		}
		if voice == "" || voice != fields["voice_id"] {
			return
		}
		switch p["type"] {
		case "realtime_session_started":
			fields["voice_started_at"] = row["timestamp"]
		case "realtime_session_closed":
			if fields["close_epoch"] == nil {
				fields["close_epoch"] = epoch()
			}
			fields["voice_closed_at"] = row["timestamp"]
		case "transcript_segment":
			if segment := transcriptSegment(p, row); segment != nil {
				rows = append(rows, segment)
			}
		}
	})
	if l.insertSegments(str(s["id"]), rows) {
		fields["last_transcript_at"] = now()
		fields["last_activity_epoch"] = epoch()
	}
	fields["cursor"], fields["has_partial_line"] = next, partial
	fields["last_read_at"], fields["heartbeat"], fields["heartbeat_epoch"] = now(), now(), epoch()
	fields["transcript_status"] = "listening"
	fields["status"] = "waiting_transcript"
	if str(fields["voice_id"]) == "" {
		fields["status"] = "waiting_voice"
	}
	s = l.patch(str(s["id"]), fields)
	if str(s["voice_id"]) != "" {
		// Review metadata belongs to closeout, not source integrity. Its failure
		// must not stop receiving the remaining conversation.
		registrationError := attempt(func() { l.registerReview(s) })
		var diagnostic any
		if registrationError != nil {
			diagnostic = registrationError.Error()
		}
		if s["review_error"] != diagnostic {
			s = l.patch(str(s["id"]), M{"review_error": diagnostic})
		}
	}
	end := num(s["close_epoch"])
	if s["desired"] == "drain" && end == 0 {
		end = epoch()
		s = l.patch(str(s["id"]), M{"drain_epoch": get(s, "drain_epoch", end)})
		end = num(s["drain_epoch"])
	}
	if end > 0 {
		s = l.patch(str(s["id"]), M{"status": "draining"})
		quiet := epoch() - num(s["last_activity_epoch"])
		if epoch()-end >= 5 && quiet >= 5 && !partial {
			counts := l.counts(str(s["id"]))
			pending := integer(counts["pending"]) + integer(counts["translating"])
			if pending == 0 || s["translation_status"] == "unavailable" || epoch()-end >= 60 {
				l.patch(str(s["id"]), M{"status": "ended", "transcript_status": "ended", "ready": false, "desired": "stopped"})
			}
		}
	} else if epoch()-num(s["created_epoch"]) > 21600 || epoch()-num(s["last_activity_epoch"]) > 1800 {
		l.patch(str(s["id"]), M{"status": "expired", "desired": "stopped", "ready": false, "error": "长时间未收到新转写，已停止伴随。"})
	}
}
func (l *Live) counts(run string) M {
	c := M{}
	for _, v := range query(l.db, "SELECT status,COUNT(*) AS n FROM segments WHERE run=? GROUP BY status", run) {
		r := obj(v)
		c[str(r["status"])] = r["n"]
	}
	return c
}
func (l *Live) batch(run string) A {
	tx, e := l.db.Begin()
	must(e)
	defer tx.Rollback()
	// New sentences precede retries, so a poison sentence cannot hold the queue.
	rows := query(tx, "SELECT * FROM segments WHERE run=? AND status='pending' ORDER BY attempts,seq LIMIT 3", run)
	selected := A{}
	size := 0
	for _, v := range rows {
		r := obj(v)
		if len(selected) > 0 && size+len([]rune(str(r["text"]))) > 4500 {
			break
		}
		selected = append(selected, r)
		size += len([]rune(str(r["text"])))
		sqlExec(tx, "UPDATE segments SET status='translating',attempts=attempts+1 WHERE seq=?", r["seq"])
	}
	must(tx.Commit())
	return selected
}
func (l *Live) translated(run string, rows A, latency float64, expected M) {
	for _, v := range rows {
		r := obj(v)
		sqlExec(l.db, "UPDATE segments SET chinese=?,status='translated',translated_at=?,latency=? WHERE run=? AND id=? AND text=? AND (status!='translated' OR chinese IS NOT ?)", r["chinese"], now(), latency, run, r["id"], expected[str(r["id"])], r["chinese"])
	}
}
func (l *Live) failBatch(run string, rows A) {
	for _, v := range rows {
		r := obj(v)
		sqlExec(l.db, "UPDATE segments SET status=CASE WHEN attempts>=2 THEN 'failed' ELSE 'pending' END WHERE run=? AND id=? AND text=? AND status='translating'", run, r["id"], r["text"])
	}
}
func (l *Live) rejectTranslations(run string, rejected, expected M) {
	// A later duplicate/conflicting unit can invalidate an early streamed row.
	// Revoke only that request's exact source version, then apply the usual budget.
	for id := range rejected {
		sqlExec(l.db, "UPDATE segments SET chinese=NULL,translated_at=NULL,latency=NULL,status=CASE WHEN attempts>=2 THEN 'failed' ELSE 'pending' END WHERE run=? AND id=? AND text=?", run, id, expected[id])
	}
}
func (l *Live) rememberTranslationErrors(run string, valid A, rejected M, expected M) {
	errors := copyM(obj(l.run(run)["translation_rejected"]))
	for _, v := range valid {
		delete(errors, str(obj(v)["id"]))
	}
	for id, reason := range rejected {
		rows := query(l.db, "SELECT text,status FROM segments WHERE run=? AND id=?", run, id)
		if len(rows) > 0 && obj(rows[0])["text"] == expected[id] && obj(rows[0])["status"] != "translated" {
			errors[id] = reason
		}
	}
	l.patch(run, M{"translation_rejected": errors})
}
func (l *Live) teachingRows(run string) A {
	return reverse(query(l.db, "SELECT id,role,text,timestamp FROM segments WHERE run=? ORDER BY seq DESC LIMIT 30", run))
}
func (l *Live) teachingContext(run string) M {
	rows := l.teachingRows(run)
	profile := obj(readJSON(filepath.Join(l.root, "profile.json")))
	return M{"conversation": annotateFragments(rows), "scene": sceneFor(l.root, run), "profile": pick(profile, "correction", "input_support", "help_language")}
}
func (l *Live) view(a M) M {
	active := l.active()
	id := textOr(a["run"], str(active["id"]))
	s := l.run(id)
	require(id == "" || s != nil, "没有找到这场双语缓存。")
	counts := l.counts(id)
	total := 0
	for _, n := range counts {
		total += integer(n)
	}
	pages := max(1, (total+39)/40)
	page := clampInt(a["page"], pages, 1, pages)
	offset := max(0, total-40)
	if str(a["page"]) != "" {
		offset = (page - 1) * 40
	}
	if str(a["offset"]) != "" {
		offset = clampInt(a["offset"], offset, 0, max(0, total-1))
		page = min(pages, (offset+39)/40+1)
	}
	lookback := min(4, offset)
	rows := query(l.db, "SELECT * FROM segments WHERE run=? ORDER BY seq LIMIT ? OFFSET ?", id, 40+lookback, offset-lookback)
	rows = annotateFragments(rows)[lookback:]
	var hint any
	if raw := str(l.meta("hint:" + id)); raw != "" {
		hint = parseObject(raw)
	}
	key := teachingKey(M{"conversation": l.teachingRows(id)})
	if key == "" || obj(hint)["context_key"] != key {
		hint = nil
	}
	if s != nil {
		s = omit(s, "source", "file_identity", "source_file_id", "cursor")
		s["scene_introduction"] = l.meta("scene:" + id)
		s["stale"] = s["desired"] != "stopped" && !terminal(s["status"]) && epoch()-num(s["heartbeat_epoch"]) > 8
		if terminal(s["status"]) || s["desired"] == "stopped" || s["close_epoch"] != nil {
			hint = nil
		}
	}
	history := A{}
	for _, v := range query(l.db, "SELECT state FROM runs ORDER BY rowid DESC LIMIT 12") {
		r := parseObject(str(obj(v)["state"]))
		history = append(history, pick(r, "id", "created_at", "demo", "status", "thread_id", "recovery_mode", "voice_started_at"))
	}
	return M{"state": s, "items": rows, "teaching": hint, "total": total, "counts": counts, "page": page, "pages": pages, "offset": offset, "enabled": l.enabled(), "server_time": now(), "history": history}
}
func (l *Live) registerReview(s M) {
	thread, voice := str(s["thread_id"]), str(s["voice_id"])
	if voice == "" {
		return
	}
	watch := obj(maybeJSON(filepath.Join(l.root, "Runtime", "ReviewWatches", str(s["id"])+".json"), M{}))
	if len(watch) > 0 || s["auto_review"] == true {
		fields := merge(omit(watch, "thread_id"), M{"source": s["source"], "run_id": s["id"], "auto_review": true})
		setReviewStage(l.root, thread, voice, "practicing", fields, false)
		if len(watch) > 0 {
			_ = os.Remove(filepath.Join(l.root, "Runtime", "ReviewWatches", str(s["id"])+".json"))
		}
	}
}
func sleepContext(ctx context.Context, d time.Duration) bool {
	select {
	case <-ctx.Done():
		return false
	case <-time.After(d):
		return true
	}
}
func runTailer(ctx context.Context, root string) {
	lock, ok := tryLock(filepath.Join(root, "Runtime", ".live-worker.lock"))
	if !ok {
		return
	}
	defer lock.Unlock()
	l := openLive(root)
	defer l.close()
	for {
		if ctx.Err() != nil {
			return
		}
		s := l.active()
		if s != nil && s["desired"] != "stopped" && !terminal(s["status"]) {
			if err := attempt(func() { l.readTail(s) }); err != nil {
				log.Printf("caption source read failed run=%s thread=%s voice=%s cursor=%.0f: %v", str(s["id"]), str(s["thread_id"]), str(s["voice_id"]), num(s["cursor"]), err)
				l.patch(str(s["id"]), M{"status": "error", "transcript_status": "error", "desired": "stopped", "ready": false, "error": err.Error()})
			}
		}
		if !sleepContext(ctx, 250*time.Millisecond) {
			return
		}
	}
}

// Translation failure only changes translation fields. Source ingestion and review
// registration remain independent. Retries back off and stop after three failures.
func runTranslations(ctx context.Context, root string) {
	lock, ok := tryLock(filepath.Join(root, "Runtime", ".translation-worker.lock"))
	if !ok {
		return
	}
	defer lock.Unlock()
	l := openLive(root)
	defer l.close()
	var client *ModelClient
	defer func() {
		if client != nil {
			client.close()
		}
	}()
	current := ""
	failures := 0
	retryAt := 0.0
	for {
		if ctx.Err() != nil {
			return
		}
		s := l.active()
		if s == nil || s["desired"] == "stopped" || terminal(s["status"]) {
			if client != nil {
				client.close()
				client = nil
			}
			current = ""
			if !sleepContext(ctx, 350*time.Millisecond) {
				return
			}
			continue
		}
		id := str(s["id"])
		l.copyLocalTranscripts(id)
		if id != current {
			if client != nil {
				client.close()
			}
			client = nil
			current = id
			failures = 0
			retryAt = 0
			sqlExec(l.db, "UPDATE segments SET status='pending' WHERE run=? AND status='translating'", id)
		}
		if s["translation_retry"] == true {
			failures = 0
			retryAt = 0
			l.patch(id, M{"translation_retry": false})
			sqlExec(l.db, "UPDATE segments SET status='pending',attempts=0 WHERE run=? AND status IN ('failed','translating')", id)
		}
		if failures >= 3 || epoch() < retryAt {
			if !sleepContext(ctx, 350*time.Millisecond) {
				return
			}
			continue
		}
		rows := A{}
		err := attempt(func() {
			if client == nil {
				l.patch(id, M{"translation_status": "connecting", "translation_error": nil})
				client = newModelClient(str(s["model"]), 45*time.Second)
				client.maxTurns = 8
				client.connect(ctx)
				l.patch(id, M{"ready": true, "translation_status": "ready", "connection": M{"model": s["model"], "effort": "low", "auth": "chatgpt", "ephemeral": true}})
			}
			rows = l.batch(id)
			if len(rows) == 0 {
				return
			}
			l.patch(id, M{"translation_status": "translating"})
			expected := M{}
			for _, v := range rows {
				r := obj(v)
				expected[str(r["id"])] = r["text"]
			}
			timing := M{"started_at": now(), "segments": len(rows)}
			out, _, rejected, latency := client.translate(ctx, rows, nil, func(part A, seconds float64) {
				l.translated(id, part, seconds, expected)
				if timing["first_sentence_seconds"] == nil {
					timing["first_sentence_seconds"] = seconds
					l.patch(id, M{"translation_timing": timing})
				}
			})
			timing["request_seconds"] = latency
			l.translated(id, out, latency, expected)
			l.rejectTranslations(id, rejected, expected)
			// Semantic failures retry only their own rows, at most twice. They
			// never trip the connection circuit breaker or discard valid rows.
			l.failBatch(id, rows)
			l.rememberTranslationErrors(id, out, rejected, expected)
			l.patch(id, M{"translation_status": "ready", "translation_error": nil, "translation_failures": 0, "translation_retry_at": 0, "ready": true, "translation_timing": timing})
		})
		if err != nil {
			l.failBatch(id, rows)
			if client != nil {
				client.close()
				client = nil
			}
			failures++
			retryAt = epoch() + float64(failures*5)
			l.patch(id, M{"translation_status": "unavailable", "translation_error": err.Error(), "ready": false, "translation_failures": failures, "translation_retry_at": retryAt})
		} else if len(rows) > 0 {
			failures = 0
		}
		if !sleepContext(ctx, 300*time.Millisecond) {
			return
		}
	}
}
func (l *Live) retry(id string) {
	s := l.run(id)
	require(s != nil, "Unknown binding")
	if s["desired"] == "stopped" || terminal(s["status"]) {
		// Validate the exact closed source before queueing, without taking over
		// an unrelated active binding or silently creating a new practice.
		snapshotVoice(str(s["source"]), str(s["thread_id"]), str(s["voice_id"]))
		l.patch(id, M{"recovery_requested": true})
		return
	}
	l.patch(id, M{"translation_retry": true})
}
func liveURL(base, run string) string {
	return strings.TrimRight(base, "/") + "/#live?run=" + url.QueryEscape(run)
}
