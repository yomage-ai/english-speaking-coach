package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

var activeReviews = stringsA("queued", "reading", "generating", "checking", "saving")

func reviewFile(root, thread, voice string) string {
	sources := voiceSources(thread, voice)
	return filepath.Join(root, "Runtime", "Reviews", hash([]byte(str(sources[0]) + "\n" + str(sources[1])))[:24]+".json")
}
func setReviewStage(root, thread, voice, status string, fields M, locked bool) M {
	require(has(stringsA("practicing", "queued", "reading", "generating", "checking", "preparing", "saving", "saved", "error"), status), "Unknown review stage")
	var result M
	save := func() {
		path := reviewFile(root, thread, voice)
		old := obj(maybeJSON(path, M{}))
		if status == "practicing" && len(old) > 0 {
			result = old
			return
		}
		result = merge(old, M{"status": status, "thread_id": thread, "voice_id": voice, "created_epoch": get(old, "created_epoch", epoch())}, fields)
		if status != "practicing" && result["started_epoch"] == nil {
			result["started_epoch"] = epoch()
		}
		if old["status"] != status {
			result["stage_epoch"] = epoch()
		}
		if status != "error" {
			delete(result, "error")
		}
		writeJSON(path, result)
	}
	if locked {
		save()
	} else {
		withLock(filepath.Join(root, ".write.lock"), save)
	}
	return result
}
func recentReviews(root string) A {
	out := A{}
	for _, p := range glob(filepath.Join(root, "Runtime", "Reviews", "*.json")) {
		var row M
		if err := attempt(func() { row = obj(readJSON(p)) }); err == nil {
			out = append(out, row)
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return num(obj(out[i])["created_epoch"]) > num(obj(out[j])["created_epoch"]) })
	return out
}
func reviewStatus(root, thread, voice string) M {
	p := reviewFile(root, thread, voice)
	if !exists(p) {
		return M{"status": "waiting", "elapsed_seconds": 0}
	}
	d := obj(readJSON(p))
	elapsed := max(0, int(epoch()-num(get(d, "started_epoch", epoch()))))
	stage := textOr(d["status"], "preparing")
	status := stage
	if has(append(activeReviews, "preparing"), stage) && elapsed >= 180 {
		status = "needs_attention"
	}
	return merge(d, M{"stage": stage, "status": status, "elapsed_seconds": elapsed})
}
func matchingRecords(state M, thread, voice string) A {
	ids := voiceSources(thread, voice)
	out := A{}
	for _, v := range arr(state["sessions"]) {
		s := obj(v)
		if has(s["source_ids"], ids[0]) && has(s["source_ids"], ids[1]) {
			out = append(out, s)
		}
	}
	require(len(out) <= 1, "同一场 Voice 有多份复盘，需核对来源。")
	return out
}
func enqueueReview(root, thread, voice, source string, retry bool) M {
	if source == "" {
		source = findSource(thread)
	}
	source = absolute(source)
	snapshotVoice(source, thread, voice)
	s := buildState(root)
	matches := matchingRecords(s, thread, voice)
	if len(matches) > 0 {
		return M{"status": "saved", "session_id": obj(matches[0])["id"], "archive_route": reviewRoute(thread, voice)}
	}
	var result M
	withLock(filepath.Join(root, ".write.lock"), func() {
		old := obj(maybeJSON(reviewFile(root, thread, voice), M{}))
		if has(activeReviews, old["status"]) || old["status"] == "error" && !retry {
			result = old
			return
		}
		result = setReviewStage(root, thread, voice, "queued", M{"source": source, "auto_review": true, "attempt": get(old, "attempt", 0), "retry_requested": retry, "started_epoch": epoch()}, true)
	})
	return merge(result, M{"archive_route": reviewRoute(thread, voice), "next_action": "Open the exact review page. The local worker generates and saves; do not draft a competing review."})
}
func canonicalKey(en, zh string) string {
	return strings.Join(strings.Fields(strings.ToLower(en)), " ") + "\n" + strings.Join(strings.Fields(zh), " ")
}
func mapTurnIDs(value any, mapping map[string]string, field string) any {
	switch v := value.(type) {
	case map[string]any:
		r := M{}
		for k, x := range v {
			key := k
			if field == "omitted_turns" && mapping[k] != "" {
				key = mapping[k]
			}
			r[key] = mapTurnIDs(x, mapping, k)
		}
		return r
	case []any:
		r := A{}
		for _, x := range v {
			r = append(r, mapTurnIDs(x, mapping, field))
		}
		return r
	case string:
		if has(stringsA("id", "segment_id", "source_turn_ids"), field) && mapping[v] != "" {
			return mapping[v]
		}
	}
	return value
}
func unpackReview(d M) M {
	d = copyM(d)
	if d["summary_points"] != nil {
		parts := []string{}
		for _, v := range arr(d["summary_points"]) {
			parts = append(parts, str(obj(v)["text"]))
		}
		d["summary"] = strings.Join(parts, " ")
	}
	if a, ok := d["omitted_turns"].([]any); ok {
		out := M{}
		for _, v := range a {
			x := obj(v)
			id := str(x["segment_id"])
			require(out[id] == nil, "Duplicate omitted turn ID")
			out[id] = x["reason"]
		}
		d["omitted_turns"] = out
	}
	if a, ok := d["reading_omissions"].([]any); ok {
		out := M{}
		for _, v := range a {
			x := obj(v)
			out[strconv.Itoa(integer(x["expression_index"]))] = x["reason"]
		}
		d["reading_omissions"] = out
	}
	for _, v := range append(arr(d["expressions"]), arr(d["concept_observations"])...) {
		x := obj(v)
		for k, v := range x {
			if v == nil {
				delete(x, k)
			}
		}
	}
	return d
}
func coalesceExpressions(d M) M {
	d = copyM(d)
	out := A{}
	byKey := map[string]int{}
	remap := map[int]int{}
	for i, v := range arr(d["expressions"]) {
		raw := obj(v)
		key := canonicalKey(str(raw["english"]), str(raw["chinese"]))
		if ref := str(raw["expression_ref"]); ref != "" {
			key = "ref:" + ref
		}
		target, found := byKey[key]
		if !found {
			byKey[key] = len(out)
			remap[i] = len(out)
			out = append(out, raw)
			continue
		}
		remap[i] = target
		old := obj(out[target])
		chosen := old
		if raw["review_result"] != nil && old["review_result"] == nil {
			chosen = copyM(raw)
		}
		quotes := A{}
		for _, item := range []M{old, raw} {
			if a := arr(item["source_quotes"]); len(a) > 0 {
				quotes = append(quotes, a...)
			} else {
				quotes = append(quotes, M{"quote": item["original"], "source_turn_ids": item["source_turn_ids"]})
			}
		}
		chosen["source_turn_ids"] = unique(append(arr(old["source_turn_ids"]), arr(raw["source_turn_ids"])...))
		chosen["source_quotes"] = unique(quotes)
		if chosen["reading_guide"] == nil {
			chosen["reading_guide"] = get(old, "reading_guide", raw["reading_guide"])
			if chosen["reading_guide"] == nil {
				delete(chosen, "reading_guide")
			}
		}
		out[target] = chosen
	}
	d["expressions"] = out
	for _, k := range []string{"priority_indices"} {
		if d[k] != nil {
			a := A{}
			for _, v := range arr(d[k]) {
				i := integer(v)
				if mapped, ok := remap[i]; ok {
					i = mapped
				}
				a = append(a, i)
			}
			d[k] = unique(a)
		}
	}
	omissions := M{}
	for k, v := range obj(d["reading_omissions"]) {
		i, e := strconv.Atoi(k)
		must(e)
		if mapped, ok := remap[i]; ok {
			i = mapped
		}
		omissions[strconv.Itoa(i)] = v
	}
	d["reading_omissions"] = omissions
	for _, v := range arr(d["concept_observations"]) {
		x := obj(v)
		if x["expression_indices"] == nil {
			continue
		}
		a := A{}
		for _, v := range arr(x["expression_indices"]) {
			i := integer(v)
			if mapped, ok := remap[i]; ok {
				i = mapped
			}
			a = append(a, i)
		}
		x["expression_indices"] = unique(a)
	}
	return d
}
func reconcileReview(d M, language string) M {
	d = coalesceExpressions(d)
	// The prompt asks for the strongest items first. A model occasionally
	// returns one extra focus or coaching note; that is a mechanical size
	// violation, not a reason to spend another full model call repairing an
	// otherwise valid review.
	d["next_focus"] = head(arr(d["next_focus"]), 2)
	d["coaching_notes"] = head(arr(d["coaching_notes"]), 3)
	for _, v := range arr(d["concept_observations"]) {
		o := obj(v)
		// A supplied wording model can support completion, never independent
		// mastery. Downgrade this contradiction without changing its source,
		// quote or support. Other invalid evidence still fails normal checks.
		if o["result"] == "success" && has(stringsA("meaning", "use"), o["dimension"]) && has(stringsA("model", "keywords"), o["support"]) {
			o["result"] = "supported"
			note := "Supplied wording is recorded as supported completion, not independent mastery."
			if language == "zh-CN" {
				note = "当时有语言提示，记为有提示完成，不代表独立掌握。"
			}
			o["note"] = strings.TrimSpace(str(o["note"]) + " " + note)
		}
	}
	selected := M{}
	for _, v := range append(arr(d["expressions"]), arr(d["concept_observations"])...) {
		for _, id := range arr(obj(v)["source_turn_ids"]) {
			selected[str(id)] = true
		}
	}
	for id := range obj(d["omitted_turns"]) {
		if selected[id] != nil {
			delete(obj(d["omitted_turns"]), id)
		}
	}
	for i, v := range arr(d["expressions"]) {
		x := obj(v)
		g := obj(x["reading_guide"])
		if len(g) == 0 {
			continue
		}
		en := strings.TrimSpace(str(x["english"]))
		tokens := words(en)
		if len(tokens) >= 2 && len(tokens) <= 9 && strings.HasSuffix(en, "?") && !strings.ContainsAny(en, ",;:—") && !has(tokens, "but") && !has(tokens, "because") && !has(tokens, "although") && !has(tokens, "while") && has(stringsA("how", "what", "where", "when", "why", "which", "who", "do", "does", "can", "could", "would", "is", "are", "may", "will"), tokens[0]) {
			stress := A{}
			for _, v := range arr(g["groups"]) {
				stress = append(stress, arr(obj(v)["stress"])...)
			}
			g["groups"] = A{M{"text": en, "stress": head(unique(stress), 3)}}
			if len(tokens) > 0 && !has(tokens, "or") && has(stringsA("how", "what", "where", "when", "why", "which", "who"), tokens[0]) && len(arr(g["groups"])) == 1 {
				g["tone"] = "fall"
				g["tone_note"] = "For a neutral information question, a fall is a useful option; checking or surprise can change the tune."
				if language == "zh-CN" {
					g["tone_note"] = "中性地询问信息时，句末可自然下降；确认或惊讶时可以换语调。"
				}
			}
		}
		if err := attempt(func() { validateGuide(g, en) }); err != nil {
			delete(x, "reading_guide")
			note := "Reading annotations did not pass validation and are withheld; the English expression is retained."
			if language == "zh-CN" {
				note = "读法标注未通过校验，暂不展示；英文表达已保留。"
			}
			obj(d["reading_omissions"])[strconv.Itoa(i)] = note
			x["note"] = strings.TrimSpace(str(x["note"]) + " " + note)
		}
	}
	return d
}
func learnerTurns(snapshot M) M {
	out := M{}
	for _, v := range arr(snapshot["segments"]) {
		s := obj(v)
		if s["role"] == "user" {
			out[str(s["id"])] = s
		}
	}
	return out
}

