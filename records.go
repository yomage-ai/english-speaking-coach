package main

import (
	"encoding/json"
	"fmt"
	"html"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

var sessionID = regexp.MustCompile(`^SES-\d{8}-\d{3}$`)
var expressionID = regexp.MustCompile(`^EXP-\d{8}-\d{3}$`)
var mastery = M{"not_tested": "尚未尝试", "source_text": "有原句提示说出", "keywords": "借关键词说出", "independent": "曾独立说出", "transfer": "曾换场景使用"}

func block(marker string, v any) string { return "<!-- " + marker + "\n" + string(encode(v)) + "-->\n" }
func extract(p, marker string) M {
	t := string(readFile(p))
	start := strings.Index(t, "<!-- "+marker+"\n")
	if start < 0 {
		return nil
	}
	t = t[start+len(marker)+6:]
	end := strings.Index(t, "-->")
	require(end >= 0, "Incomplete record block: "+p)
	var v M
	must(json.Unmarshal([]byte(t[:end]), &v))
	return v
}
func profileDefault() M {
	return M{"schema_version": 1, "goal": "清楚、自然地表达自己的想法 / Express ideas clearly and naturally", "practice_language": "english_first", "help_language": "zh-CN", "mode": "roleplay", "correction": "in_character", "drills": "guided", "review_delivery": "written", "review_limit": 2, "input_support": "adaptive", "source_ids": A{}, "updated": today()}
}
func initialize(root string) {
	for _, d := range []string{"Sessions", "Weeks", "Archive", "Pending", "Evidence"} {
		mkdir(filepath.Join(root, d))
	}
	p := filepath.Join(root, "Archive", "legacy-v1.md")
	if !exists(p) {
		old := obj(maybeJSON(filepath.Join(root, "state.json"), M{"schema_version": 1, "project_id": "PRJ-ENGLISH-SPEAKING", "updated": "", "learner": M{}, "sessions": A{}, "expressions": A{}, "weekly_reviews": A{}}))
		require(integer(old["schema_version"]) == 1, "Legacy archive missing; restore it before rebuilding")
		hashes := M{}
		for _, v := range arr(old["sessions"]) {
			sid := str(obj(v)["id"])
			require(sessionID.MatchString(sid), "Unsafe legacy ID")
			hashes[sid] = hash(readFile(filepath.Join(root, "Sessions", sid+".md")))
		}
		atomicWrite(p, []byte("# 旧版学习状态原样归档 / Original legacy archive\n\n"+block("speaking-legacy-v1", M{"state": old, "session_hashes": hashes})))
	}
	if !exists(filepath.Join(root, "profile.json")) {
		writeJSON(filepath.Join(root, "profile.json"), profileDefault())
	}
}
func ensureWorkspace(w M) {
	root := str(w["data_root"])
	if exists(filepath.Join(root, "profile.json")) {
		return
	}
	require(str(w["mode"]) == "user-data" && emptyDir(root), "Configured archive is unavailable; no empty replacement created")
	withLock(filepath.Join(root, ".write.lock"), func() {
		initialize(root)
		rebuild(root)
		writeJSON(configPath(), M{"schema_version": 1, "data_root": root, "project_page": nil})
	})
}
func validateProfile(p M) {
	require(strings.TrimSpace(str(p["goal"])) != "", "goal must be nonempty")
	choices := map[string][]string{"practice_language": {"english_first", "bilingual"}, "help_language": {"zh-CN", "en"}, "mode": {"conversation", "roleplay", "focused"}, "correction": {"light", "detailed", "after_scene", "in_character"}, "drills": {"on_request", "guided"}}
	for k, a := range choices {
		require(has(stringsA(a...), p[k]), "Invalid preference: "+k)
	}
	require(has(stringsA("written", "spoken"), get(p, "review_delivery", "spoken")), "Invalid review delivery")
	require(has(stringsA("adaptive", "short_turns"), get(p, "input_support", "adaptive")), "Invalid input support")
	require(num(p["review_limit"]) == float64(integer(p["review_limit"])) && num(p["review_limit"]) >= 0 && num(p["review_limit"]) <= 5, "review_limit must be 0–5")
	checkStrings(p["source_ids"], "source_ids")
	checkDate(p["updated"])
}
func validatePayload(d M, inProgress bool) {
	for _, k := range []string{"id", "date", "title", "summary", "source_ids", "expressions"} {
		_, ok := d[k]
		require(ok, "Missing session field: "+k)
	}
	require(sessionID.MatchString(str(d["id"])), "Invalid session ID")
	checkDate(d["date"])
	require(str(d["id"])[4:12] == strings.ReplaceAll(str(d["date"]), "-", ""), "Session ID date differs from practice date")
	if d["practiced_at"] != nil {
		require(stamp(str(d["practiced_at"])).Format("2006-01-02") == str(d["date"]), "Invalid practice timestamp")
	}
	for _, k := range []string{"title", "summary"} {
		require(strings.TrimSpace(str(d[k])) != "", k+" must be nonempty")
	}
	checkStrings(d["source_ids"], "source_ids")
	require(len(arr(d["source_ids"])) > 0, "Actual source_ids required")
	for _, k := range []string{"topics", "scenarios", "progress", "next_focus", "unfinished", "coaching_notes"} {
		checkStrings(get(d, k, A{}), k)
	}
	require(len(arr(d["next_focus"])) <= 2 && len(arr(d["coaching_notes"])) <= 3, "Too many focus/coaching notes")
	for _, v := range arr(d["coaching_notes"]) {
		require(len([]rune(str(v))) <= 500, "Coaching note too long")
	}
	end := textOr(d["end_status"], "ended")
	require(end == "ended" || inProgress && end == "in_progress", "Only ended sessions can be committed")
	require(has(stringsA("selected", "partial"), get(d, "evidence_status", "selected")), "Invalid evidence status")
	if d["recovered_on"] != nil {
		checkDate(d["recovered_on"])
	}
	_, ok := d["expressions"].([]any)
	require(ok, "expressions must be a list")
	validateObservations(get(d, "concept_observations", A{}))
	seen := M{}
	for _, v := range arr(d["expressions"]) {
		x := obj(v)
		for _, k := range []string{"id", "english", "chinese", "mastery", "next_review", "note"} {
			require(strings.TrimSpace(str(x[k])) != "", "Expression missing text: "+k)
		}
		id := str(x["id"])
		require(expressionID.MatchString(id) && seen[id] == nil, "Invalid/duplicate expression ID")
		seen[id] = true
		checkDate(x["next_review"])
		require(mastery[str(x["mastery"])] != nil, "Invalid mastery")
		if x["original"] != nil {
			_, ok := x["original"].(string)
			require(ok, "original must be text")
		}
		checkStrings(get(x, "issue_tags", A{}), "issue_tags")
		if x["reading_guide"] != nil {
			validateGuide(obj(x["reading_guide"]), str(x["english"]))
		}
		r, p := str(x["review_result"]), str(x["review_prompt"])
		if r != "" || p != "" {
			require(has(stringsA("failed", "partial", "success", "transfer_success"), r) && has(stringsA("source_text", "keywords", "none", "changed_context"), p) && str(x["original"]) != "", "Attempt requires actual wording, result and prompt")
		}
		switch x["mastery"] {
		case "independent":
			require(r == "success" && p == "none", "Independent mastery needs an unprompted attempt")
		case "transfer":
			require(r == "transfer_success" && p == "changed_context", "Transfer needs a matching attempt")
		case "not_tested":
			require(r == "" && p == "", "Untested collection cannot contain a scored attempt")
		}
	}
	if ids, ok := d["review_priority_ids"]; ok {
		checkStrings(ids, "review_priority_ids")
		require(len(arr(ids)) <= 3 && len(unique(arr(ids))) == len(arr(ids)), "Invalid review priorities")
		for _, id := range arr(ids) {
			require(seen[str(id)] != nil, "Priority not in session")
		}
	}
	if c, ok := d["review_coverage"]; ok {
		x := obj(c)
		total, n := integer(x["available_learner_turns"]), integer(x["selected_learner_turns"])
		require(n >= 0 && total == n+len(obj(x["omitted_turns"])), "Coverage does not reconcile")
		for k, v := range obj(x["omitted_turns"]) {
			require(k != "" && strings.TrimSpace(str(v)) != "", "Omission needs a reason")
		}
	}
	recordFrontmatter(d)
}
func recordFrontmatter(d M) string {
	m := M{"id": d["id"], "type": "english-practice", "sensitivity": "private", "created": d["date"], "source_ids": d["source_ids"]}
	for k, v := range obj(d["record_metadata"]) {
		require(has(stringsA("type", "status", "primary_project", "related_projects", "domains", "sensitivity"), k), "Unsupported record metadata")
		if _, ok := v.(string); !ok {
			checkStrings(v, "metadata")
		}
		m[k] = v
	}
	keys := []string{}
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := "---\n"
	for _, k := range keys {
		out += k + ": " + compact(m[k]) + "\n"
	}
	return out + "---\n\n"
}
func sessionMarkdown(d M) string {
	out := recordFrontmatter(d) + "# " + str(d["title"]) + "\n\n" + str(d["date"]) + "\n\n" + str(d["summary"]) + "\n\n"
	for _, v := range arr(d["expressions"]) {
		x := obj(v)
		out += "## " + str(x["english"]) + "\n\n" + str(x["chinese"]) + "\n\n**我当时说：** " + textOr(x["original"], "未保留原话；仅收集表达，尚未测试。") + "\n\n**这次观察：** " + str(x["note"]) + "\n\n**提示情况：** " + str(mastery[str(x["mastery"])]) + "；建议复习 " + str(x["next_review"]) + "\n\n"
		if x["reading_guide"] != nil {
			g := obj(x["reading_guide"])
			parts := []string{}
			for _, v := range arr(g["groups"]) {
				parts = append(parts, str(obj(v)["text"]))
			}
			out += "怎么念（参考）：" + strings.Join(parts, " / ") + "\n\n" + str(g["tone_note"]) + "\n\n"
		}
	}
	for _, v := range arr(d["concept_observations"]) {
		x := obj(v)
		out += "## " + str(x["term"]) + " · " + str(dimensions[str(x["dimension"])]) + "\n\n" + str(x["meaning"]) + "\n\n来源选段：" + str(x["quote"]) + "\n\n" + str(x["note"]) + "\n\n"
	}
	for _, pair := range [][2]string{{"progress", "本次观察"}, {"next_focus", "后续可练的表达能力"}, {"coaching_notes", "教练下次如何调整"}, {"unfinished", "尚未聊完"}, {"source_ids", "来源与证据边界"}} {
		out += "## " + pair[1] + "\n\n"
		for _, v := range arr(d[pair[0]]) {
			out += "- " + str(v) + "\n"
		}
		out += "\n"
	}
	out += textOr(d["evidence_note"], "只保留精选转写；文字不能证明发音准确。") + "\n\n" + block("speaking-record-v2", d) + "\n## 我的补充\n\n可在这里自由补充学习笔记；Agent 重建页面时保留本文件。\n"
	return out
}
func buildState(root string) M {
	legacy := extract(filepath.Join(root, "Archive", "legacy-v1.md"), "speaking-legacy-v1")
	require(len(obj(legacy["state"])) > 0, "Legacy archive invalid")
	s := copyM(legacy["state"])
	s["schema_version"] = 2
	for _, k := range []string{"sessions", "expressions", "weekly_reviews"} {
		s[k] = get(s, k, A{})
	}
	oldIDs := M{}
	bySession := M{}
	for _, v := range arr(s["sessions"]) {
		x := obj(v)
		id := str(x["id"])
		require(sessionID.MatchString(id), "Unsafe legacy ID")
		require(exists(filepath.Join(root, "Sessions", id+".md")), "Legacy source missing: "+id)
		oldIDs[id] = true
		bySession[id] = x
	}
	records := A{}
	for _, p := range glob(filepath.Join(root, "Sessions", "*.md")) {
		id := strings.TrimSuffix(filepath.Base(p), ".md")
		if oldIDs[id] != nil {
			continue
		}
		r := extract(p, "speaking-record-v2")
		require(r != nil, "Unindexed session needs explicit migration: "+p)
		validatePayload(r, false)
		require(r["id"] == id, "Session file/ID mismatch")
		records = append(records, r)
		bySession[id] = r
	}
	sortRows(records, order, false)
	expressions := M{}
	for _, v := range arr(s["expressions"]) {
		expressions[str(obj(v)["id"])] = v
	}
	for _, v := range records {
		r := obj(v)
		summary := omit(copyM(r), "expressions")
		ids := A{}
		for _, v := range arr(r["expressions"]) {
			x := obj(v)
			id := str(x["id"])
			ids = append(ids, id)
			prior := obj(expressions[id])
			attempts := arr(clone(get(prior, "attempts", A{})))
			if str(x["review_result"]) != "" {
				attempt := M{"date": r["date"], "session": r["id"], "result": x["review_result"], "prompt": x["review_prompt"], "original": x["original"], "note": x["note"]}
				if evidence := obj(x["attempt_evidence"]); len(evidence) > 0 {
					attempt["original"] = obj(evidence["learner"])["quote"]
					attempt["attempt_evidence"] = clone(evidence)
				}
				attempts = append(attempts, attempt)
			}
			newer := str(prior["updated"]) > str(r["date"])
			for _, sid := range arr(get(prior, "seen_in_sessions", A{prior["source_session"]})) {
				if z := obj(bySession[str(sid)]); len(z) > 0 && order(z) > order(r) {
					newer = true
				}
			}
			merged := copyM(x)
			if newer {
				merged = copyM(prior)
			} else if merged["reading_guide"] == nil && prior["english"] == x["english"] && prior["reading_guide"] != nil {
				merged["reading_guide"] = clone(prior["reading_guide"])
			}
			merged["source_session"] = get(prior, "source_session", r["id"])
			seen := unique(append(arr(get(prior, "seen_in_sessions", A{})), r["id"]))
			sort.Slice(seen, func(i, j int) bool { return str(seen[i]) < str(seen[j]) })
			merged["seen_in_sessions"] = seen
			sortRows(attempts, func(a M) string {
				z := obj(bySession[str(a["session"])])
				if len(z) == 0 {
					return order(a)
				}
				return order(z)
			}, false)
			merged["attempts"] = attempts
			merged["updated"] = max(str(prior["updated"]), str(r["date"]))
			expressions[id] = merged
		}
		summary["expression_ids"] = ids
		s["sessions"] = append(arr(s["sessions"]), summary)
	}
	sortRows(arr(s["sessions"]), order, false)
	s["expressions"] = A{}
	for _, v := range expressions {
		s["expressions"] = append(arr(s["expressions"]), v)
	}
	sortRows(arr(s["expressions"]), func(m M) string { return str(m["id"]) }, false)
	for _, v := range arr(s["sessions"]) {
		s["updated"] = max(str(s["updated"]), str(obj(v)["date"]))
	}
	profile := obj(readJSON(filepath.Join(root, "profile.json")))
	validateProfile(profile)
	s["profile"] = profile
	focus := A{}
	if a := arr(s["sessions"]); len(a) > 0 {
		focus = arr(obj(a[len(a)-1])["next_focus"])
	}
	s["learner"] = merge(obj(s["learner"]), M{"goal": profile["goal"], "current_focus": focus, "practice_style": A{profile["mode"], profile["correction"], profile["drills"]}})
	s["review_strategy"] = M{"name": "contextual-retrieval-v2", "max_due_per_session": profile["review_limit"], "default_intervals_days": M{"not_tested": 1, "source_text": 1, "keywords": 3, "independent": 7, "transfer": 14}}
	s["concepts"] = collectProgress(root, s, nil)
	return s
}
func rebuild(root string) M {
	s := buildState(root)
	writeJSON(filepath.Join(root, "state.json"), s)
	index := "# 英语学习手记 / English practice journal\n\n[本地阅读页](dashboard.html)\n\n"
	htmlText := "<!doctype html><html lang=zh-CN><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>英语学习手记</title><style>body{font:18px system-ui;max-width:850px;margin:3rem auto;padding:1rem;line-height:1.7}article{border-bottom:1px solid #ddd;padding:1rem 0}blockquote{margin:1rem 0;padding:1rem;background:#f3f6fa;border-radius:10px}small{color:#556}a{color:#245bb7}</style><h1>英语学习手记</h1><p>离线阅读快照 / Offline reading snapshot</p>"
	for _, v := range reverse(arr(s["sessions"])) {
		x := obj(v)
		path := "Sessions/" + str(x["id"]) + ".md"
		index += "- [" + str(x["date"]) + " · " + str(x["title"]) + "](" + path + ")\n"
		htmlText += "<article><small>" + html.EscapeString(str(x["date"])) + "</small><h2><a href=\"" + path + "\">" + html.EscapeString(str(x["title"])) + "</a></h2><p>" + html.EscapeString(str(x["summary"])) + "</p>"
		record, supplement := readRecord(root, x)
		for _, v := range arr(record["expressions"]) {
			e := obj(v)
			htmlText += "<blockquote><strong>" + html.EscapeString(str(e["english"])) + "</strong><br>" + html.EscapeString(str(e["chinese"])) + "<br><small>原话 / Original: " + html.EscapeString(str(e["original"])) + "</small><p>" + html.EscapeString(str(e["note"])) + "</p></blockquote>"
		}
		if supplement != "" {
			htmlText += "<p>" + html.EscapeString(supplement) + "</p>"
		}
		htmlText += "</article>"
	}
	atomicWrite(filepath.Join(root, "INDEX.md"), []byte(index))
	atomicWrite(filepath.Join(root, "dashboard.html"), []byte(htmlText))
	return s
}
func commitRecord(root string, d M) M {
	validatePayload(d, false)
	dest := filepath.Join(root, "Sessions", str(d["id"])+".md")
	pending := filepath.Join(root, "Pending", str(d["id"])+".json")
	status := "saved"
	if exists(dest) {
		require(equal(extract(dest, "speaking-record-v2"), d), "Conflicting session ID; existing record preserved")
		status = "already_saved"
	} else {
		prospective := buildState(root)
		prospective["sessions"] = append(arr(prospective["sessions"]), omit(d, "expressions"))
		known := M{}
		for _, v := range arr(prospective["expressions"]) {
			known[str(obj(v)["id"])] = true
		}
		for _, v := range arr(d["expressions"]) {
			if known[str(obj(v)["id"])] == nil {
				prospective["expressions"] = append(arr(prospective["expressions"]), v)
			}
		}
		collectProgress(root, prospective, nil)
		if exists(pending) {
			old := obj(readJSON(pending))
			require(textOr(old["end_status"], "ended") != "ended" || equal(old, d), "Conflicting ended checkpoint; recover it first")
		}
		writeJSON(pending, d)
		atomicWrite(dest, []byte(sessionMarkdown(d)))
	}
	rebuild(root)
	if exists(pending) && equal(readJSON(pending), d) {
		must(os.Remove(pending))
	}
	return M{"status": status, "session": d["id"], "archive_route": "#sessions/" + str(d["id"])}
}
func validateArchive(root string) M {
	s := buildState(root)
	problems := A{}
	if !exists(filepath.Join(root, "state.json")) || !equal(readJSON(filepath.Join(root, "state.json")), s) {
		problems = append(problems, "state.json missing or stale; run rebuild")
	}
	if !exists(filepath.Join(root, "dashboard.html")) {
		problems = append(problems, "dashboard.html missing; run rebuild")
	}
	changed := A{}
	for sid, digest := range obj(extract(filepath.Join(root, "Archive", "legacy-v1.md"), "speaking-legacy-v1")["session_hashes"]) {
		if hash(readFile(filepath.Join(root, "Sessions", sid+".md"))) != digest {
			changed = append(changed, sid)
		}
	}
	return M{"ok": len(problems) == 0, "problems": problems, "sessions": len(arr(s["sessions"])), "expressions": len(arr(s["expressions"])), "legacy_notes_changed": changed, "pending": pendingNames(root)}
}
func pendingNames(root string) A {
	out := A{}
	for _, p := range glob(filepath.Join(root, "Pending", "*.json")) {
		out = append(out, filepath.Base(p))
	}
	return out
}
func nextID(prefix string, used M) string {
	for i := 1; i < 1000; i++ {
		id := fmt.Sprintf("%s%03d", prefix, i)
		if used[id] == nil {
			used[id] = true
			return id
		}
	}
	panic(fmt.Errorf("No available ID for %s", prefix))
}
func addDays(day string, n int) string {
	t, e := time.Parse("2006-01-02", day)
	must(e)
	return t.AddDate(0, 0, n).Format("2006-01-02")
}
