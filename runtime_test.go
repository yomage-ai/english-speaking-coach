package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

const testThread = "11111111-1111-4111-8111-111111111111"
const testVoice = "22222222-2222-4222-8222-222222222222"

func testRoot(t *testing.T) string {
	t.Helper()
	root := filepath.Join(t.TempDir(), "学习 data")
	initialize(root)
	rebuild(root)
	return root
}
func fixtureRecord() M {
	return M{"id": "SES-20260908-001", "date": "2026-09-08", "practiced_at": "2026-09-08T09:00:00+08:00", "title": "Fictional bakery", "summary": "Practised asking for bread.", "source_ids": voiceSources(testThread, testVoice), "scenarios": stringsA("bakery"), "topics": stringsA("Food"), "next_focus": stringsA("Ask the price"), "expressions": A{M{"id": "EXP-20260908-001", "english": "I'd like two rolls, please.", "chinese": "我想要两个小面包。", "original": "I want two bread", "mastery": "not_tested", "next_review": "2026-09-09", "note": "Review-only wording suggestion."}}}
}
func fixtureDraft() M {
	return M{"title": "Fictional bakery", "summary": "Asked for bread and the price.", "expressions": A{M{"source_turn_ids": stringsA("u1"), "original": "I want two bread", "english": "I'd like two rolls, please.", "chinese": "我想要两个小面包。", "note": "Review-only wording suggestion."}}, "omitted_turns": M{"u2": "Polite closing"}, "priority_indices": A{0}, "reading_omissions": M{"0": "Familiar short phrase"}, "word_checks": A{M{"segment_id": "u1", "needs_word_help": false, "reason": "Sentence structure", "concept_indices": A{}}, M{"segment_id": "u2", "needs_word_help": false, "reason": "Polite closing", "concept_indices": A{}}}, "concept_observations": A{}}
}
func voiceLog(t *testing.T, closed bool) string {
	t.Helper()
	p := filepath.Join(t.TempDir(), "rollout.jsonl")
	rows := A{M{"type": "session_meta", "payload": M{"id": testThread}}, M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:00Z", "payload": M{"type": "realtime_session_started", "realtime_session_id": testVoice}}}
	atomicWrite(p, nil)
	for _, v := range rows {
		appendLog(p, obj(v))
	}
	appendSegment(p, "u1", "user", "I want two bread")
	appendSegment(p, "a1", "assistant", "You can say, I'd like two rolls, please.")
	appendSegment(p, "u2", "user", "Thank you.")
	if closed {
		appendClose(p)
	}
	return p
}
func appendLog(p string, row M) {
	f, e := os.OpenFile(p, os.O_APPEND|os.O_WRONLY, 0600)
	must(e)
	_, e = io.WriteString(f, compact(row)+"\n")
	must(e)
	must(f.Close())
}
func appendSegment(p, id, role, text string) {
	appendLog(p, M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:01Z", "payload": M{"type": "transcript_segment", "realtime_session_id": testVoice, "id": id, "role": role, "text": text}})
}
func appendClose(p string) {
	appendLog(p, M{"type": "realtime_item", "timestamp": "2026-09-08T01:01:00Z", "payload": M{"type": "realtime_session_closed", "realtime_session_id": testVoice}})
}
func reject(t *testing.T, f func()) {
	t.Helper()
	if err := attempt(f); err == nil {
		t.Fatal("Expected rejection")
	}
}
func TestRecordRoundTripAndConflict(t *testing.T) {
	root := testRoot(t)
	d := fixtureRecord()
	commitRecord(root, d)
	before := string(readFile(filepath.Join(root, "Sessions", str(d["id"])+".md")))
	if commitRecord(root, d)["status"] != "already_saved" {
		t.Fatal("not idempotent")
	}
	d["summary"] = "Conflicting evidence"
	reject(t, func() { commitRecord(root, d) })
	if string(readFile(filepath.Join(root, "Sessions", str(d["id"])+".md"))) != before {
		t.Fatal("Original changed")
	}
	if !truth(validateArchive(root)["ok"]) {
		t.Fatal("Invalid rebuilt archive")
	}
}
func TestRecordMarkupEscaped(t *testing.T) {
	root := testRoot(t)
	d := fixtureRecord()
	d["summary"] = "An example: --> <script>alert(1)</script>"
	commitRecord(root, d)
	if !equal(extract(filepath.Join(root, "Sessions", str(d["id"])+".md"), "speaking-record-v2"), d) {
		t.Fatal("Markup broke JSON block")
	}
	page := string(readFile(filepath.Join(root, "dashboard.html")))
	if strings.Contains(page, "<script>alert") || !strings.Contains(page, "我想要两个小面包") {
		t.Fatal("Offline snapshot must escape markup and retain bilingual learning content")
	}
}

func TestArchiveUpdateTimeReflectsSourcesNotPageVisit(t *testing.T) {
	root := testRoot(t)
	fixed := time.Date(2025, 4, 1, 12, 30, 0, 0, time.UTC)
	for _, p := range archiveSourceFiles(root) {
		must(os.Chtimes(p, fixed, fixed))
	}
	data := newArchive(root).query("/api/overview", M{})
	if !stamp(str(data["source_updated_at"])).Equal(fixed) {
		t.Fatal("Opening a page must not claim the learning records were just updated")
	}
}

func TestSourceReplacementRewindsWithoutDuplicateSegments(t *testing.T) {
	root, source := testRoot(t), voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, source, defaultModel, true)
	l.readTail(s)
	s = l.run(str(s["id"]))
	original := string(readFile(source))
	parts := strings.SplitN(original, "\n", 2)
	insert := compact(M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:01Z", "payload": M{"type": "transcript_segment", "realtime_session_id": testVoice, "id": "inserted", "role": "user", "text": "One more roll, please."}})
	atomicWrite(source, []byte(parts[0]+"\n"+insert+"\n"+parts[1]))
	l.readTail(s)
	if len(query(l.db, "SELECT id FROM segments WHERE run=?", s["id"])) != 4 || integer(l.run(str(s["id"]))["rewinds"]) != 1 {
		t.Fatal("Replaced larger source was not re-read exactly once", l.counts(str(s["id"])))
	}
}

func TestSQLiteUsesChosenFolderWithURISymbols(t *testing.T) {
	name := "English #1 %25 & 中文"
	if runtime.GOOS != "windows" {
		name += " ? why"
	}
	root := filepath.Join(t.TempDir(), name)
	initialize(root)
	l := openLive(root)
	l.setMeta("path-check", "preserved")
	l.close()
	if !exists(filepath.Join(root, "Live", "companion.sqlite3")) {
		t.Fatal("SQLite opened a different path instead of the selected folder")
	}
	l = openLive(root)
	defer l.close()
	if l.meta("path-check") != "preserved" {
		t.Fatal("Selected cache did not reopen")
	}
}

func TestManagedRecoveryBackupPreservesSavedLesson(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := defaultRoot()
	runCLI([]string{"init"})
	commitRecord(root, fixtureRecord())
	result := recoveryBackup(root)
	manifest := inspectBackup(readFile(str(result["recovery_backup"])))
	if integer(obj(manifest["counts"])["sessions"]) != 1 {
		t.Fatal("Recovery copy omitted the saved lesson")
	}
	if len(recoveryBackup(testRoot(t))) != 0 {
		t.Fatal("External test archive must not replace the managed recovery copy")
	}
}
func TestMasteryRequiresActualEvidence(t *testing.T) {
	for _, level := range []string{"independent", "transfer"} {
		t.Run(level, func(t *testing.T) {
			d := fixtureRecord()
			obj(arr(d["expressions"])[0])["mastery"] = level
			reject(t, func() { validatePayload(d, false) })
		})
	}
}
func TestMissingConfiguredArchiveIsNotReplaced(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	missing := filepath.Join(t.TempDir(), "missing")
	writeJSON(configPath(), M{"schema_version": 1, "data_root": missing, "project_page": nil})
	reject(t, func() { ensureWorkspace(workspace("")) })
	if exists(missing) {
		t.Fatal("Created empty replacement")
	}
}
func TestCanonicalStateAndScope(t *testing.T) {
	root := testRoot(t)
	d := fixtureRecord()
	commitRecord(root, d)
	second := copyM(d)
	second["id"] = "SES-20260908-002"
	second["practiced_at"] = "2026-09-08T10:00:00+08:00"
	second["source_ids"] = stringsA("test:second")
	e := obj(arr(second["expressions"])[0])
	e["mastery"] = "independent"
	e["review_result"] = "success"
	e["review_prompt"] = "none"
	e["original"] = "I'd like two rolls, please."
	commitRecord(root, second)
	state := buildState(root)
	if len(arr(state["expressions"])) != 1 || len(arr(obj(arr(state["expressions"])[0])["seen_in_sessions"])) != 2 {
		t.Fatal("Duplicate canonical expression")
	}
	archive := newArchive(root)
	v := archive.query("/api/terms", M{"session": "SES-20260908-002", "page": "999"})
	if integer(v["total"]) != 1 || integer(v["page"]) != 1 || integer(obj(v["scope"])["count"]) != 1 {
		t.Fatal(v)
	}
	detail := archive.query("/api/sessions/SES-20260908-001", M{})
	if obj(arr(detail["excerpts"])[0])["mastery"] != "not_tested" {
		t.Fatal("Later success rewrote historical lesson")
	}
}
func TestConceptEvidenceAndPeriodBoundary(t *testing.T) {
	root := testRoot(t)
	d := fixtureRecord()
	o := M{"id": "OBS-first", "concept_id": "CON-roll", "term": "roll", "meaning": "小面包", "dimension": "use", "result": "supported", "support": "model", "modality": "transcript", "context": "bakery", "note": "Prompted", "quote_kind": "utterance", "quote": "I want two bread", "expression_ids": stringsA("EXP-20260908-001")}
	d["concept_observations"] = A{o}
	commitRecord(root, d)
	second := copyM(d)
	second["id"] = "SES-20260909-001"
	second["date"] = "2026-09-09"
	second["practiced_at"] = "2026-09-09T09:00:00+08:00"
	second["source_ids"] = stringsA("test:later")
	ob := obj(arr(second["concept_observations"])[0])
	ob["id"], ob["result"], ob["support"], ob["context"] = "OBS-later", "success", "none", "cafe"
	commitRecord(root, second)
	cs := arr(buildState(root)["concepts"])
	if obj(cs[0])["level"] != "independent" {
		t.Fatal(cs)
	}
	period := periodRows(cs, M{"to": "2026-09-08"})
	if obj(period[0])["level"] != "supported" {
		t.Fatal("Future evidence leaked into past")
	}
	ob["dimension"] = "reading"
	reject(t, func() { validateObservations(A{ob}) })
}
func TestReadingGroupsPreserveWords(t *testing.T) {
	g := M{"kind": "suggestion", "groups": A{M{"text": "Do you have milk?", "stress": stringsA("milk")}}, "tone": "rise", "tone_note": "One possible neutral reading.", "memory": A{M{"text": "Do you have", "meaning": "询问有没有"}}}
	validateGuide(g, "Do you have milk?")
	obj(arr(g["groups"])[0])["text"] = "Do you milk have?"
	reject(t, func() { validateGuide(g, "Do you have milk?") })
}
func TestReviewCoverageSourceAndDedup(t *testing.T) {
	root := testRoot(t)
	source := voiceLog(t, true)
	snap := snapshotVoice(source, testThread, testVoice)
	draft := fixtureDraft()
	qualityCheck(draft, snap)
	record := normalizeReview(root, draft, testThread, testVoice, snap, buildState(root))
	if integer(obj(record["review_coverage"])["available_learner_turns"]) != 2 {
		t.Fatal(record)
	}
	draft["omitted_turns"] = M{}
	reject(t, func() { normalizeReview(root, draft, testThread, testVoice, snap, buildState(root)) })
	draft = fixtureDraft()
	obj(arr(draft["expressions"])[0])["original"] = "Not in transcript"
	reject(t, func() { normalizeReview(root, draft, testThread, testVoice, snap, buildState(root)) })
	draft = fixtureDraft()
	result := finishReview(root, draft, testThread, testVoice, source)
	again := finishReview(root, draft, testThread, testVoice, source)
	if result["session"] != again["session"] || again["status"] != "already_saved" {
		t.Fatal("Duplicate voice was saved twice")
	}
}
func TestWordCoverageCannotHideBehindSentence(t *testing.T) {
	snap := snapshotVoice(voiceLog(t, true), testThread, testVoice)
	d := fixtureDraft()
	obj(arr(d["word_checks"])[0])["needs_word_help"] = true
	reject(t, func() { qualityCheck(d, snap) })
}
func TestTranslationCoverageAndMixedEnglish(t *testing.T) {
	segments := A{M{"id": "1", "role": "user", "text": "车厘子，how do you say it?"}}
	units := translationUnits(segments)
	if len(units) != 1 {
		t.Fatal(units)
	}
	u := obj(units[0])
	result := assembleTranslations(segments, units, A{M{"id": u["id"], "chinese": "怎么说？", "kind": "translation"}})
	if obj(result[0])["chinese"] != "车厘子，怎么说？" {
		t.Fatal(result)
	}
	reject(t, func() { assembleTranslations(segments, units, A{}) })
	reject(t, func() {
		assembleTranslations(segments, units, A{M{"id": u["id"], "chinese": "how do you say it?", "kind": "translation"}})
	})
}
func TestStreamingPreviewBeforeOptionalFields(t *testing.T) {
	raw := `{"expressions":[{"source_turn_ids":["u1"],"original":"I want two bread","english":"I'd like two rolls, please.","chinese":"我想要两个小面包。","reading_guide":{"groups":[`
	preview := checkedPreview(suggestionPrefix(raw), snapshotVoice(voiceLog(t, true), testThread, testVoice))
	if len(preview) != 1 {
		t.Fatal("Phrase waited for incomplete annotations", preview)
	}
	if a, _ := arrayPrefix(`{"data":{"translations":[{}]}}`, "translations", 5); len(a) > 0 {
		t.Fatal("Nested field accepted")
	}
}
func TestSourcePartialUTF8AndCumulativeRevision(t *testing.T) {
	root := testRoot(t)
	source := voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, source, defaultModel, true)
	l.readTail(s)
	if integer(l.view(M{})["total"]) != 3 {
		t.Fatal("missing source rows")
	}
	r := M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:02Z", "payload": M{"type": "transcript_segment", "realtime_session_id": testVoice, "id": "u3", "role": "user", "text": "车厘子"}}
	raw := []byte(compact(r) + "\n")
	cut := strings.Index(string(raw), "车") + 1
	f, e := os.OpenFile(source, os.O_APPEND|os.O_WRONLY, 0600)
	must(e)
	f.Write(raw[:cut])
	f.Close()
	l.readTail(l.active())
	if integer(l.view(M{})["total"]) != 3 {
		t.Fatal("Consumed partial UTF8")
	}
	f, e = os.OpenFile(source, os.O_APPEND|os.O_WRONLY, 0600)
	must(e)
	f.Write(raw[cut:])
	f.Close()
	l.readTail(l.active())
	if integer(l.view(M{})["total"]) != 4 {
		t.Fatal("Lost completed partial line")
	}
	appendSegment(source, "u3", "user", "车厘子怎么说")
	l.readTail(l.active())
	rows := arr(l.view(M{})["items"])
	if str(obj(rows[len(rows)-1])["text"]) != "车厘子怎么说" {
		t.Fatal("Cumulative update lost")
	}
	appendSegment(source, "u3", "user", "unrelated text")
	reject(t, func() { l.readTail(l.active()) })
}
func TestExactBindingAndClosedSnapshot(t *testing.T) {
	root := testRoot(t)
	source := voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	reject(t, func() { l.bind("33333333-3333-4333-8333-333333333333", source, defaultModel, true) })
	l.bind(testThread, source, defaultModel, true)
	other := voiceLog(t, false)
	reject(t, func() { l.bind(testThread, other, defaultModel, true) })
	reject(t, func() { snapshotVoice(source, testThread, testVoice) })
	appendClose(source)
	snap := snapshotVoice(source, testThread, testVoice)
	if len(arr(snap["segments"])) != 3 {
		t.Fatal(snap)
	}
}
func TestTranslationFailureDoesNotStopIngestion(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	source := voiceLog(t, false)
	fakeCodex(t, "account-error")
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, source, defaultModel, true)
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { defer close(done); runTranslations(ctx, root) }()
	defer func() { cancel(); <-done }()
	l.readTail(s)
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) && l.active()["translation_status"] != "unavailable" {
		time.Sleep(20 * time.Millisecond)
	}
	require(l.active()["translation_status"] == "unavailable", "Expected isolated translation failure")
	appendSegment(source, "u3", "user", "How much is it?")
	l.readTail(l.active())
	if integer(l.view(M{})["total"]) != 4 || l.active()["desired"] == "stopped" || l.active()["status"] == "error" {
		t.Fatal("Translation stopped transcript ingestion", l.active())
	}
}
func TestStaleTranslationAndTeachingRejected(t *testing.T) {
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, voiceLog(t, false), defaultModel, true)
	l.readTail(s)
	run := str(s["id"])
	l.translated(run, A{M{"id": "u1", "chinese": "错误旧译文"}}, 1, M{"u1": "old text"})
	rows := query(l.db, "SELECT chinese FROM segments WHERE run=? AND id='u1'", run)
	if obj(rows[0])["chinese"] != nil {
		t.Fatal("Stale translation committed")
	}
	hint := M{"kind": "help", "source_id": "u1", "quote": "I want", "english": "I'd like two rolls.", "chinese": "我想要两个小面包。", "next_cue": "", "groups": stringsA("I'd like two rolls.")}
	if validateHint(hint, arr(l.teachingContext(run)["conversation"])) != nil {
		t.Fatal("Stale hint accepted")
	}
}
func TestBackupRestoreAndTamper(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	commitRecord(root, fixtureRecord())
	before := treeFingerprint(root)
	blob, manifest := backupBytes(root, "", false)
	target := filepath.Join(t.TempDir(), "restored")
	result := restoreBackup(blob, target, false)
	if !equal(result["counts"], manifest["counts"]) {
		t.Fatal("Lost records")
	}
	if !equal(before, treeFingerprint(root)) {
		t.Fatal("Source changed")
	}
	reject(t, func() { restoreBackup(blob, target, false) })
	damaged := append([]byte{}, blob...)
	damaged[len(damaged)/2] ^= 0xFF
	reject(t, func() { inspectBackup(damaged) })
}
func TestBackupIncludesConsistentSQLiteAndDetaches(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	l := openLive(root)
	source := voiceLog(t, false)
	s := l.bind(testThread, source, defaultModel, true)
	l.readTail(s)
	l.patch(str(s["id"]), M{"status": "ended", "desired": "stopped"})
	l.close()
	blob, m := backupBytes(root, "", true)
	if !truth(m["includes_live"]) {
		t.Fatal("Missing SQLite")
	}
	target := filepath.Join(t.TempDir(), "restored")
	restoreBackup(blob, target, false)
	cache := openLive(target)
	defer cache.close()
	if integer(cache.view(M{})["total"]) != 3 || cache.active()["source"] != "" || cache.active()["desired"] != "stopped" {
		t.Fatal("Runtime was not detached")
	}
}
func testHTTP(t *testing.T, root string) (*Server, *httptest.Server) {
	t.Helper()
	s := newServer(root, false)
	h := httptest.NewServer(s)
	_, port, e := net.SplitHostPort(strings.TrimPrefix(h.URL, "http://"))
	must(e)
	s.port = clampInt(port, 0, 0, 65535)
	t.Cleanup(h.Close)
	return s, h
}
func TestHTTPHostOriginAndStorageToken(t *testing.T) {
	root := testRoot(t)
	s, h := testHTTP(t, root)
	r, e := http.Get(h.URL + "/api/overview")
	must(e)
	r.Body.Close()
	if r.StatusCode != 200 {
		t.Fatal(r.Status)
	}
	for _, test := range []struct{ host, origin, token string }{{"evil.invalid", "", ""}, {"", "https://evil.invalid", s.archive.token}, {"", "", "bad"}} {
		req, e := http.NewRequest("POST", h.URL+"/api/storage/open", strings.NewReader("{}"))
		must(e)
		if test.host != "" {
			req.Host = test.host
		}
		req.Header.Set("Origin", test.origin)
		req.Header.Set("X-Coach-Token", test.token)
		req.Header.Set("Content-Type", "application/json")
		resp, e := http.DefaultClient.Do(req)
		must(e)
		resp.Body.Close()
		if resp.StatusCode != 403 {
			t.Fatal("CSRF accepted", test, resp.Status)
		}
	}
}
func TestFreshSceneAndSavedCorrectionPreferences(t *testing.T) {
	root := testRoot(t)
	c := resumeContext(root, today(), "", nil)
	scene := chooseScene(root, c)
	rememberScene(root, "first", scene)
	next := chooseScene(root, c)
	if equal(scene, next) {
		t.Fatal("Repeated scene")
	}
	c = speakingContext(profileDefault(), true, "scene", scene)
	if strings.Contains(str(c["voice_brief"]), "Introduce this fresh scene once in English: 今天") {
		t.Fatal("Written Chinese used as spoken opening")
	}
	p := profileDefault()
	p["correction"] = "after_scene"
	c = speakingContext(p, true, "scene", scene)
	if obj(c["policy"])["english_structure_help"] != "after_scene" {
		t.Fatal("Saved correction preference changed")
	}
}
func fakeCodex(t *testing.T, mode string) {
	t.Helper()
	exe, e := os.Executable()
	must(e)
	t.Setenv("ENGLISH_COACH_CODEX", exe)
	t.Setenv("ENGLISH_COACH_TEST_HELPER", "1")
	t.Setenv("ENGLISH_COACH_TEST_MODE", mode)
}
func TestModelProtocolAndFailureBoundary(t *testing.T) {
	for _, mode := range []string{"good", "account-error", "tool-request", "model-mismatch"} {
		t.Run(mode, func(t *testing.T) {
			t.Setenv("CODEX_HOME", t.TempDir())
			fakeCodex(t, mode)
			c := newModelClient(defaultModel, 3*time.Second)
			defer c.close()
			err := attempt(func() { c.connect(context.Background()); c.generate(context.Background(), M{}, M{}, nil) })
			if (mode == "good") != (err == nil) {
				t.Fatalf("mode=%s error=%v", mode, err)
			}
		})
	}
}
func TestMain(m *testing.M) {
	if os.Getenv("ENGLISH_COACH_TEST_HELPER") == "1" {
		fakeModelServer()
		return
	}
	os.Exit(m.Run())
}
func fakeModelServer() {
	for _, a := range os.Args {
		if a == "--help" {
			fmt.Println("app-server --listen stdio://")
			return
		}
	}
	mode := os.Getenv("ENGLISH_COACH_TEST_MODE")
	send := func(v M) { fmt.Println(compact(v)) }
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 65536), 16*1024*1024)
	for scanner.Scan() {
		row := parseObject(scanner.Text())
		id := row["id"]
		if id == nil {
			continue
		}
		var result M
		switch row["method"] {
		case "initialize":
			result = M{}
		case "account/read":
			typ := "chatgpt"
			if mode == "account-error" {
				typ = "apiKey"
			}
			result = M{"account": M{"type": typ}}
		case "model/list":
			result = M{"data": A{M{"model": defaultModel, "supportedReasoningEfforts": A{M{"reasoningEffort": "low"}}}}, "nextCursor": nil}
		case "thread/start":
			model := defaultModel
			if mode == "model-mismatch" {
				model = "other"
			}
			result = M{"model": model, "thread": M{"id": "test-thread"}}
		case "turn/start":
			send(M{"id": id, "result": M{"turn": M{"id": "test-turn"}}})
			if mode == "tool-request" {
				send(M{"id": 99, "method": "item/commandExecution/requestApproval", "params": M{}})
				continue
			}
			answer := "{}"
			if mode == "translation-poison" || mode == "content-malformed" {
				payload := parseObject(str(obj(arr(obj(row["params"])["input"])[0])["text"]))
				translations := A{}
				for _, v := range arr(payload["units"]) {
					u := obj(v)
					x := M{"id": u["id"], "kind": "translation", "chinese": "虚构测试译文"}
					if u["text"] == "backpack" {
						x["kind"], x["chinese"] = "translation", "backpack"
					}
					translations = append(translations, x)
				}
				answer = compact(M{"translations": translations})
				if mode == "content-malformed" {
					for _, unit := range arr(payload["units"]) {
						if obj(unit)["text"] == "broken" {
							answer = "{broken"
						}
					}
				}
			}
			send(M{"method": "item/completed", "params": M{"turnId": "test-turn", "item": M{"type": "agentMessage", "phase": "final_answer", "text": answer}}})
			send(M{"method": "turn/completed", "params": M{"turn": M{"id": "test-turn", "status": "completed"}}})
			continue
		default:
			result = M{}
		}
		send(M{"id": id, "result": result})
	}
}