// completeReviewBookkeeping derives exhaustive per-turn accounting from the
// model's selected evidence. These fields are mechanical validation metadata,
// so asking the model to repeat one object for every learner turn only makes a
// review slower and more likely to time out without adding judgment quality.
func completeReviewBookkeeping(d, snapshot M, language string) M {
	d = copyM(d)
	turns := learnerTurns(snapshot)
	learnerIDs := func(value any) A {
		out := A{}
		for _, rawID := range arr(value) {
			if turns[str(rawID)] != nil {
				out = append(out, rawID)
			}
		}
		return unique(out)
	}
	selected := M{}
	conceptsByTurn := map[string]A{}
	needsHelp := M{}
	for _, v := range arr(d["expressions"]) {
		x := obj(v)
		x["source_turn_ids"] = learnerIDs(x["source_turn_ids"])
		for _, rawQuote := range arr(x["source_quotes"]) {
			quote := obj(rawQuote)
			quote["source_turn_ids"] = learnerIDs(quote["source_turn_ids"])
		}
		result, prompt := str(x["review_result"]), str(x["review_prompt"])
		validAttempt := has(stringsA("failed", "partial", "success", "transfer_success"), result) && has(stringsA("source_text", "keywords", "none", "changed_context"), prompt)
		if !validAttempt {
			x["mastery"] = "not_tested"
			delete(x, "review_result")
			delete(x, "review_prompt")
		}
		for _, id := range arr(x["source_turn_ids"]) {
			if turns[str(id)] != nil {
				selected[str(id)] = true
			}
		}
	}
	for index, v := range arr(d["concept_observations"]) {
		x := obj(v)
		x["source_turn_ids"] = learnerIDs(x["source_turn_ids"])
		for _, rawID := range arr(x["source_turn_ids"]) {
			id := str(rawID)
			if turns[id] == nil {
				continue
			}
			selected[id] = true
			conceptsByTurn[id] = append(conceptsByTurn[id], index)
			if x["result"] != "success" || x["support"] != "none" {
				needsHelp[id] = true
			}
		}
	}
	omissions := M{}
	checks := A{}
	for _, v := range arr(snapshot["segments"]) {
		s := obj(v)
		if s["role"] != "user" {
			continue
		}
		id := str(s["id"])
		reason := "No distinct word help selected."
		omission := "No distinct review item selected after full-turn assessment."
		if language == "zh-CN" {
			reason = "本回合没有单独的词义求助。"
			omission = "逐项检查后，本回合没有需要单独保留的复习点。"
		}
		if truth(needsHelp[id]) {
			reason = "Selected word help is linked."
			if language == "zh-CN" {
				reason = "已关联本回合的词义求助。"
			}
		}
		indices := conceptsByTurn[id]
		if indices == nil {
			indices = A{}
		}
		checks = append(checks, M{"segment_id": id, "needs_word_help": truth(needsHelp[id]), "reason": reason, "concept_indices": indices})
		if selected[id] == nil {
			omissions[id] = omission
		}
	}
	d["word_checks"] = checks
	d["omitted_turns"] = omissions
	return d
}

