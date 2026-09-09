package main

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestNamePreservationDoesNotGuessFromCasing(t *testing.T) {
	for _, text := range []string{"iPad", "eBay", "adidas", "St. Louis", "Bank of America", "NASA"} {
		rows := A{M{"id": "u1", "text": "这个 " + text + " 多大？"}}
		units := translationUnits(rows)
		out := assembleTranslations(rows, units, A{M{"id": obj(units[0])["id"], "kind": "name", "chinese": text}})
		if obj(out[0])["chinese"] != "这个 "+text+"（专名原文） 多大？" {
			t.Fatal(out)
		}
		for _, changed := range []string{strings.ToUpper(text), text + "2", text + "解释"} {
			if changed == text {
				continue
			}
			reject(t, func() {
				assembleTranslations(rows, units, A{M{"id": obj(units[0])["id"], "kind": "name", "chinese": changed}})
			})
		}
	}
	// Names are a semantic model judgment. Deterministic validation proves
	// identity/coverage, not a dictionary classification based on letter case.
}

func TestDevelopmentExecutableFolderIsNotLegacySkillData(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root := testRoot(t)
	t.Setenv("ENGLISH_COACH_SKILL_ROOT", filepath.Dir(root))
	if len(recoveryBackup(root)) != 0 {
		t.Fatal("Development data overwrote managed backup")
	}
}

func TestTranslationPoisonRowIsolation(t *testing.T) {
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, voiceLog(t, false), defaultModel, true)
	id := str(s["id"])
	rows := A{M{"id": "good", "role": "assistant", "text": "Good morning."}, M{"id": "bad", "role": "user", "text": "这是 backpack"}, M{"id": "next", "role": "assistant", "text": "Can I help?"}}
	l.insertSegments(id, rows)
	batch := l.batch(id)
	units := translationUnits(batch)
	translations := A{}
	for _, v := range units {
		u := obj(v)
		x := M{"id": u["id"], "kind": "translation", "chinese": "虚构测试译文"}
		if u["segment_id"] == "bad" {
			x["kind"], x["chinese"] = "translation", "backpack"
		}
		translations = append(translations, x)
	}
	out, failed := partialTranslations(batch, units, translations)
	if len(out) != 2 || len(failed) != 1 || failed["bad"] == nil {
		t.Fatal(out, failed)
	}
	l.translated(id, out, 1, M{"good": "Good morning.", "next": "Can I help?"})
	l.failBatch(id, batch)
	l.insertSegments(id, A{M{"id": "new", "role": "user", "text": "Thank you."}})
	retry := l.batch(id)
	if obj(retry[0])["id"] != "new" {
		t.Fatal("Retry blocked newer text", retry)
	}
	l.failBatch(id, retry)
	if integer(l.counts(id)["translated"]) != 2 || integer(l.counts(id)["failed"]) != 1 {
		t.Fatal(l.counts(id))
	}
	if l.run(id)["desired"] != "running" {
		t.Fatal("Poison row stopped source")
	}
	unknown := append(translations, M{"id": "another-run", "kind": "translation", "chinese": "别场文字"})
	out, failed = partialTranslations(batch, units, unknown)
	if len(out) != 0 || len(failed) != 3 {
		t.Fatal("Foreign IDs accepted", out, failed)
	}
}

func TestClosedCaptionRetryCannotStealActiveBinding(t *testing.T) {
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	source := voiceLog(t, false)
	s := l.bind(testThread, source, defaultModel, true)
	id := str(s["id"])
	l.patch(id, M{"status": "ended", "desired": "stopped"})
	reject(t, func() { l.retry(id) }) // a state label is not actual close evidence
	appendClose(source)
	l.setMeta("active", "unrelated")
	l.retry(id)
	l.retry(id)
	if !truth(l.run(id)["recovery_requested"]) || l.meta("active") != "unrelated" {
		t.Fatal("Retry stole source")
	}
	fakeCodex(t, "translation-poison")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	done := make(chan struct{})
	go func() { defer close(done); runCaptionRecoveries(ctx, root) }()
	defer func() { cancel(); <-done }()
	for truth(l.run(id)["recovery_requested"]) && ctx.Err() == nil {
		time.Sleep(20 * time.Millisecond)
	}
	if integer(l.counts(id)["translated"]) != 3 || l.meta("active") != "unrelated" || l.run(id)["status"] != "ended" {
		t.Fatal(l.counts(id), l.run(id))
	}
}

