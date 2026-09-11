package main

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestSummaryEvidenceChecksRoleQuoteAndAssembledText(t *testing.T) {
	snapshot := M{"segments": A{M{"id": "u1", "role": "user", "text": "Could I have a discount?"}, M{"id": "a1", "role": "assistant", "text": "You can say: Could I have a discount?"}}}
	point := M{"text": "The learner asked for a discount.", "kind": "conversation_event", "evidence": A{M{"segment_id": "u1", "quote": "Could I have a discount?"}}}
	d := unpackReview(M{"summary_points": A{point}})
	checkSummaryEvidence(d, snapshot)
	if d["summary"] != point["text"] {
		t.Fatal("Summary was not assembled from observations")
	}
	for _, change := range []M{{"summary": "The learner mastered bargaining."}, {"summary_points": A{merge(point, M{"kind": "received_help"})}}, {"summary_points": A{merge(point, M{"evidence": A{M{"segment_id": "a1", "quote": "An invoice is different from a receipt."}}})}}} {
		reject(t, func() { checkSummaryEvidence(merge(d, change), snapshot) })
	}
	helped := merge(point, M{"kind": "received_help", "text": "The coach supplied a way to ask for a discount.", "evidence": A{M{"segment_id": "a1", "quote": "You can say: Could I have a discount?"}}})
	checkSummaryEvidence(unpackReview(M{"summary_points": A{helped}}), snapshot)
	checkSummaryEvidence(M{"summary": "A legacy selected summary."}, snapshot)
}

func TestRealReviewSeparatesUnexplainedDistinction(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_REVIEW_TEST") != "1" {
		t.Skip("Explicit isolated integration opt-in required")
	}
	root := testRoot(t)
	source := filepath.Join(t.TempDir(), "source.jsonl")
	atomicWrite(source, nil)
	appendLog(source, M{"type": "session_meta", "payload": M{"id": testThread}})
	appendLog(source, M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:00Z", "payload": M{"type": "realtime_session_started", "realtime_session_id": testVoice}})
	appendSegment(source, "ask", "user", "I pay for the card.")
	appendSegment(source, "paid", "assistant", "Payment received. Your order is ready.")
	appendSegment(source, "document", "user", "我想要发票，这个怎么说？")
	appendSegment(source, "substitution", "assistant", "You would like a receipt. Is that right?")
	appendSegment(source, "agree", "user", "Yes, receipt, please.")
	appendSegment(source, "end", "assistant", "Here is your receipt. Goodbye.")
	appendClose(source)
	job := enqueueReview(root, testThread, testVoice, source, false)
	ctx, cancel := context.WithTimeout(context.Background(), 180*time.Second)
	defer cancel()
	processReview(ctx, root, job)
	status := reviewStatus(root, testThread, testVoice)
	if status["status"] != "saved" {
		t.Fatal(status)
	}
	s := obj(arr(buildState(root)["sessions"])[0])
	if len(arr(s["summary_points"])) == 0 {
		t.Fatal("Saved summary lacks evidence")
	}
	checkSummaryEvidence(s, snapshotVoice(source, testThread, testVoice))
	t.Logf("SUMMARY: %s\nNOTES: %s\nNEXT: %s\nPOINTS: %s", s["summary"], compact(s["coaching_notes"]), compact(s["next_focus"]), compact(s["summary_points"]))
}

