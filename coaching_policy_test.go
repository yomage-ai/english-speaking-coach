package main

import (
	"context"
	"os"
	"testing"
	"time"
)

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

func TestBilingualTeachingHintKeepsSourceAndEnglishConfirmation(t *testing.T) {
	rows := A{M{"id": "u1", "role": "user", "text": "maybe go shop"}}
	hint := M{"kind": "help", "source_id": "u1", "quote": "maybe go shop", "english": "Maybe we could go shopping.", "chinese": "也许我们可以去购物。", "next_cue": "Have I understood you correctly?", "groups": stringsA("Maybe we could go shopping.")}
	validated := validateHint(hint, rows)
	if validated == nil || validated["chinese"] != hint["chinese"] || validated["source_text"] != "maybe go shop" || validated["next_cue"] != hint["next_cue"] {
		t.Fatal("Bilingual written hint or its English meaning check was lost")
	}
	if validateHint(hint, append(rows, M{"id": "u2", "role": "user", "text": "Yes"})) != nil {
		t.Fatal("Stale confirmation was retained after a new learner turn")
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

func TestRealMixedInputBilingualHint(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_MODEL_TEST") != "1" {
		t.Skip("Explicit development integration opt-in required")
	}
	c := newModelClient(defaultModel, 45*time.Second)
	defer c.close()
	c.instructions = str(contracts["translation_instructions"]) + str(contracts["teaching_instructions"])
	ctx, cancel := context.WithTimeout(context.Background(), 70*time.Second)
	defer cancel()
	rows := A{M{"id": "u1", "role": "user", "text": "I want some 车厘子."}}
	out, hint, seconds := c.translate(ctx, rows, M{"conversation": rows, "scene": M{"setting": "A grocery store"}, "profile": M{"practice_language": "bilingual", "correction": "in_character", "help_language": "zh-CN"}}, nil)
	if len(out) != 1 || hint == nil || hint["kind"] != "help" || !hanRE.MatchString(str(hint["chinese"])) || hanRE.MatchString(str(hint["english"])+str(hint["next_cue"])) || str(hint["next_cue"]) == "" {
		t.Fatal("Bilingual meaning or English confirmation missing", out, hint)
	}
	t.Logf("Real isolated mixed-input integration: %.2fs, translation=%v hint=%v", seconds, out, hint)
}

func TestRealUncertainObjectHint(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_MODEL_TEST") != "1" {
		t.Skip("Explicit development integration opt-in required")
	}
	c := newModelClient(defaultModel, 45*time.Second)
	defer c.close()
	c.instructions = str(contracts["translation_instructions"]) + str(contracts["teaching_instructions"])
	ctx, cancel := context.WithTimeout(context.Background(), 70*time.Second)
	defer cancel()
	rows := A{M{"id": "u1", "role": "user", "text": "I want buy two bread for breakfast."}}
	out, hint, seconds := c.translate(ctx, rows, M{"conversation": rows, "scene": M{"setting": "A bakery"}, "profile": M{"correction": "in_character", "help_language": "zh-CN"}}, nil)
	if len(out) != 1 || hint == nil || hint["kind"] != "continue" || str(hint["next_cue"]) == "" {
		t.Fatal("Uncertain item was silently chosen instead of clarified", out, hint)
	}
	t.Logf("Real isolated uncertain-object integration: %.2fs, translation=%v hint=%v", seconds, out, hint)
}
