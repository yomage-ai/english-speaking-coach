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

func TestPracticeControlsKeepTheirDistinctEffects(t *testing.T) {
	root := testRoot(t)
	for _, event := range []string{"pause", "user_end", "host_closed", "scene_complete_and_continuing"} {
		c := transitionContext(resumeContext(root, "2026-01-01", "scene", nil), event)
		move := obj(c["transition"])
		switch event {
		case "pause":
			if c["phase"] != "scene" || truth(move["save_selected"]) || truth(move["continue_voice"]) {
				t.Fatal("Pause started review or continued speech", c)
			}
		case "user_end", "host_closed":
			if c["phase"] != nil || !truth(move["save_selected"]) || truth(move["continue_voice"]) || truth(move["spoken_review"]) {
				t.Fatal("End was delayed or dropped written saving", c)
			}
		case "scene_complete_and_continuing":
			if move["action"] != "ask_open_next_step" || truth(move["save_selected"]) || !truth(move["continue_voice"]) {
				t.Fatal("Scene completion ended practice or offered a menu", c)
			}
		}
	}
}
