package main

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestCaptionPublishesBeforeFollowingUtteranceCompletes(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	fakeCodex(t, "stream-captions")
	c := newModelClient(defaultCaptionModel, 5*time.Second)
	defer c.close()
	var first time.Time
	var early A
	out, bad, _ := c.translate(context.Background(), A{M{"id": "short", "text": "Yes."}, M{"id": "long", "text": "Could I move to a quieter room, please?"}}, func(rows A, _ float64) {
		if first.IsZero() {
			first, early = time.Now(), rows
		}
	})
	if len(out) != 2 || len(bad) > 0 || len(early) != 1 || obj(early[0])["id"] != "short" || time.Since(first) < 500*time.Millisecond {
		t.Fatal("A complete sentence waited for the rest of the array", out, early, bad)
	}
}

func TestCaptionContextReusesThenReleasesConversation(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	fakeCodex(t, "translation-poison")
	trace := filepath.Join(t.TempDir(), "requests.jsonl")
	atomicWrite(trace, nil)
	t.Setenv("ENGLISH_COACH_TEST_REQUESTS", trace)
	c := newModelClient(defaultCaptionModel, 3*time.Second)
	c.maxTurns = 2
	defer c.close()
	for i := 0; i < 3; i++ {
		out, bad, _ := c.translate(context.Background(), A{M{"id": "u", "role": "user", "text": "Thank you."}}, nil)
		if len(out) != 1 || len(bad) > 0 {
			t.Fatal(out, bad)
		}
	}
	starts, ends := 0, 0
	for _, line := range strings.Split(strings.TrimSpace(string(readFile(trace))), "\n") {
		r := parseObject(line)
		if r["method"] == "thread/start" {
			starts++
		}
		if r["method"] == "thread/unsubscribe" {
			ends++
		}
		if r["method"] == "turn/start" {
			p := parseObject(str(obj(arr(obj(r["params"])["input"])[0])["text"]))
			if p["teaching_context"] != nil || len(arr(p["prior_context"])) > 4 {
				t.Fatal("Caption prompt accumulated teaching context", p)
			}
		}
	}
	if starts != 2 || ends != 1 {
		t.Fatal("Conversation lifetime not bounded", starts, ends)
	}
}

func TestLateInvalidationRevokesOnlyRequestedSourceVersion(t *testing.T) {
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	id := str(l.bind(testThread, voiceLog(t, false), defaultCaptionModel, true)["id"])
	l.insertSegments(id, A{M{"id": "u", "role": "user", "text": "I need a room."}, M{"id": "v", "role": "assistant", "text": "Of course."}})
	l.batch(id, false)
	expected := M{"u": "I need a room.", "v": "Of course."}
	l.translated(id, A{M{"id": "u", "chinese": "我需要一个房间。"}, M{"id": "v", "chinese": "当然。"}}, 1, expected)
	l.rejectTranslations(id, M{"u": "duplicate unit"}, expected)
	rows := query(l.db, "SELECT * FROM segments WHERE run=? ORDER BY seq", id)
	if obj(rows[0])["status"] != "pending" || obj(rows[0])["chinese"] != nil || obj(rows[1])["status"] != "translated" {
		t.Fatal(rows)
	}
	l.insertSegments(id, A{M{"id": "u", "role": "user", "text": "I need a room. A quiet one."}})
	l.translated(id, A{M{"id": "u", "chinese": "我需要一间安静的房间。"}}, 1, M{"u": "I need a room. A quiet one."})
	l.rejectTranslations(id, M{"u": "late old error"}, expected)
	if integer(l.counts(id)["translated"]) != 2 {
		t.Fatal("Stale failure revoked revised text")
	}
}

