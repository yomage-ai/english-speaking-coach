package main

import "testing"

func TestEnglishPracticePolicyPreservesLegacyPreferences(t *testing.T) {
	root := testRoot(t)
	for _, language := range []string{"english_first", "bilingual"} {
		for _, helpLanguage := range []string{"zh-CN", "en"} {
			profile := profileDefault()
			profile["practice_language"] = language
			profile["help_language"] = helpLanguage
			profile["correction"] = "after_scene"
			before := compact(profile)
			scene := chooseScene(root, M{"profile": profile})
			if hanRE.MatchString(str(scene["introduction"])) {
				t.Fatal("Legacy help language changed the practice introduction")
			}
			for _, phase := range []string{"scene", "review"} {
				context := speakingContext(profile, true, phase, scene)
				policy := obj(context["policy"])
				if policy["response_language"] != "english_only" || policy["non_english_input"] != "confirm_in_english_once" || policy["question_style"] != "open_without_supplied_choices" {
					t.Fatalf("Legacy preferences changed mandatory policy: %v", policy)
				}
				if policy["correction_timing"] != "after_scene" || compact(profile) != before {
					t.Fatal("Practice policy mutated saved preferences")
				}
			}
		}
	}
}

func TestEnglishTeachingHintKeepsSourceAndConfirmation(t *testing.T) {
	rows := A{M{"id": "u1", "role": "user", "text": "maybe go shop"}}
	hint := M{"kind": "help", "source_id": "u1", "quote": "maybe go shop", "english": "Maybe we could go shopping.", "chinese": "", "next_cue": "Have I understood you correctly?", "groups": stringsA("Maybe we could go shopping.")}
	validated := validateHint(hint, rows)
	if validated == nil || validated["chinese"] != "" || validated["source_text"] != "maybe go shop" || validated["next_cue"] != hint["next_cue"] {
		t.Fatal("English-only hint or its meaning check was lost")
	}
	if validateHint(hint, append(rows, M{"id": "u2", "role": "user", "text": "Yes"})) != nil {
		t.Fatal("Stale confirmation was retained after a new learner turn")
	}
}