func TestTranslationWorkerContinuesPastPoisonSentence(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	fakeCodex(t, "translation-poison")
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, voiceLog(t, false), defaultModel, true)
	id := str(s["id"])
	l.insertSegments(id, A{M{"id": "bad", "role": "user", "text": "这是 backpack"}, M{"id": "good", "role": "assistant", "text": "Good morning."}})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	done := make(chan struct{})
	go func() { defer close(done); runTranslations(ctx, root) }()
	defer func() { cancel(); <-done }()
	for integer(l.counts(id)["failed"]) == 0 && ctx.Err() == nil {
		time.Sleep(20 * time.Millisecond)
	}
	l.insertSegments(id, A{M{"id": "later", "role": "assistant", "text": "How can I help?"}})
	for integer(l.counts(id)["translated"]) < 2 && ctx.Err() == nil {
		time.Sleep(20 * time.Millisecond)
	}
	if integer(l.counts(id)["translated"]) != 2 || l.run(id)["translation_status"] == "unavailable" || integer(l.run(id)["translation_failures"]) > 0 {
		t.Fatal(l.counts(id), l.run(id))
	}
	if obj(l.run(id)["translation_rejected"])["bad"] == nil {
		t.Fatal("Lost an unresolved sentence's diagnostic")
	}
}

func TestRecoveredDraftDoesNotRegenerateSuppliedSuccess(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	fakeCodex(t, "tool-request") // a needless model call would fail
	root := testRoot(t)
	source := voiceLog(t, true)
	job := enqueueReview(root, testThread, testVoice, source, false)
	draft := fixtureDraft()
	draft["concept_observations"] = A{M{"term": "bread", "meaning": "面包", "dimension": "use", "result": "success", "support": "model", "quote": "bread", "note": "Supplied wording", "source_turn_ids": stringsA("u1"), "expression_indices": A{0}}}
	writeJSON(filepath.Join(root, "Runtime", "Reviews", filepath.Base(reviewFile(root, testThread, testVoice))[:24]+".draft"), draft)
	processReview(context.Background(), root, job)
	status := reviewStatus(root, testThread, testVoice)
	if status["status"] != "saved" {
		t.Fatal(status)
	}
	if obj(status["timing"])["generation_seconds"] != nil {
		t.Fatal("Regenerated a valid source-checked draft")
	}
	obs := obj(arr(obj(arr(buildState(root)["sessions"])[0])["concept_observations"])[0])
	if obs["result"] != "supported" {
		t.Fatal(obs)
	}
}

func TestReviewSuppliedSuccessIsConservativeAndIdempotent(t *testing.T) {
	d := fixtureDraft()
	d["concept_observations"] = A{M{"dimension": "use", "result": "success", "support": "model", "note": "Example", "quote": "I'd like two rolls.", "source_turn_ids": stringsA("u1")}, M{"dimension": "meaning", "result": "success", "support": "none", "note": "Independent"}, M{"dimension": "reading", "result": "success", "support": "model", "modality": "transcript"}}
	out := reconcileReview(d, "zh-CN")
	obs := arr(out["concept_observations"])
	if obj(obs[0])["result"] != "supported" || obj(obs[0])["support"] != "model" || obj(obs[1])["result"] != "success" || obj(obs[2])["result"] != "success" {
		t.Fatal(obs)
	}
	first := compact(out)
	if compact(reconcileReview(out, "zh-CN")) != first {
		t.Fatal("Repeated normalization adds evidence")
	}
	// The reading claim is untouched: downstream audio validation must still reject it.
}

func TestReconcileReviewTrimsMechanicalListOverflow(t *testing.T) {
	d := M{
		"next_focus":     stringsA("first", "second", "third"),
		"coaching_notes": stringsA("one", "two", "three", "four"),
	}
	out := reconcileReview(d, "en")
	if got := arr(out["next_focus"]); len(got) != 2 || got[0] != "first" || got[1] != "second" {
		t.Fatalf("next_focus should retain the first two items, got %#v", got)
	}
	if got := arr(out["coaching_notes"]); len(got) != 3 || got[0] != "one" || got[2] != "three" {
		t.Fatalf("coaching_notes should retain the first three items, got %#v", got)
	}
}

func TestRealMixedNameTranslation(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_MODEL_TEST") != "1" {
		t.Skip("Explicit development opt-in required")
	}
	c := newModelClient(defaultModel, 45*time.Second)
	defer c.close()
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	rows := A{M{"id": "u1", "role": "user", "text": "这个 iPad 可以放进包里吗？"}, M{"id": "a1", "role": "assistant", "text": "Yes, the backpack is big enough."}, M{"id": "u2", "role": "user", "text": "这个 backpack 怎么说？"}}
	out, _, rejected, seconds := c.translate(ctx, rows, nil, nil)
	if len(rejected) != 0 || len(out) != 3 {
		t.Fatal(out, rejected)
	}
	t.Logf("Mixed-name integration %.2fs: %v", seconds, out)
}
