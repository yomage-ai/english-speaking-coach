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

func TestConceptSupportFollowsTheActualSentenceAttempt(t *testing.T) {
	model := "I'm going to order lunch."
	snapshot := M{"segments": A{
		M{"id": "need", "role": "user", "text": "How do I say 点午餐?"},
		M{"id": "coach", "role": "assistant", "text": model},
		M{"id": "try", "role": "user", "text": model + " My train leaves soon."},
		M{"id": "later", "role": "user", "text": "I can order dinner myself."},
	}}
	expression := M{"source_turn_ids": stringsA("need", "try"), "review_prompt": "source_text", "review_result": "success", "attempt_evidence": M{"learner": M{"segment_id": "try", "quote": model}, "coach": M{"segment_id": "coach", "quote": model}}}
	observation := M{"source_turn_ids": stringsA("need", "try"), "term": "order", "quote": model, "dimension": "use", "result": "success", "support": "none", "expression_indices": A{0}}
	draft := M{"expressions": A{expression}, "concept_observations": A{observation}}
	got := completeReviewBookkeeping(obj(clone(draft)), snapshot, "zh-CN")
	o := obj(arr(got["concept_observations"])[0])
	if o["result"] != "supported" || o["support"] != "model" || o["quote"] != model || !equal(o["source_turn_ids"], observation["source_turn_ids"]) {
		t.Fatal("Sentence and concept disagree about the same prompted attempt", o)
	}
	first := compact(got)
	if compact(completeReviewBookkeeping(got, snapshot, "zh-CN")) != first {
		t.Fatal("Repeated bookkeeping changed evidence")
	}
	for name, change := range map[string]M{
		"unprompted clause in same turn": {"quote": "My train leaves soon.", "term": "train"},
		"separate use":                   {"quote": "order", "source_turn_ids": stringsA("try", "later")},
		"other dimension":                {"dimension": "reading"},
		"unsuccessful attempt":           {"result": "needs_help"},
	} {
		t.Run(name, func(t *testing.T) {
			x := merge(obj(clone(observation)), change)
			before := compact(x)
			normalizeExpressionAttempt(expression, snapshot)
			reconcileConceptAttempt(x, A{expression}, snapshot, "en")
			if compact(x) != before {
				t.Fatal("Unrelated evidence was reclassified", x)
			}
		})
	}
	// A supplied keyword cannot make every other word in the sentence prompted.
	keywords := obj(clone(expression))
	keywords["review_prompt"] = "keywords"
	obj(obj(keywords["attempt_evidence"])["coach"])["quote"] = "order"
	normalizeExpressionAttempt(keywords, snapshot)
	for quote, want := range map[string]string{"order": "supported", "lunch": "success"} {
		x := merge(obj(clone(observation)), M{"quote": quote})
		reconcileConceptAttempt(x, A{keywords}, snapshot, "en")
		if x["result"] != want {
			t.Fatal(quote, x)
		}
	}
}