func TestBadCLIAndMissingRootDoNotInitialize(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	reject(t, func() { runCLI([]string{"typo-command"}) })
	if exists(defaultRoot()) {
		t.Fatal("Unknown command created an archive")
	}
}
func TestTransientTranslationDisconnectCanRetry(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	source := voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, source, defaultModel, true)
	l.patch(str(s["id"]), M{"translation_status": "unavailable", "translation_error": "Offline", "translation_failures": 3})
	l.readTail(l.active())
	l.retry(str(s["id"]))
	if l.active()["desired"] != "running" || !truth(l.active()["translation_retry"]) {
		t.Fatal("Retry changed source binding")
	}
}
func TestNativeSourceCloseRegistersReviewWithoutTranslation(t *testing.T) {
	root := testRoot(t)
	source := voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, source, defaultModel, true)
	l.patch(str(s["id"]), M{"auto_review": true, "translation_status": "unavailable", "translation_error": "Offline"})
	appendClose(source)
	l.readTail(l.active())
	jobs := recentReviews(root)
	if len(jobs) != 1 || obj(jobs[0])["voice_id"] != testVoice || !truth(obj(jobs[0])["auto_review"]) {
		t.Fatal("Review depended on translation", jobs)
	}
}
func TestStoragePlanRejectsChangedSource(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	saveConfiguration(root, "")
	s := newServer(root, true)
	target := filepath.Join(t.TempDir(), "moved")
	plan := s.previewStorage(M{"action": "move", "destination": target})
	commitRecord(root, fixtureRecord())
	reject(t, func() { s.applyStorage(M{"plan": plan["plan"]}) })
	if exists(target) || workspace("")["data_root"] != root {
		t.Fatal("Changed archive was moved")
	}
}
func TestStorageSwitchRotatesTokenAndKeepsSource(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	commitRecord(root, fixtureRecord())
	saveConfiguration(root, "")
	s := newServer(root, true)
	target := filepath.Join(t.TempDir(), "moved")
	plan := s.previewStorage(M{"action": "move", "destination": target})
	oldToken := s.archive.token
	s.applyStorage(M{"plan": plan["plan"]})
	defer s.stopBackground()
	if s.archive.root != absolute(target) || s.archive.token == oldToken || !exists(filepath.Join(root, "Sessions", "SES-20260908-001.md")) {
		t.Fatal("Switch lost source or retained stale token")
	}
}
func TestRealModelTranslation(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_MODEL_TEST") != "1" {
		t.Skip("Explicit development integration opt-in required")
	}
	c := newModelClient(defaultModel, 45*time.Second)
	defer c.close()
	c.instructions = str(contracts["translation_instructions"]) + str(contracts["teaching_instructions"])
	ctx, cancel := context.WithTimeout(context.Background(), 70*time.Second)
	defer cancel()
	rows := A{M{"id": "u1", "role": "user", "text": "I want buy two bread rolls for breakfast."}}
	out, hint, rejected, seconds := c.translate(ctx, rows, M{"conversation": rows, "scene": M{"setting": "A bakery"}, "profile": M{"correction": "in_character", "help_language": "zh-CN", "input_support": "short_turns"}}, nil)
	if len(rejected) > 0 {
		t.Fatalf("Rejected translations: %v", rejected)
	}
	if len(out) != 1 || !hanRE.MatchString(str(obj(out[0])["chinese"])) || hint == nil || hint["kind"] != "help" {
		t.Fatal("Unexpected translation/teaching", out, hint)
	}
	t.Logf("Real isolated account integration: %.2fs, translation=%v hint=%v", seconds, out, hint)
}