func qualityCheck(d, snapshot M) {
	checkSummaryEvidence(d, snapshot)
	turns := learnerTurns(snapshot)
	checks := arr(d["word_checks"])
	require(len(checks) == len(turns), "word_checks must assess every learner turn exactly once")
	seen := M{}
	concepts := arr(d["concept_observations"])
	for _, v := range checks {
		x := obj(v)
		id := str(x["segment_id"])
		require(turns[id] != nil && seen[id] == nil, "Invalid/duplicate word check ID")
		seen[id] = true
		_, ok := x["needs_word_help"].(bool)
		require(ok && strings.TrimSpace(str(x["reason"])) != "", "Word check needs a boolean and concrete reason")
		ids := arr(x["concept_indices"])
		if truth(x["needs_word_help"]) {
			require(len(ids) > 0, "Explicit word help must have a concept observation")
		}
		for _, v := range ids {
			i := integer(v)
			require(num(v) == float64(i) && i >= 0 && i < len(concepts), "Invalid word check concept index")
			require(has(obj(concepts[i])["source_turn_ids"], id), "Word assessment refers to unrelated evidence")
		}
	}
	expressions := arr(d["expressions"])
	for _, v := range arr(d["priority_indices"]) {
		i := integer(v)
		require(num(v) == float64(i) && i >= 0 && i < len(expressions), "Invalid priority index")
		require(obj(expressions[i])["reading_guide"] != nil || str(obj(d["reading_omissions"])[strconv.Itoa(i)]) != "", "Each priority needs reading guidance or an omission reason")
	}
}

