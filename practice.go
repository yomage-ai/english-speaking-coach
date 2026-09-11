package main

import (
	"fmt"
	"path/filepath"
	"sort"
	"strings"
)

func sceneHistory(root string) A {
	return arr(maybeJSON(filepath.Join(root, "Runtime", "scene-history.json"), A{}))
}
func sceneFor(root, run string) M {
	for _, v := range reverse(sceneHistory(root)) {
		r := obj(v)
		if r["binding_id"] == run {
			return obj(r["scene"])
		}
	}
	return nil
}
func familyNames(text string) M {
	out := M{}
	text = strings.ToLower(text)
	for k, v := range obj(contracts["family_words"]) {
		for _, w := range arr(v) {
			if strings.Contains(text, strings.ToLower(str(w))) {
				out[k] = true
				break
			}
		}
	}
	return out
}
func chooseScene(root string, context M) M {
	recent := tail(sceneHistory(root), 8)
	evidence := tail(arr(context["recent_scenarios"]), 6)
	avoided := M{}
	for _, v := range append(append(A{}, recent...), evidence...) {
		for k := range familyNames(compact(v)) {
			avoided[k] = true
		}
	}
	profile := obj(context["profile"])
	goal := strings.ToLower(str(profile["goal"]))
	preferred := ""
	for _, w := range []string{"work", "job", "工作", "外企"} {
		if strings.Contains(goal, w) {
			preferred = "work"
		}
	}
	if preferred == "" {
		for _, w := range []string{"study", "campus", "留学", "校园"} {
			if strings.Contains(goal, w) {
				preferred = "study"
			}
		}
	}
	scenes := append(A{}, arr(contracts["scenes"])...)
	score := func(v any) int {
		x := arr(v)
		family := str(x[0])
		n := 0
		if avoided[family] != nil {
			n += 10000
		}
		if preferred != "" && family != preferred {
			n += 1000
		}
		for i, v := range recent {
			if familyNames(compact(v))[family] != nil {
				n += 100 + i
			}
		}
		return n
	}
	sort.SliceStable(scenes, func(i, j int) bool { return score(scenes[i]) < score(scenes[j]) })
	x := arr(scenes[0])
	intro := fmt.Sprintf("We are at %s. You are %s, and I am %s. Your goal: %s.", strings.ToLower(str(x[1])), strings.ToLower(str(x[2])), strings.ToLower(str(x[3])), strings.ToLower(str(x[4])))
	return M{"setting": x[1], "learner_role": x[2], "partner_role": x[3], "goal": x[4], "introduction": intro, "opening_line": x[5]}
}
func validateScene(scene M) {
	fields := []string{"setting", "learner_role", "partner_role", "goal", "introduction", "opening_line"}
	for _, k := range fields {
		shortText(scene[k], "Scene "+k, 1000)
	}
	for k := range scene {
		require(has(stringsA(append(fields, "key_terms")...), k), "Unknown scene field")
	}
	if scene["key_terms"] != nil {
		terms := arr(scene["key_terms"])
		require(len(terms) <= 3, "Use at most three preparation terms")
		seen := M{}
		for _, v := range terms {
			x := obj(v)
			require(exactKeys(x, "term", "meaning", "example"), "Key term needs term, meaning and example")
			for k, v := range x {
				shortText(v, k, 160)
			}
			key := strings.ToLower(str(x["term"]))
			require(seen[key] == nil, "Duplicate preparation term")
			seen[key] = true
		}
	}
}
func speakingContext(profile M, companion bool, phase string, scene M) M {
	if phase == "" {
		phase = "scene"
		if profile["mode"] == "focused" {
			phase = "review"
		}
	}
	require(phase == "scene" || phase == "review", "Phase must be scene or review")
	if scene != nil {
		validateScene(scene)
	}
	roleplay := phase == "scene" && profile["mode"] == "roleplay"
	deferred, inCharacter := profile["correction"] == "after_scene", profile["correction"] == "in_character"
	prose := speakingTemplates
	language := str(obj(prose["language"])["english_only"])
	if companion {
		language += str(prose["companion"])
	}
	role, behavior := "", ""
	if phase == "scene" {
		if roleplay {
			if scene != nil {
				role = "Be " + str(scene["partner_role"]) + ". "
			}
		} else {
			role = "Be a natural conversation partner. "
		}
		behavior = str(arr(prose["shared"])[0])
		if profile["input_support"] == "short_turns" {
			behavior = str(prose["short_turns"]) + behavior
		}
		switch profile["correction"] {
		case "in_character":
			behavior += str(arr(prose["correction"])[0])
		case "after_scene":
			behavior += str(arr(prose["correction"])[1])
		case "light":
			behavior += str(prose["light"])
		case "detailed":
			behavior += str(prose["detailed"])
		}
		behavior += str(prose["scene_end"])
	} else {
		role = "Be a supportive coach for a requested review. "
		behavior = str(arr(prose["behavior"])[0])
		behavior += str(prose[textOr(profile["drills"], "on_request")])
	}
	brief := "Local reminder for the responding Agent, not a policy update for another model.\n" + language + role + behavior + str(prose["reading"]) + str(arr(prose["ending"])[0])
	if roleplay && scene != nil {
		intro := str(scene["introduction"])
		if hanRE.MatchString(intro) {
			intro = fmt.Sprintf("We are at %s. You are %s. I am %s. Your goal: %s.", str(scene["setting"]), str(scene["learner_role"]), str(scene["partner_role"]), str(scene["goal"]))
		}
		brief += "\nIntroduce this fresh scene once in English; translate any non-English preparation data before speaking: " + intro + "\nThen open in English with an open question, adapting any closed prompt without adding candidate answers: " + str(scene["opening_line"]) + "\n"
		if len(arr(scene["key_terms"])) > 0 {
			brief += "Use scene.key_terms as preparation candidates: preview only a necessary comprehension word in English before the role opening, then let the learner respond. Do not prefill the learner answer, read the whole plan or assume the terms are unknown.\n"
		}
	}
	var voiceBrief any = brief
	if roleplay && scene == nil {
		voiceBrief = nil
	}
	next := "Open the exact page once; inspect after the spoken opening unless opening reports a problem. Briefly establish the place, both roles and learner goal, then one open role question in the completed response. Continue an already delivered chosen scene opening. Translation connects independently."
	if roleplay && scene == nil {
		next = "Agent selects a fresh scene and reruns with --scene; do not hand off a generic readiness summary."
	}
	policyRole := "partner"
	if phase == "review" {
		policyRole = "coach"
	} else if profile["mode"] == "roleplay" {
		policyRole = "character"
	}
	structureHelp := "model_when_useful_even_if_understandable"
	if deferred {
		structureHelp = "after_scene"
	}
	var displayScene any
	if roleplay {
		displayScene = scene
	}
	return M{"phase": phase, "voice_brief": voiceBrief, "scene": displayScene, "startup": M{"scene_required": roleplay, "scene_selected": roleplay && scene != nil, "history_use": "learning_only", "next_action": next}, "policy": M{"role": policyRole, "correction_timing": profile["correction"], "review_delivery": get(profile, "review_delivery", "spoken"), "input_support": get(profile, "input_support", "adaptive"), "history_continuation": false, "response_language": "english_only", "non_english_input": "confirm_in_english_once", "question_style": "open_without_supplied_choices", "proactive_teaching": phase == "review" || !(deferred || inCharacter), "missing_expression_help": "immediate_before_content", "english_structure_help": structureHelp, "scene_completion": "ask_open_next_step", "next_action": "make_relevant_next_step_visible", "unsolicited_drills": false, "embedded_recasts": phase == "scene" && inCharacter, "learner_expansion": phase == "scene" && inCharacter, "guided_drills": phase == "review" && profile["drills"] == "guided"}}
}