func TestRealReviewTracksPromptedReuse(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_REVIEW_TEST") != "1" {
		t.Skip("Explicit isolated integration opt-in required")
	}
	root := testRoot(t)
	source := filepath.Join(t.TempDir(), "source.jsonl")
	atomicWrite(source, nil)
	appendLog(source, M{"type": "session_meta", "payload": M{"id": testThread}})
	appendLog(source, M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:00Z", "payload": M{"type": "realtime_session_started", "realtime_session_id": testVoice}})
	appendSegment(source, "question", "user", "面包店怎么说？Is there any bread shop near here?")
	appendSegment(source, "model", "assistant", "You can ask, 'Is there a bakery near here?' Is that what you mean?")
	appendSegment(source, "reuse", "user", "Yes. Is there a bakery near here?")
	appendSegment(source, "reply", "assistant", "Yes, there is one next to the park.")
	appendSegment(source, "milk", "user", "I also want milk. How to ask if they sell milk?")
	appendSegment(source, "milkmodel", "assistant", "You can ask, 'Do they sell milk?' Is that what you mean?")
	appendSegment(source, "bareyes", "user", "Yes. Goodbye.")
	appendSegment(source, "end", "assistant", "Goodbye.")
	appendClose(source)
	job := enqueueReview(root, testThread, testVoice, source, false)
	ctx, cancel := context.WithTimeout(context.Background(), 180*time.Second)
	defer cancel()
	processReview(ctx, root, job)
	status := reviewStatus(root, testThread, testVoice)
	if status["status"] != "saved" {
		t.Fatal(status)
	}
	state := buildState(root)
	found := false
	for _, v := range arr(state["expressions"]) {
		x := obj(v)
		t.Log(compact(x))
		if has(x["source_turn_ids"], "reuse") {
			found = true
			if x["mastery"] != "source_text" || x["review_result"] != "success" || x["review_prompt"] != "source_text" {
				t.Fatal("Prompted reuse lost", x)
			}
			proof := obj(x["attempt_evidence"])
			if obj(proof["learner"])["segment_id"] != "reuse" || obj(proof["coach"])["segment_id"] != "model" {
				t.Fatal(proof)
			}
			attempts := arr(x["attempts"])
			if len(attempts) != 1 || obj(attempts[0])["original"] != obj(proof["learner"])["quote"] {
				t.Fatal("Attempt history must use actual later words", attempts)
			}
		}
		if has(x["source_turn_ids"], "milk") && x["mastery"] != "not_tested" {
			t.Fatal("Agreement is not a sentence attempt", x)
		}
	}
	if !found {
		t.Fatal("The selected useful modeled sentence was lost")
	}
}

func TestRealReviewMeaningAndConceptSupport(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_REVIEW_TEST") != "1" {
		t.Skip("Explicit isolated integration opt-in required")
	}
	root := testRoot(t)
	source := filepath.Join(t.TempDir(), "source.jsonl")
	atomicWrite(source, nil)
	appendLog(source, M{"type": "session_meta", "payload": M{"id": testThread}})
	appendLog(source, M{"type": "realtime_item", "timestamp": "2026-09-08T01:00:00Z", "payload": M{"type": "realtime_session_started", "realtime_session_id": testVoice}})
	appendSegment(source, "tea", "user", "I like black tea. 薄荷茶, is that right?")
	appendSegment(source, "wrong", "assistant", "Yes, that's right.")
	appendSegment(source, "complaint", "user", "But I said Chinese before, you didn't teach me how to say it in English.")
	appendSegment(source, "misread", "assistant", "Okay, I won't teach you when you use Chinese.")
	appendSegment(source, "lunch", "user", "How do I say 我要点午饭?")
	appendSegment(source, "model", "assistant", "You can say, 'I'm going to order lunch.' Is that right?")
	appendSegment(source, "repeat", "user", "Yes. I'm going to order lunch.")
	appendSegment(source, "end", "user", "Goodbye.")
	appendClose(source)
	job := enqueueReview(root, testThread, testVoice, source, false)
	ctx, cancel := context.WithTimeout(context.Background(), 180*time.Second)
	defer cancel()
	processReview(ctx, root, job)
	status := reviewStatus(root, testThread, testVoice)
	if status["status"] != "saved" {
		t.Fatal(status)
	}
	s := obj(arr(buildState(root)["sessions"])[0])
	for _, v := range arr(s["concept_observations"]) {
		x := obj(v)
		if has(x["source_turn_ids"], "repeat") && x["result"] == "success" && x["support"] == "none" {
			t.Fatal("Prompted concept promoted", x)
		}
	}
	t.Logf("REVIEW: %s", compact(s))
}

func TestRealTranslationMissedHelpComplaint(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_MODEL_TEST") != "1" {
		t.Skip("Explicit isolated integration opt-in required")
	}
	c := newModelClient(defaultCaptionModel, 45*time.Second)
	defer c.close()
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	rows := A{
		M{"id": "need", "role": "user", "text": "今天心情很好, how do I say?"},
		M{"id": "missed", "role": "assistant", "text": "What would you like to order?"},
		M{"id": "complaint", "role": "user", "text": "But I say Chinese, you don't teach me how to say it before."},
	}
	out, rejected, seconds := c.translate(ctx, rows, nil)
	if len(rejected) != 0 || len(out) != len(rows) {
		t.Fatal(out, rejected)
	}
	t.Logf("Missed-help translation %.2fs: %v", seconds, out)
}