// Quote/role checks establish provenance, not semantic truth. Model evaluation
// still assesses whether the actual words support each summary observation.
func checkSummaryEvidence(d, snapshot M) {
	if d["summary_points"] == nil {
		return // Legacy/manual drafts remain readable and recoverable.
	}
	points := arr(d["summary_points"])
	require(len(points) > 0 && len(points) <= 3, "Summary needs one to three source-linked observations")
	segments := M{}
	for _, v := range arr(snapshot["segments"]) {
		segments[str(obj(v)["id"])] = v
	}
	parts := []string{}
	for _, v := range points {
		p := obj(v)
		shortText(p["text"], "Summary observation", 600)
		require(has(stringsA("conversation_event", "received_help", "demonstrated_use"), p["kind"]), "Unknown summary observation kind")
		refs := arr(p["evidence"])
		require(len(refs) > 0, "Summary observation needs transcript evidence")
		roles := M{}
		for _, ref := range refs {
			e := obj(ref)
			s := obj(segments[str(e["segment_id"])])
			quote := str(e["quote"])
			require(s != nil && strings.TrimSpace(quote) != "" && strings.Contains(str(s["text"]), quote), "Summary evidence must quote an exact available transcript segment")
			roles[str(s["role"])] = true
		}
		if p["kind"] == "received_help" {
			require(truth(roles["assistant"]), "Received teaching needs the coach's actual words, not a review suggestion")
		} else {
			require(truth(roles["user"]), "Conversation or demonstrated use needs learner evidence")
		}
		parts = append(parts, str(p["text"]))
	}
	require(str(d["summary"]) == strings.Join(parts, " "), "Summary contains text outside its source-linked observations")
}
func normalizeReview(root string, d M, thread, voice string, snapshot, state M) M {
	checkSummaryEvidence(d, snapshot)
	require(snapshot["thread_id"] == thread && snapshot["voice_id"] == voice, "Review snapshot belongs to another Voice")
	for _, k := range []string{"title", "summary", "expressions", "omitted_turns"} {
		_, ok := d[k]
		require(ok, "Review draft missing "+k)
	}
	dateTime := stamp(str(snapshot["voice_started_at"])).Local()
	day := dateTime.Format("2006-01-02")
	used := M{}
	for _, pattern := range []string{"Sessions/*.md", "Pending/*.json"} {
		for _, p := range glob(filepath.Join(root, pattern)) {
			used[strings.TrimSuffix(filepath.Base(p), filepath.Ext(p))] = true
		}
	}
	sid := nextID("SES-"+strings.ReplaceAll(day, "-", "")+"-", used)
	r := merge(pick(d, "title", "summary", "summary_points", "topics", "scenarios", "progress", "next_focus", "coaching_notes", "unfinished"), M{"id": sid, "date": day, "practiced_at": dateTime.Format(time.RFC3339Nano), "source_ids": voiceSources(thread, voice), "end_status": "ended", "evidence_status": "selected", "evidence_note": "核对本场可用的去重转写后精选；转写不是发音证据。课后新增说法不代表会中已教学或已掌握。", "expressions": A{}, "concept_observations": A{}})
	turns := learnerTurns(snapshot)
	covered := M{}
	sourceTurns := func(x M, quote string) {
		ids, ok := x["source_turn_ids"].([]any)
		require(ok && len(ids) > 0, "Selected item needs actual learner source_turn_ids")
		validQuote := false
		for _, v := range ids {
			id := str(v)
			require(turns[id] != nil, "Unknown learner source_turn_id: "+id)
			if strings.Contains(str(obj(turns[id])["text"]), quote) {
				validQuote = true
			}
			covered[id] = true
		}
		require(strings.TrimSpace(quote) != "" && validQuote, "Selected quote must be an exact excerpt of a linked learner turn")
	}
	expressions, byText, used := M{}, M{}, M{}
	for _, v := range arr(state["expressions"]) {
		e := obj(v)
		expressions[str(e["id"])] = e
		used[str(e["id"])] = true
		byText[canonicalKey(str(e["english"]), str(e["chinese"]))] = e
	}
	for _, p := range glob(filepath.Join(root, "Pending", "*.json")) {
		for _, v := range arr(obj(readJSON(p))["expressions"]) {
			used[str(obj(v)["id"])] = true
		}
	}
	for _, v := range arr(d["expressions"]) {
		x := copyM(v)
		sourceTurns(x, str(x["original"]))
		for _, v := range arr(x["source_quotes"]) {
			sourceTurns(obj(v), str(obj(v)["quote"]))
		}
		ref := str(x["expression_ref"])
		delete(x, "expression_ref")
		if ref != "" {
			require(expressions[ref] != nil, "Unknown expression_ref")
			for _, k := range []string{"english", "chinese"} {
				require(x[k] == nil || x[k] == obj(expressions[ref])[k], "Conflicting expression_ref text")
				x[k] = obj(expressions[ref])[k]
			}
		} else {
			for _, k := range []string{"english", "chinese"} {
				require(strings.TrimSpace(str(x[k])) != "", "New expression needs "+k)
			}
			require(validExpressionLanguages(x), "表达需要英文原句与中文句意；未把错位语言保存为学习资料。")
			ref = str(obj(byText[canonicalKey(str(x["english"]), str(x["chinese"]))])["id"])
		}
		if ref == "" {
			ref = nextID("EXP-"+strings.ReplaceAll(day, "-", "")+"-", used)
		}
		x["id"] = ref
		x["mastery"] = get(x, "mastery", "not_tested")
		x["next_review"] = get(x, "next_review", addDays(day, 1))
		r["expressions"] = append(arr(r["expressions"]), x)
		byText[canonicalKey(str(x["english"]), str(x["chinese"]))] = x
	}
	concepts := M{}
	for _, v := range arr(state["concepts"]) {
		concepts[str(obj(v)["id"])] = v
	}
	for index, v := range arr(d["concept_observations"]) {
		x := copyM(v)
		sourceTurns(x, str(x["quote"]))
		cid := str(x["concept_id"])
		if cid != "" {
			require(concepts[cid] != nil, "Unknown concept_id; new senses need term and meaning")
			for _, k := range []string{"term", "meaning"} {
				require(x[k] == nil || x[k] == obj(concepts[cid])[k], "Conflicting canonical concept text")
				x[k] = obj(concepts[cid])[k]
			}
		} else {
			for _, k := range []string{"term", "meaning"} {
				require(strings.TrimSpace(str(x[k])) != "", "New concept needs "+k)
			}
			for id, v := range concepts {
				c := obj(v)
				if canonicalKey(str(c["term"]), str(c["meaning"])) == canonicalKey(str(x["term"]), str(x["meaning"])) {
					cid = id
					x["term"], x["meaning"] = c["term"], c["meaning"]
					break
				}
			}
			if cid == "" {
				cid = "CON-" + hash([]byte(strings.ToLower(strings.TrimSpace(str(x["term"]))) + "\n" + strings.TrimSpace(str(x["meaning"]))))[:16]
			}
		}
		x["concept_id"] = cid
		x["id"] = fmt.Sprintf("OBS-%s-%d", sid[4:], index+1)
		require(get(x, "modality", "transcript") == "transcript" && get(x, "quote_kind", "utterance") == "utterance", "finish-review only uses transcript utterances")
		x["modality"], x["quote_kind"] = "transcript", "utterance"
		x["context"] = get(x, "context", r["title"])
		ids := A{}
		for _, v := range arr(x["expression_indices"]) {
			i := integer(v)
			require(num(v) == float64(i) && i >= 0 && i < len(arr(r["expressions"])), "Invalid expression index")
			ids = append(ids, obj(arr(r["expressions"])[i])["id"])
		}
		delete(x, "expression_indices")
		x["expression_ids"] = ids
		r["concept_observations"] = append(arr(r["concept_observations"]), x)
	}
	omitted, ok := d["omitted_turns"].(map[string]any)
	require(ok, "omitted_turns must map learner IDs to reasons")
	for id, v := range omitted {
		require(turns[id] != nil && strings.TrimSpace(str(v)) != "", "Invalid omission")
		require(covered[id] == nil, "A selected turn must not also be omitted")
	}
	for id := range turns {
		require(covered[id] != nil || omitted[id] != nil, "Review has not accounted for learner turn: "+id)
	}
	priorities := get(d, "priority_indices", A{})
	if d["priority_indices"] == nil {
		a := A{}
		for i := 0; i < min(3, len(arr(r["expressions"]))); i++ {
			a = append(a, i)
		}
		priorities = a
	}
	require(len(arr(priorities)) <= 3 && len(unique(arr(priorities))) == len(arr(priorities)), "Invalid priority indices")
	ids := A{}
	for _, v := range arr(priorities) {
		i := integer(v)
		require(num(v) == float64(i) && i >= 0 && i < len(arr(r["expressions"])), "Invalid priority index")
		ids = append(ids, obj(arr(r["expressions"])[i])["id"])
	}
	r["review_priority_ids"] = ids
	r["review_coverage"] = M{"available_learner_turns": len(turns), "selected_learner_turns": len(covered), "omitted_turns": omitted, "scope": "available_unique_segments", "judgment": "Agent selection; coverage does not prove teaching quality"}
	if d["word_checks"] != nil {
		c := obj(r["review_coverage"])
		c["word_assessed_turns"] = len(arr(d["word_checks"]))
		n := 0
		for _, v := range arr(d["word_checks"]) {
			if truth(obj(v)["needs_word_help"]) {
				n++
			}
		}
		c["word_help_turns"] = n
		c["concept_observations"] = len(arr(r["concept_observations"]))
		n = 0
		for _, v := range arr(r["expressions"]) {
			if obj(v)["reading_guide"] != nil {
				n++
			}
		}
		c["reading_guided_expressions"] = n
	}
	validatePayload(r, false)
	return r
}
func finishReview(root string, d M, thread, voice, source string) M {
	state := buildState(root)
	matches := matchingRecords(state, thread, voice)
	if len(matches) > 0 {
		return M{"status": "already_saved", "session": obj(matches[0])["id"], "validation": validateArchive(root)}
	}
	if source == "" {
		source = findSource(thread)
	}
	snapshot := snapshotVoice(source, thread, voice)
	var pending M
	for _, p := range glob(filepath.Join(root, "Pending", "*.json")) {
		x := obj(readJSON(p))
		ids := voiceSources(thread, voice)
		if has(x["source_ids"], ids[0]) && has(x["source_ids"], ids[1]) {
			require(pending == nil, "Multiple checkpoints for the same Voice")
			pending = x
		}
	}
	setReviewStage(root, thread, voice, "saving", M{}, true)
	var result M
	if pending != nil {
		require(textOr(pending["end_status"], "ended") == "ended", "In-progress checkpoint needs explicit reconciliation")
		result = commitRecord(root, pending)
	} else {
		result = commitRecord(root, normalizeReview(root, d, thread, voice, snapshot, state))
	}
	result["validation"] = validateArchive(root)
	require(truth(obj(result["validation"])["ok"]), "Saved record needs derived-state recovery")
	setReviewStage(root, thread, voice, "saved", M{"session_id": result["session"]}, true)
	return result
}
func compactReviewInput(state, snapshot M) M {
	text := ""
	transcript := A{}
	for _, v := range arr(snapshot["segments"]) {
		s := obj(v)
		text += strings.ToLower(str(s["text"])) + " "
		transcript = append(transcript, pick(s, "id", "role", "text"))
	}
	catalog, concepts := A{}, A{}
	for _, v := range reverse(arr(state["expressions"])) {
		e := obj(v)
		for _, w := range strings.Fields(str(e["english"])) {
			if len(w) > 3 && strings.Contains(text, strings.ToLower(w)) {
				catalog = append(catalog, pick(e, "id", "english", "chinese"))
				break
			}
		}
	}
	for _, v := range arr(state["concepts"]) {
		c := obj(v)
		if strings.Contains(text, strings.ToLower(str(c["term"]))) || strings.Contains(text, str(c["meaning"])) {
			concepts = append(concepts, pick(c, "id", "term", "meaning"))
		}
	}
	return M{"profile": pick(obj(state["profile"]), "help_language", "input_support"), "transcript": transcript, "expression_catalog": head(catalog, 16), "concept_catalog": head(concepts, 24)}
}
func checkedPreview(expressions A, snapshot M) A {
	turns := learnerTurns(snapshot)
	out := A{}
	for _, v := range head(expressions, 3) {
		x := obj(v)
		good := true
		for _, k := range []string{"original", "english", "chinese"} {
			if strings.TrimSpace(str(x[k])) == "" || len([]rune(str(x[k]))) > 1500 {
				good = false
			}
		}
		quote := str(x["original"])
		linked := false
		for _, id := range arr(x["source_turn_ids"]) {
			if turns[str(id)] == nil {
				good = false
			} else if strings.Contains(str(obj(turns[str(id)])["text"]), quote) {
				linked = true
			}
		}
		if good && linked && validExpressionLanguages(x) {
			out = append(out, pick(x, "original", "english", "chinese", "note", "source_turn_ids"))
		}
	}
	return out
}
func processReview(ctx context.Context, root string, job M) {
	thread, voice := str(job["thread_id"]), str(job["voice_id"])
	draftFile := strings.TrimSuffix(reviewFile(root, thread, voice), ".json") + ".draft"
	var client *ModelClient
	started := time.Now()
	timings := M{}
	err := attempt(func() {
		setReviewStage(root, thread, voice, "reading", M{"worker_pid": os.Getpid()}, false)
		state := buildState(root)
		if matches := matchingRecords(state, thread, voice); len(matches) > 0 {
			setReviewStage(root, thread, voice, "saved", M{"session_id": obj(matches[0])["id"]}, false)
			_ = os.Remove(draftFile)
			return
		}
		snapshot := snapshotVoice(str(job["source"]), thread, voice)
		payload := compactReviewInput(state, snapshot)
		language := str(obj(state["profile"])["help_language"])
		aliases, originals := map[string]string{}, map[string]string{}
		setAliases := func() {
			for i, v := range arr(snapshot["segments"]) {
				id := str(obj(v)["id"])
				alias := fmt.Sprintf("t%d", i+1)
				aliases[id] = alias
				originals[alias] = id
			}
		}
		setAliases()
		preview := func(raw string) {
			part := suggestionPrefix(raw)
			checked := checkedPreview(arr(mapTurnIDs(part, originals, "")), snapshot)
			if len(checked) > 0 && ctx.Err() == nil {
				if timings["first_preview_seconds"] == nil {
					timings["first_preview_seconds"] = time.Since(started).Seconds()
				}
				setReviewStage(root, thread, voice, "generating", M{"preview": checked, "first_preview_seconds": timings["first_preview_seconds"]}, false)
			}
		}
		generate := func(input M) M {
			if client == nil {
				client = newModelClient(defaultReviewModel, 120*time.Second)
				client.instructions = str(contracts["review_instructions"])
			}
			t := time.Now()
			answer := client.generate(ctx, obj(mapTurnIDs(input, aliases, "")), rawContracts["review_schema"], preview)
			timings["generation_seconds"] = time.Since(t).Seconds()
			return reconcileReview(obj(mapTurnIDs(unpackReview(answer), originals, "")), language)
		}
		var draft M
		if exists(draftFile) {
			draft = reconcileReview(obj(readJSON(draftFile)), language)
		} else {
			setReviewStage(root, thread, voice, "generating", M{"attempt": integer(job["attempt"]) + 1, "model": defaultReviewModel, "effort": "low", "input_chars": len([]rune(compact(payload)))}, false)
			draft = generate(payload)
			writeJSON(draftFile, draft)
		}
		draft = completeReviewBookkeeping(draft, snapshot, language)
		for trial := 0; trial < 2; trial++ {
			var result M
			failure := attempt(func() {
				setReviewStage(root, thread, voice, "checking", M{}, false)
				latest := snapshotVoice(str(job["source"]), thread, voice)
				if !equal(latest["segments"], snapshot["segments"]) {
					snapshot = latest
					payload = compactReviewInput(state, snapshot)
					setAliases()
					panic(fmt.Errorf("Final transcript changed; reconcile the latest full transcript"))
				}
				qualityCheck(draft, snapshot)
				withLock(filepath.Join(root, ".write.lock"), func() {
					normalizeReview(root, draft, thread, voice, snapshot, buildState(root))
					result = finishReview(root, draft, thread, voice, str(job["source"]))
				})
			})
			if failure == nil {
				backup := recoveryBackup(root)
				timings["worker_seconds"] = time.Since(started).Seconds()
				setReviewStage(root, thread, voice, "saved", merge(backup, M{"session_id": result["session"], "timing": timings, "preview": A{}}), false)
				_ = os.Remove(draftFile)
				return
			}
			require(trial == 0 && (client != nil || truth(job["retry_requested"])), failure.Error())
			// Keep source-checked suggestions visible while the same draft is repaired.
			setReviewStage(root, thread, voice, "generating", M{"repair_reason": failure.Error(), "preview": checkedPreview(arr(draft["expressions"]), snapshot)}, false)
			draft = generate(merge(payload, M{"prior_draft": draft, "validation_error": failure.Error()}))
			draft = completeReviewBookkeeping(draft, snapshot, language)
			writeJSON(draftFile, draft)
		}
	})
	if client != nil {
		client.close()
	}
	if err != nil && ctx.Err() == nil {
		setReviewStage(root, thread, voice, "error", M{"error": err.Error()}, false)
	}
}
func runReviews(ctx context.Context, root string) {
	lock, ok := tryLock(filepath.Join(root, "Runtime", ".review-worker.lock"))
	if !ok {
		return
	}
	defer lock.Unlock()
	for {
		if ctx.Err() != nil {
			return
		}
		registerReviewWatches(root)
		for _, v := range reverse(recentReviews(root)) {
			job := obj(v)
			if !truth(job["auto_review"]) {
				continue
			}
			thread, voice := str(job["thread_id"]), str(job["voice_id"])
			err := attempt(func() {
				if job["status"] == "practicing" {
					err := attempt(func() { snapshotVoice(str(job["source"]), thread, voice) })
					if err != nil {
						if _, waiting := err.(sourcePendingError); waiting {
							return
						}
						panic(err)
					}
					job = enqueueReview(root, thread, voice, str(job["source"]), false)
				}
				if has(activeReviews, job["status"]) {
					processReview(ctx, root, job)
				}
			})
			if err != nil {
				setReviewStage(root, thread, voice, "error", M{"error": err.Error()}, false)
			}
			if ctx.Err() != nil {
				return
			}
		}
		if !sleepContext(ctx, time.Second) {
			return
		}
	}
}