func TestLiveServiceNeverStartsPredictionWorker(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	fakeCodex(t, "translation-poison")
	trace := filepath.Join(t.TempDir(), "requests.jsonl")
	atomicWrite(trace, nil)
	t.Setenv("ENGLISH_COACH_TEST_REQUESTS", trace)
	root := testRoot(t)
	l := openLive(root)
	id := str(l.bind(testThread, voiceLog(t, false), defaultCaptionModel, true)["id"])
	l.setMeta("hint:"+id, compact(M{"english": "obsolete prediction"}))
	l.patch(id, M{"teaching_status": "generating", "teaching_error": "obsolete"})
	l.close()

	server := newServer(root, true)
	server.startBackground()
	defer server.stopBackground()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		check := openLive(root)
		done := integer(check.counts(id)["translated"]) > 0
		check.close()
		if done {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	server.stopBackground()
	check := openLive(root)
	defer check.close()
	view := check.view(M{"run": id})
	if _, ok := view["teaching"]; ok || check.meta("hint:"+id) != nil {
		t.Fatal("Live API retained prediction output", view)
	}
	state := obj(view["state"])
	if state["teaching_status"] != nil || state["teaching_error"] != nil {
		t.Fatal("Live API retained prediction state", state)
	}
	turns := 0
	for _, line := range strings.Split(strings.TrimSpace(string(readFile(trace))), "\n") {
		if line == "" {
			continue
		}
		r := parseObject(line)
		if r["method"] != "turn/start" {
			continue
		}
		turns++
		payload := parseObject(str(obj(arr(obj(r["params"])["input"])[0])["text"]))
		if payload["teaching_context"] != nil {
			t.Fatal("Prediction model request was started", payload)
		}
	}
	if turns == 0 {
		t.Fatal("Test did not observe a caption model request")
	}
}

func TestAutomaticRetryWaitsForDrainAndFreshCaptionsWin(t *testing.T) {
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	id := str(l.bind(testThread, voiceLog(t, false), defaultCaptionModel, true)["id"])
	l.insertSegments(id, A{M{"id": "bad", "role": "user", "text": "broken"}})
	first := l.batch(id, false)
	if len(first) != 1 || obj(first[0])["id"] != "bad" {
		t.Fatal(first)
	}
	l.failBatch(id, first)
	l.insertSegments(id, A{M{"id": "fresh", "role": "assistant", "text": "A fresh valid caption."}})
	next := l.batch(id, false)
	if len(next) != 1 || obj(next[0])["id"] != "fresh" {
		t.Fatal("Deferred retry blocked a fresh caption", next)
	}
	l.translated(id, A{M{"id": "fresh", "chinese": "一条新的有效字幕。"}}, 0.1, M{"fresh": "A fresh valid caption."})
	if queued := l.batch(id, false); len(queued) != 0 {
		t.Fatal("Automatic retry entered the active model lane", queued)
	}
	bad := obj(query(l.db, "SELECT status,attempts FROM segments WHERE run=? AND id='bad'", id)[0])
	if bad["status"] != "pending" || integer(bad["attempts"]) != 1 {
		t.Fatal("Failed row did not remain recoverable", bad)
	}
	l.patch(id, M{"close_epoch": epoch(), "desired": "drain"})
	retry := l.batch(id, true)
	if len(retry) != 1 || obj(retry[0])["id"] != "bad" {
		t.Fatal("Drain did not recover the deferred retry", retry)
	}
	l.failBatch(id, retry)
	if integer(l.counts(id)["failed"]) != 1 || integer(l.counts(id)["translated"]) != 1 {
		t.Fatal("Failure isolation changed during drain", l.counts(id))
	}
}

func TestCaptionAndReviewModelsSeparated(t *testing.T) {
	if defaultCaptionModel != "gpt-5.6-luna" || defaultReviewModel != "gpt-5.6-sol" || defaultCaptionModel == defaultReviewModel {
		t.Fatal(defaultCaptionModel, defaultReviewModel)
	}
}

func TestRealCaptionModelLatencyComparison(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_LATENCY_TEST") != "1" {
		t.Skip("Explicit account comparison only")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	models := []string{defaultReviewModel, defaultCaptionModel}
	clients := map[string]*ModelClient{}
	totals := map[string]float64{}
	for _, model := range models {
		client := newModelClient(model, 45*time.Second)
		client.maxTurns = 8
		client.connect(ctx)
		clients[model] = client
		defer client.close()
	}
	batches := []A{
		{M{"id": "u1", "role": "user", "text": "I want talk with you, but I don't know how to say it."}, M{"id": "a1", "role": "assistant", "text": "Tell me what happened at the hotel."}},
		{M{"id": "u2", "role": "user", "text": "Okay. 我的房间有点吵。 uh"}, M{"id": "a2", "role": "assistant", "text": "Take your time."}},
		{M{"id": "u3", "role": "user", "text": "It isn't noisy now. It's quiet."}, M{"id": "a3", "role": "assistant", "text": "I understand. What would you like me to help with?"}},
		{M{"id": "u4", "role": "user", "text": "Could I change to quieter room, please?"}, M{"id": "a4", "role": "assistant", "text": "Of course. Let me check which rooms are available."}},
	}
	for i, rows := range batches {
		order := append([]string{}, models...)
		if i%2 == 1 {
			order[0], order[1] = order[1], order[0]
		}
		for _, model := range order {
			first := 0.0
			out, bad, total := clients[model].translate(ctx, rows, func(_ A, seconds float64) {
				if first == 0 {
					first = seconds
				}
			})
			if len(out) != len(rows) || len(bad) > 0 {
				t.Fatal(model, out, bad)
			}
			totals[model] += total
			t.Logf("sample=%d model=%s first=%.3f total=%.3f translations=%s", i, model, first, total, compact(out))
		}
	}
	t.Logf("caption model totals: %s=%.3fs %s=%.3fs", defaultReviewModel, totals[defaultReviewModel], defaultCaptionModel, totals[defaultCaptionModel])
}