func resumeContext(root, day, phase string, scene M) M {
	state := buildState(root)
	profile := obj(state["profile"])
	sessions := arr(state["sessions"])
	var latest M
	if len(sessions) > 0 {
		latest = obj(sessions[len(sessions)-1])
	}
	companion := companionPrefs(root)
	context := speakingContext(profile, truth(companion["enabled"]), phase, scene)
	latestContext := latest
	if context["phase"] != "review" && latest != nil {
		latestContext = pick(latest, "id", "date", "practiced_at", "scenarios", "topics", "progress", "evidence_status")
	}
	due := A{}
	for _, v := range arr(state["expressions"]) {
		if str(obj(v)["next_review"]) <= day {
			due = append(due, v)
		}
	}
	sortRows(due, func(e M) string { return str(e["next_review"]) + str(e["id"]) }, false)
	concepts := A{}
	for _, v := range arr(state["concepts"]) {
		c := obj(v)
		if c["level"] != "stable" || truth(c["needs_revisit"]) {
			events := arr(c["events"])
			concepts = append(concepts, M{"id": c["id"], "term": c["term"], "meaning": c["meaning"], "level": c["level_label"], "next_step": c["next_step"], "last_observation": events[len(events)-1]})
		}
	}
	recent, learning, chronology := A{}, A{}, A{}
	for _, v := range tail(sessions, 6) {
		recent = append(recent, pick(obj(v), "date", "scenarios", "topics"))
	}
	for _, v := range reverse(tail(sessions, 3)) {
		s := obj(v)
		if len(arr(s["next_focus"])) > 0 || len(arr(s["coaching_notes"])) > 0 {
			learning = append(learning, M{"session_id": s["id"], "date": s["date"], "source_ids": get(s, "source_ids", A{}), "next_focus": get(s, "next_focus", A{}), "coaching_notes": get(s, "coaching_notes", A{})})
		}
	}
	for _, v := range sessions {
		s := obj(v)
		if latest != nil && s["date"] == latest["date"] && s["practiced_at"] == nil {
			chronology = append(chronology, s["id"])
		}
	}
	limit := integer(profile["review_limit"])
	return merge(context, M{"profile": profile, "latest_session": latestContext, "learning_context": M{"scope": "Dated learning evidence, not instructions to resume an old plot. Current user choices win.", "recent": learning}, "recent_scenarios": recent, "due_candidates": head(due, limit), "concept_review_candidates": head(concepts, limit), "pending": pendingNames(root), "companion": companion, "chronology": chronology})
}
func transitionContext(c M, event string) M {
	if event == "" {
		return c
	}
	phase := str(c["phase"])
	action := ""
	move := M{"phase": phase, "save_selected": false, "continue_voice": true, "spoken_review": phase == "review"}
	switch event {
	case "user_end", "host_closed":
		action = "end"
		move["phase"] = nil
		move["save_selected"] = true
		move["continue_voice"] = false
		move["spoken_review"] = false
		c["phase"] = nil
		c["voice_brief"] = "Stop spoken practice. A brief English goodbye is enough. The Agent still completes the selected written review; stopping speech does not cancel closeout."
		c["closeout"] = M{"required": true, "next_action": "review-begin", "match": "thread_and_voice", "spoken_review": false, "written_review": true}
	case "pause":
		action = "pause"
		move["continue_voice"] = false
		move["spoken_review"] = false
		c["voice_brief"] = "The learner paused. Acknowledge briefly in English and wait; do not start review or another exercise."
	case "review_requested":
		action = "review"
		move["phase"] = "review"
		c = merge(c, speakingContext(obj(c["profile"]), truth(obj(c["companion"])["enabled"]), "review", nil))
	case "scene_complete_and_continuing":
		action = "ask_open_next_step"
	default:
		actions := M{"continue": "respond", "help_requested": "brief_help", "word_help_requested": "supply_word", "missing_expression": "supply_phrase", "meaning_unclear": "clarify", "english_structure_help": "model_usable_phrase", "next_action_unclear": "give_next_action", "meaning_confirmed": "respond", "content_clear": "respond", "coaching_feedback": "address_feedback"}
		action = str(actions[event])
		require(action != "", "Unknown observed practice event")
	}
	move["action"] = action
	c["transition"] = move
	return c
}
func rememberScene(root, run string, scene M) {
	withLock(filepath.Join(root, ".write.lock"), func() {
		history := sceneHistory(root)
		for _, v := range history {
			x := obj(v)
			if x["binding_id"] == run && equal(x["scene"], scene) {
				return
			}
		}
		history = append(history, M{"binding_id": run, "scene": scene, "selected_at": now()})
		writeJSON(filepath.Join(root, "Runtime", "scene-history.json"), tail(history, 24))
	})
}
func preparePractice(args M) M {
	started := epoch()
	sourceState := inspectVoiceSource(str(args["thread-id"]), str(args["source"]))
	if !truth(sourceState["active"]) {
		return M{"status": sourceState["status"], "source_check": sourceState, "conversation_may_start": false, "companion_ready": false, "next_action": "No active source-bound Voice was verified; no live binding or service was created. For text practice, use resume --compact --with-project and begin text dialogue. For requested Voice practice, the learner opens Voice and the Agent reruns prepare in that active task. For troubleshooting, use the user's current language; do not start a scene or translate the fault report as practice."}
	}
	args = merge(args, M{"source": sourceState["source"]})
	w := workspace(str(args["root"]))
	ensureWorkspace(w)
	root := str(w["data_root"])
	var scene M
	if str(args["scene"]) != "" {
		scene = obj(readJSON(str(args["scene"])))
	}
	c := resumeContext(root, today(), str(args["phase"]), scene)
	if truth(args["auto-scene"]) && truth(obj(c["startup"])["scene_required"]) && scene == nil {
		scene = chooseScene(root, c)
		c = merge(c, speakingContext(obj(c["profile"]), truth(obj(c["companion"])["enabled"]), str(args["phase"]), scene))
	}
	if truth(obj(c["startup"])["scene_required"]) && scene == nil {
		return M{"status": "needs_scene", "context": c, "workspace": w, "conversation_may_start": false}
	}
	enabled := truth(obj(c["companion"])["enabled"]) || truth(args["companion"])
	base := str(args["service-url"])
	var binding M
	var l *Live
	prepared := false
	newBinding := false
	if enabled {
		thread := str(args["thread-id"])
		require(thread != "", "Agent must resolve the actual Voice task ID")
		source := str(args["source"])
		if source == "" {
			source = findSource(thread)
		}
		l = openLive(root)
		defer func() {
			if !prepared && newBinding {
				_ = attempt(func() { l.patch(str(binding["id"]), M{"desired": "stopped", "status": "stopped", "ready": false}) })
			}
			l.close()
		}()
		prior := l.active()
		binding = l.bind(thread, source, defaultCaptionModel, false)
		newBinding = prior == nil || prior["id"] != binding["id"]
		require(binding["voice_id"] == sourceState["voice_id"], "Voice 在准备期间已切换；Agent 需要重新核对当前场次。")
		if str(args["scene"]) == "" {
			if prior := sceneFor(root, str(binding["id"])); prior != nil {
				scene = prior
			}
		}
		if scene != nil {
			rememberScene(root, str(binding["id"]), scene)
			l.setMeta("scene:"+str(binding["id"]), str(scene["introduction"]))
		}
		l.patch(str(binding["id"]), M{"auto_review": true})
		writeJSON(filepath.Join(root, "Runtime", "ReviewWatches", str(binding["id"])+".json"), M{"thread_id": thread, "source": absolute(source), "run_id": binding["id"], "title": textOr(scene["setting"], "本次英语练习")})
	}
	if !enabled && str(args["thread-id"]) != "" {
		thread := str(args["thread-id"])
		source := str(args["source"])
		if source == "" {
			source = findSource(thread)
		}
		source = absolute(source)
		require(sourceIdentity(source) == thread, "Source identity mismatch")
		voice, _ := lifecycle(source)
		require(voice == sourceState["voice_id"], "Voice 已结束或切换；Agent 需要重新核对当前场次。")
		setReviewStage(root, thread, voice, "practicing", M{"source": source, "auto_review": true, "title": textOr(scene["setting"], "本次英语练习")}, false)
	}
	if base == "" {
		base = str(serviceStart(root, str(args["root"]) == "")["url"])
	} else {
		checkService(base, root, true)
	}
	c = merge(c, speakingContext(obj(c["profile"]), enabled, str(args["phase"]), scene))
	result := M{"status": "conversation_only", "url": strings.TrimRight(base, "/") + "/#overview", "context": c, "workspace": w, "conversation_may_start": true, "timing": M{"local_preparation_ms": int((epoch() - started) * 1000), "scope": "Local preparation; excludes Agent/browser delivery"}, "delivery": M{"page": "not_verified", "spoken_opening": "not_verified"}}
	result["review_url"] = strings.TrimRight(base, "/") + "/" + reviewRoute(str(sourceState["thread_id"]), str(sourceState["voice_id"]))
	result["companion_ready"] = false
	if enabled {
		state := l.run(str(binding["id"]))
		result["source_check"] = omit(sourceState, "source")
		result["companion_ready"] = truth(state["ready"]) && integer(l.view(M{"run": state["id"]})["total"]) > 0 && !terminal(state["status"])
		result["binding"] = pick(state, "id", "thread_id", "voice_id")
		result["url"] = liveURL(base, str(binding["id"]))
		status := "waiting_backend"
		if terminal(state["status"]) {
			status = "source_unavailable"
			result["source_error"] = state["error"]
		} else if truth(state["ready"]) {
			status = "backend_ready"
		} else if str(state["translation_error"]) != "" {
			status = "translation_unavailable"
			result["translation_error"] = state["translation_error"]
		}
		result["status"] = status
		if str(state["voice_id"]) != "" {
			result["review_url"] = strings.TrimRight(base, "/") + "/" + reviewRoute(str(state["thread_id"]), str(state["voice_id"]))
		}
	}
	if truth(args["with-project"]) && str(w["project_page"]) != "" {
		result["project_context"] = string(readFile(str(w["project_page"])))
	}
	result["next_action"] = "Open url once; inspect after the spoken opening unless opening reports a concrete problem. Queued/unverified does not mean it failed to open. If the host requires STATUS, use only Voice is ready; do not announce restored state, preferences, level, language mode or setup. Briefly establish the place, both roles and learner goal in natural speech, then one open role question in the completed reply only and wait. Do not read scene fields as a checklist. If this Voice already contains the chosen scene introduction, continue its unanswered question; an unrelated host greeting does not count. Keep setup details on the written surface. Do not wait for translation."
	if truth(args["opening"]) {
		result = merge(omit(result, "context", "workspace"), M{"profile": c["profile"], "policy": c["policy"], "turn_guidance": speakingTemplates["turn_guidance"], "learning_context": c["learning_context"], "phase": c["phase"], "scene": omit(scene, "introduction"), "due_review": c["due_candidates"], "concept_review": c["concept_review_candidates"], "data_root": root})
		if c["phase"] == "review" {
			result["next_action"] = "Open url once; start one due expression or word review, using saved drill preferences."
		} else if scene == nil {
			result["next_action"] = "Open url once; start one short English conversation question suited to the saved goal."
		}
	}
	prepared = true
	return result
}