// Review registration can run without a caption binding. Disabling the companion
// never removes the independent closeout path for this explicitly selected task.
func registerReviewWatches(root string) {
	for _, path := range glob(filepath.Join(root, "Runtime", "ReviewWatches", "*.json")) {
		// A damaged registration must not kill every later review. Keep the
		// original and a separate diagnostic; retry only after its bytes change.
		fingerprint := ""
		failure := attempt(func() {
			fingerprint = hash(readFile(path))
			if marker := obj(maybeJSON(path+".error", M{})); marker["source_hash"] == fingerprint {
				return
			}
			registerReviewWatch(root, path)
			_ = os.Remove(path + ".error")
		})
		if failure != nil {
			writeJSON(path+".error", M{"error": failure.Error(), "source_hash": fingerprint, "at": now()})
		}
	}
}

func registerReviewWatch(root, path string) {
	watch := obj(readJSON(path))
	require(len(watch) > 0, "复盘登记内容无效；原文件保留。")
	thread, source := str(watch["thread_id"]), str(watch["source"])
	if watch["watch_only"] != true {
		return
	}
	require(num(watch["created_epoch"]) > 0 && thread != "" && source != "", "复盘登记缺少来源或创建时间；原文件保留。")
	if epoch()-num(watch["created_epoch"]) > 21600 {
		_ = os.Remove(path)
		return
	}
	require(sourceIdentity(source) == thread, "Review source identity changed")
	next, _ := scanLines(source, int64(num(watch["cursor"])), 2*maxLine, func(row M) {
		if row["type"] != "realtime_item" {
			return
		}
		p := obj(row["payload"])
		if p["type"] == "realtime_session_started" && str(watch["voice_id"]) == "" {
			watch["voice_id"] = p["realtime_session_id"]
		}
	})
	watch["cursor"] = next
	voice := str(watch["voice_id"])
	if voice != "" {
		setReviewStage(root, thread, voice, "practicing", M{"source": source, "title": watch["title"], "auto_review": true}, false)
		must(os.Remove(path))
	} else {
		writeJSON(path, watch)
	}
}
