package main

import "testing"

func TestExpressionAttemptEvidence(t *testing.T) {
	snapshot := M{"segments": A{M{"id": "help", "role": "user", "text": "面包店?"}, M{"id": "model", "role": "assistant", "text": "Is there a bakery nearby?"}, M{"id": "try", "role": "user", "text": "Yes. Is there a bakery nearby?"}}}
	base := M{"original": "面包店?", "source_turn_ids": stringsA("help", "try"), "mastery": "not_tested", "review_result": "success", "review_prompt": "source_text", "attempt_evidence": M{"learner": M{"segment_id": "try", "quote": "Is there a bakery nearby?"}, "coach": M{"segment_id": "model", "quote": "Is there a bakery nearby?"}}}
	normalizeExpressionAttempt(base, snapshot)
	if base["mastery"] != "source_text" || base["original"] != "面包店?" {
		t.Fatal(base)
	}
	for name, change := range map[string]func(M){
		"missing proof":          func(x M) { x["attempt_evidence"] = nil },
		"wrong learner role":     func(x M) { obj(obj(x["attempt_evidence"])["learner"])["segment_id"] = "model" },
		"invented quote":         func(x M) { obj(obj(x["attempt_evidence"])["learner"])["quote"] = "I need a ticket." },
		"unlinked attempt":       func(x M) { x["source_turn_ids"] = stringsA("help") },
		"independent with model": func(x M) { x["review_prompt"] = "none" },
		"prompted transfer":      func(x M) { x["review_result"] = "transfer_success" },
	} {
		t.Run(name, func(t *testing.T) {
			x := obj(clone(base))
			change(x)
			reject(t, func() { normalizeExpressionAttempt(x, snapshot) })
		})
	}
	reversed := obj(clone(snapshot))
	reversed["segments"] = A{arr(snapshot["segments"])[2], arr(snapshot["segments"])[1]}
	reject(t, func() { normalizeExpressionAttempt(obj(clone(base)), reversed) })
	untested := M{"attempt_evidence": nil, "mastery": "independent"}
	normalizeExpressionAttempt(untested, snapshot)
	if untested["mastery"] != "not_tested" {
		t.Fatal(untested)
	}
	independent := obj(clone(base))
	independent["review_prompt"] = "none"
	obj(independent["attempt_evidence"])["coach"] = nil
	normalizeExpressionAttempt(independent, snapshot)
	if independent["mastery"] != "independent" {
		t.Fatal(independent)
	}
}
