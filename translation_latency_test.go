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
	c := newModelClient(defaultModel, 5*time.Second)
	defer c.close()
	var first time.Time
	var early A
	out, _, bad, _ := c.translate(context.Background(), A{M{"id": "short", "text": "Yes."}, M{"id": "long", "text": "Could I move to a quieter room, please?"}}, nil, func(rows A, _ float64) {
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
	c := newModelClient(defaultModel, 3*time.Second)
	c.maxTurns = 2
	defer c.close()
	for i := 0; i < 3; i++ {
		out, _, bad, _ := c.translate(context.Background(), A{M{"id": "u", "role": "user", "text": "Thank you."}}, nil, nil)
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
	id := str(l.bind(testThread, voiceLog(t, false), defaultModel, true)["id"])
	l.insertSegments(id, A{M{"id": "u", "role": "user", "text": "I need a room."}, M{"id": "v", "role": "assistant", "text": "Of course."}})
	l.batch(id)
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

func TestTeachingCannotBlockCaptionsAndDiscardsObsoleteTurn(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	fakeCodex(t, "latency-lanes")
	marker, release := filepath.Join(t.TempDir(), "started"), filepath.Join(t.TempDir(), "release")
	t.Setenv("ENGLISH_COACH_TEST_HINT_STARTED", marker)
	t.Setenv("ENGLISH_COACH_TEST_HINT_RELEASE", release)
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	id := str(l.bind(testThread, voiceLog(t, false), defaultModel, true)["id"])
	l.insertSegments(id, A{M{"id": "old", "role": "user", "text": "I want quieter room."}})
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	translations, teaching := make(chan struct{}), make(chan struct{})
	go func() { defer close(translations); runTranslations(ctx, root) }()
	go func() { defer close(teaching); runTeaching(ctx, root) }()
	defer func() { cancel(); <-translations; <-teaching }()
	wait := func(check func() bool) {
		t.Helper()
		for !check() && ctx.Err() == nil {
			time.Sleep(20 * time.Millisecond)
		}
		if ctx.Err() != nil {
			t.Fatal("Worker did not progress", l.run(id))
		}
	}
	wait(func() bool { return exists(marker) && integer(l.counts(id)["translated"]) == 1 })
	// The teaching model is deliberately held indefinitely. Another subtitle
	// must still be translated without releasing that response.
	l.insertSegments(id, A{M{"id": "coach", "role": "assistant", "text": "What is the problem?"}})
	wait(func() bool { return integer(l.counts(id)["translated"]) == 2 })
	if l.meta("hint:"+id) != nil {
		t.Fatal("Blocked hint was somehow published")
	}
	l.insertSegments(id, A{M{"id": "new", "role": "user", "text": "I need a quiet room, please."}})
	wait(func() bool { return string(readFile(marker)) == "new" && integer(l.counts(id)["translated"]) == 3 })
	atomicWrite(release, nil)
	wait(func() bool { return l.meta("hint:"+id) != nil })
	if parseObject(str(l.meta("hint:" + id)))["source_id"] != "new" {
		t.Fatal("Obsolete hint was retained")
	}
	// The same learner intent is served once; source close hides the hint.
	l.patch(id, M{"close_epoch": epoch()})
	if l.currentTeachingKey(id) != "" || l.view(M{})["teaching"] != nil {
		t.Fatal("Closed practice kept teaching")
	}
}

func TestRealCaptionLatencyComparison(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_LATENCY_TEST") != "1" {
		t.Skip("Explicit account comparison only")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	combined := newModelClient(defaultModel, 45*time.Second)
	combined.instructions += str(contracts["teaching_instructions"])
	fast := newModelClient(textOr(os.Getenv("ENGLISH_COACH_CAPTION_MODEL"), defaultModel), 45*time.Second)
	fast.maxTurns = 8
	defer combined.close()
	defer fast.close()
	if os.Getenv("ENGLISH_COACH_CAPTION_MODEL") == "" {
		combined.connect(ctx)
	}
	fast.connect(ctx)
	batches := []A{
		{M{"id": "u1", "role": "user", "text": "I want talk with you, but I don't know how to say it."}, M{"id": "a1", "role": "assistant", "text": "Tell me what happened at the hotel."}},
		{M{"id": "u2", "role": "user", "text": "Okay. 我的房间有点吵。 uh"}, M{"id": "a2", "role": "assistant", "text": "Take your time."}},
		{M{"id": "u3", "role": "user", "text": "It isn't noisy now. It's quiet."}, M{"id": "a3", "role": "assistant", "text": "I understand. What would you like me to help with?"}},
		{M{"id": "u4", "role": "user", "text": "Could I change to quieter room, please?"}, M{"id": "a4", "role": "assistant", "text": "Of course. Let me check which rooms are available."}},
	}
	conversation := A{}
	for i, rows := range batches {
		conversation = append(conversation, rows...)
		order := []string{"combined", "captions"}
		if i%2 == 1 {
			order = []string{"captions", "combined"}
		}
		if os.Getenv("ENGLISH_COACH_CAPTION_MODEL") != "" {
			order = []string{"captions"}
		}
		for _, mode := range order {
			c, help := fast, M(nil)
			if mode == "combined" {
				c = combined
				help = M{"conversation": conversation, "scene": M{"setting": "A hotel reception"}, "profile": M{"correction": "in_character", "input_support": "short_turns"}}
			}
			first := 0.0
			out, _, bad, total := c.translate(ctx, rows, help, func(_ A, seconds float64) {
				if first == 0 {
					first = seconds
				}
			})
			if len(out) != len(rows) || len(bad) > 0 {
				t.Fatal(mode, out, bad)
			}
			t.Logf("sample=%d mode=%s first=%.3f total=%.3f translations=%s", i, mode, first, total, compact(out))
		}
	}
}

func TestRealSeparateTeachingPreservesChangedIntent(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_LATENCY_TEST") != "1" {
		t.Skip("Explicit account comparison only")
	}
	c := newModelClient(defaultModel, 25*time.Second)
	c.freshTurns = true
	c.instructions = "Return only the requested JSON teaching object. Do not translate transcripts or use tools. " + str(contracts["teaching_instructions"])
	defer c.close()
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	defer cancel()
	for _, text := range []string{"It isn't noisy now. It's quiet. I want to talk about something else.", "空调在滴水，我不知道怎么说。"} {
		rows := A{M{"id": "coach", "role": "assistant", "text": "You are a hotel guest. What is the room problem?"}, M{"id": "learner", "role": "user", "text": text}}
		start := time.Now()
		hint := c.teach(ctx, M{"conversation": rows, "scene": M{"setting": "A hotel front desk", "goal": "Ask for a quieter room"}, "profile": M{"correction": "in_character", "input_support": "short_turns"}})
		t.Logf("input=%s hint=%s seconds=%.2f", text, compact(hint), time.Since(start).Seconds())
		if hint == nil && hanRE.MatchString(text) {
			t.Fatal("Missing help for an unresolved intent")
		}
	}
}