func TestRealReviewIntegration(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_REVIEW_TEST") != "1" {
		t.Skip("Explicit development integration opt-in required")
	}
	root := testRoot(t)
	source := voiceLog(t, true)
	job := enqueueReview(root, testThread, testVoice, source, false)
	ctx, cancel := context.WithTimeout(context.Background(), 160*time.Second)
	defer cancel()
	processReview(ctx, root, job)
	status := reviewStatus(root, testThread, testVoice)
	if status["status"] != "saved" {
		t.Fatalf("Review failed: %v", status)
	}
	state := buildState(root)
	if len(arr(state["sessions"])) != 1 {
		t.Fatal("Review was not saved exactly once")
	}
	c := obj(obj(arr(state["sessions"])[0])["review_coverage"])
	if integer(c["available_learner_turns"]) != 2 || integer(c["word_assessed_turns"]) != 2 {
		t.Fatal("Incomplete review coverage", c)
	}
	t.Logf("Real isolated review: timing=%v, expressions=%d", status["timing"], len(arr(state["expressions"])))
}

func TestRuntimeBuildWithoutLanguageInterpreters(t *testing.T) {
	if testing.Short() {
		t.Skip("standalone build")
	}
	tmp := t.TempDir()
	binary := filepath.Join(tmp, "english-coach")
	if runtime.GOOS == "windows" {
		binary += ".exe"
	}
	build := exec.Command("go", "build", "-o", binary, ".")
	build.Env = append(os.Environ(), "CGO_ENABLED=0")
	if out, e := build.CombinedOutput(); e != nil {
		t.Fatalf("build: %v %s", e, out)
	}
	emptyPath := filepath.Join(tmp, "empty-path")
	mkdir(emptyPath)
	root := filepath.Join(tmp, "学习档案")
	run := func(args ...string) M {
		cmd := exec.Command(binary, args...)
		cmd.Env = append(os.Environ(), "PATH="+emptyPath, "CODEX_HOME="+filepath.Join(tmp, "codex"))
		b, e := cmd.CombinedOutput()
		if e != nil {
			t.Fatalf("standalone %v: %v %s", args, e, b)
		}
		return parseObject(string(b))
	}
	run("init", "--root", root)
	result := run("validate", "--root", root)
	if !truth(result["ok"]) {
		t.Fatal(result)
	}
	w := run("paths")
	if within(str(w["data_root"]), filepath.Dir(binary)) { /* CODEX_HOME explicitly lives in test temp; archive still outside Skill bin. */
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	cmd := exec.CommandContext(ctx, binary, "serve", "--root", root, "--port", "0")
	cmd.Env = append(os.Environ(), "PATH="+emptyPath, "CODEX_HOME="+filepath.Join(tmp, "codex"))
	stdout, e := cmd.StdoutPipe()
	must(e)
	cmd.Stderr = os.Stderr
	must(cmd.Start())
	t.Cleanup(func() {
		cancel()
		_ = cmd.Wait()
	})
	scanner := bufio.NewScanner(stdout)
	line := make(chan string, 1)
	go func() {
		if scanner.Scan() {
			line <- scanner.Text()
		}
	}()
	var base string
	select {
	case s := <-line:
		base = strings.TrimPrefix(s, "English learning archive: ")
	case <-time.After(10 * time.Second):
		t.Fatal("Standalone service did not start")
	}
	// The listening announcement precedes lazy SQLite initialization. A cold
	// Windows runner can exceed the CLI's two-second probe while this finishes.
	// Wait for actual API readiness within a bounded startup budget; validate
	// response contents below so retries cannot conceal a wrong response.
	ready := func(path string) M {
		t.Helper()
		deadline := time.Now().Add(10 * time.Second)
		for {
			var data M
			err := attempt(func() { data = fetchJSON(base + path) })
			if err == nil {
				return data
			}
			if time.Now().After(deadline) {
				t.Fatalf("Standalone API %s did not become ready: %v", path, err)
			}
			time.Sleep(100 * time.Millisecond)
		}
	}
	identity := ready("/api/identity")
	overview := ready("/api/overview")
	live := ready("/api/live")
	if identity["runtime"] != "go" || integer(obj(overview["counts"])["sessions"]) != 0 || integer(live["total"]) != 0 {
		t.Fatal(identity, overview, live)
	}
}

func TestReviewWatchWorksWithCaptionsDisabled(t *testing.T) {
	root := testRoot(t)
	source := voiceLog(t, false)
	path := filepath.Join(root, "Runtime", "ReviewWatches", "disabled.json")
	writeJSON(path, M{"watch_only": true, "thread_id": testThread, "source": source, "cursor": 0, "created_epoch": epoch(), "title": "Fictional practice"})
	registerReviewWatches(root)
	jobs := recentReviews(root)
	if len(jobs) != 1 || obj(jobs[0])["voice_id"] != testVoice || exists(path) {
		t.Fatal("Independent review registration failed", jobs)
	}
	if exists(filepath.Join(root, "Live")) {
		t.Fatal("Disabled captions were initialized")
	}
}
func TestFragmentAnnotationsPreserveRawEvidence(t *testing.T) {
	rows := A{M{"id": "1", "role": "assistant", "text": "a block", "timestamp": "2026-09-08T01:00:00Z"}, M{"id": "2", "role": "assistant", "text": "- buster", "timestamp": "2026-09-08T01:00:01Z"}, M{"id": "3", "role": "assistant", "text": ". continued", "timestamp": "2026-09-08T01:00:02Z"}}
	out := annotateFragments(rows)
	if obj(obj(out[1])["fragment"])["joined_word"] != "blockbuster" || obj(out[1])["text"] != "- buster" || obj(obj(out[2])["fragment"])["kind"] != "continuation" {
		t.Fatal(out)
	}
}
func TestReviewSchemaPreservesStreamingOrder(t *testing.T) {
	var schema struct {
		Properties map[string]json.RawMessage `json:"properties"`
	}
	must(json.Unmarshal(rawContracts["review_schema"], &schema))
	raw := string(rawContracts["review_schema"])
	if strings.Index(raw, `"expressions"`) > strings.Index(raw, `"word_checks"`) {
		t.Fatal("Expressions no longer first")
	}
	expression := string(schema.Properties["expressions"])
	if strings.Index(expression, `"source_turn_ids"`) > strings.Index(expression, `"reading_guide"`) {
		t.Fatal("Quote fields moved behind slow optional fields")
	}
}
