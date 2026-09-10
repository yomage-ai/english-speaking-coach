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
