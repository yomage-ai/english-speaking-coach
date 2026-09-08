package main

import (
	"fmt"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

type Archive struct {
	root      string
	token     string
	signature string
	data      M
}

func newArchive(root string) *Archive { return &Archive{root: absolute(root), token: token()} }
func fingerprint(root string) string {
	parts := []string{}
	files := []string{filepath.Join(root, "Archive", "legacy-v1.md"), filepath.Join(root, "profile.json")}
	for _, d := range []string{"Sessions", "Evidence"} {
		files = append(files, glob(filepath.Join(root, d, "*.md"))...)
	}
	for _, p := range files {
		parts = append(parts, p+"/"+hash(readFile(p)))
	}
	return hash([]byte(strings.Join(parts, "\n")))
}
func bookFor(s M) string {
	text := str(s["title"]) + compact(s["topics"]) + compact(s["scenarios"])
	for _, pair := range [][2]string{{"旅行|机场|出租|打车|点餐", "旅行出行"}, {"宠物|兽医|领养", "宠物咨询"}, {"日常|音乐|计划|聊天", "日常聊天"}} {
		if regexp.MustCompile(pair[0]).MatchString(text) {
			return pair[1]
		}
	}
	a := arr(s["topics"])
	if len(a) > 0 {
		return str(a[0])
	}
	return "其他主题"
}
func readRecord(root string, s M) (M, string) {
	path := filepath.Join(root, "Sessions", str(s["id"])+".md")
	record := extract(path, "speaking-record-v2")
	text := string(readFile(path))
	if record != nil {
		supplement := ""
		if parts := strings.SplitN(text, "## 我的补充\n", 2); len(parts) == 2 {
			supplement = strings.TrimSpace(parts[1])
			if strings.HasPrefix(supplement, "可在这里自由补充学习笔记；") {
				p := strings.SplitN(supplement, "\n", 2)
				supplement = ""
				if len(p) > 1 {
					supplement = strings.TrimSpace(p[1])
				}
			}
		}
		return record, supplement
	}
	rows := A{}
	if parts := strings.SplitN(text, "## 精选表达与证据", 2); len(parts) > 1 {
		table := strings.SplitN(parts[1], "\n## ", 2)[0]
		for _, line := range strings.Split(table, "\n") {
			line = strings.TrimSpace(line)
			placeholder := "\x00PIPE\x00"
			cells := strings.Split(strings.ReplaceAll(line, `\|`, placeholder), "|")
			if len(cells) == 8 {
				cells = cells[1:7]
				for i := range cells {
					cells[i] = strings.TrimSpace(strings.ReplaceAll(cells[i], placeholder, "|"))
				}
				if cells[0] != "用户原话" && cells[0] != "---" {
					rows = append(rows, M{"original": cells[0], "english": cells[1], "chinese": cells[2], "note": "旧课次记载：" + cells[4] + "。这是当时保存的状态；未补造更详细的提示过程。"})
				}
			}
		}
	}
	return merge(s, M{"expressions": rows, "evidence_note": "旧课次原话与状态直接读取原始 Markdown 表格；保留当时的判断，不用当前索引改写旧证据。文字不能证明发音准确。"}), ""
}
func (a *Archive) load() M {
	sig := fingerprint(a.root)
	if sig == a.signature && a.data != nil {
		return a.data
	}
	for trial := 0; trial < 3; trial++ {
		sig = fingerprint(a.root)
		state := buildState(a.root)
		sessions, terms, details := A{}, A{}, M{}
		for _, v := range reverse(arr(state["sessions"])) {
			raw := obj(v)
			s := merge(raw, M{"book": bookFor(raw), "expression_count": len(arr(raw["expression_ids"]))})
			record, supplement := readRecord(a.root, raw)
			sessions = append(sessions, s)
			details[str(s["id"])] = merge(s, M{"evidence_note": get(record, "evidence_note", ""), "excerpts": get(record, "expressions", A{}), "supplement": supplement})
		}
		byID := M{}
		for _, v := range sessions {
			byID[str(obj(v)["id"])] = v
		}
		for _, v := range reverse(arr(state["expressions"])) {
			raw := obj(v)
			source := obj(byID[str(raw["source_session"])])
			require(len(source) > 0, "Expression source session is missing")
			t := merge(raw, M{"book": source["book"], "source_title": source["title"], "date": source["date"], "state_label": get(mastery, str(raw["mastery"]), "未记录")})
			sources := A{}
			for _, sid := range arr(get(raw, "seen_in_sessions", A{source["id"]})) {
				s := obj(byID[str(sid)])
				if len(s) > 0 {
					sources = append(sources, pick(s, "id", "title", "date"))
				}
			}
			t["sources"] = sources
			terms = append(terms, t)
		}
		for _, v := range arr(state["concepts"]) {
			c := obj(v)
			events := arr(c["events"])
			relatedIDs, sids := M{}, A{}
			for _, v := range events {
				e := obj(v)
				sids = append(sids, e["session"])
				for _, id := range arr(e["expression_ids"]) {
					relatedIDs[str(id)] = true
				}
			}
			var matching M
			for _, v := range terms {
				t := obj(v)
				if strings.Trim(strings.ToLower(str(t["english"])), " .?!") == strings.Trim(strings.ToLower(str(c["term"])), " .?!") && relatedIDs[str(t["id"])] != nil {
					matching = t
					break
				}
			}
			if matching != nil {
				matching["concept_id"] = c["id"]
				continue
			}
			source := obj(byID[str(obj(events[0])["session"])])
			var quote any
			for _, v := range reverse(events) {
				if obj(v)["quote_kind"] == "utterance" {
					quote = obj(v)["quote"]
					break
				}
			}
			next := str(c["last_date"])
			found := false
			for _, v := range terms {
				t := obj(v)
				if relatedIDs[str(t["id"])] != nil {
					if !found || str(t["next_review"]) < next {
						next = str(t["next_review"])
					}
					found = true
				}
			}
			sids = unique(sids)
			sort.Slice(sids, func(i, j int) bool { return str(sids[i]) < str(sids[j]) })
			sources := A{}
			for _, id := range sids {
				sources = append(sources, pick(obj(byID[str(id)]), "id", "title", "date"))
			}
			m := "not_tested"
			if c["level"] == "stable" || c["level"] == "independent" {
				m = "independent"
			} else if c["level"] == "supported" {
				m = "source_text"
			}
			t := M{"id": c["id"], "concept_id": c["id"], "english": c["term"], "chinese": c["meaning"], "kind": "知识点", "original": quote, "mastery": m, "state_label": c["level_label"], "source_session": source["id"], "source_title": source["title"], "date": source["date"], "updated": c["last_date"], "note": obj(events[len(events)-1])["note"], "next_review": next, "book": source["book"], "sources": sources, "seen_in_sessions": sids}
			terms = append(A{t}, terms...)
		}
		for _, v := range sessions {
			s := obj(v)
			count := 0
			for _, v := range terms {
				t := obj(v)
				if has(get(t, "seen_in_sessions", A{t["source_session"]}), s["id"]) {
					count++
				}
			}
			s["card_count"] = count
			obj(details[str(s["id"])])["card_count"] = count
		}
		books := countBooks(terms, sessions)
		if sig != fingerprint(a.root) {
			continue
		}
		a.signature = sig
		a.data = M{"sessions": sessions, "details": details, "terms": terms, "books": books, "concepts": get(state, "concepts", A{}), "profile": state["profile"], "revision": sig[:12], "source_updated_at": now()}
		return a.data
	}
	panic(fmt.Errorf("学习记录正在保存，请稍后刷新。"))
}
func countBooks(terms, sessions A) A {
	names := A{}
	counts := M{}
	for _, v := range terms {
		name := str(obj(v)["book"])
		if counts[name] == nil {
			names = append(names, name)
		}
		counts[name] = integer(counts[name]) + 1
	}
	out := A{}
	for _, v := range names {
		name := str(v)
		r := M{"name": name, "count": counts[name]}
		if sessions != nil {
			n := 0
			for _, v := range sessions {
				if obj(v)["book"] == name {
					n++
				}
			}
			r["sessions"] = n
		}
		out = append(out, r)
	}
	return out
}
func filterRows(rows A, args, data M) A {
	start, end := dateRange(args)
	q := strings.ToLower(strings.TrimSpace(str(args["q"])))
	out := A{}
	for _, v := range rows {
		r := obj(v)
		sid := str(args["session"])
		if sid != "" && !has(obj(obj(data["details"])[sid])["expression_ids"], r["id"]) && !has(r["seen_in_sessions"], sid) {
			continue
		}
		date := str(r["date"])
		if start != "" && date < start || end != "" && date > end {
			continue
		}
		if str(args["book"]) != "" && r["book"] != args["book"] {
			continue
		}
		if str(args["state"]) != "" && r["mastery"] != args["state"] {
			continue
		}
		if args["due"] == "1" && textOr(r["next_review"], "9999") > today() {
			continue
		}
		search := get(obj(data["details"]), str(r["id"]), r)
		if q != "" && !strings.Contains(strings.ToLower(compact(search)), q) {
			continue
		}
		out = append(out, r)
	}
	return out
}
func clampInt(v any, def, low, high int) int {
	n := def
	if s, ok := v.(string); ok && s != "" {
		i, e := strconv.Atoi(s)
		must(e)
		n = i
	} else if v != nil {
		n = integer(v)
	}
	return min(high, max(low, n))
}
func (a *Archive) query(path string, args M) M {
	if path == "/api/live" {
		l := openLive(a.root)
		defer l.close()
		return l.view(args)
	}
	data := a.load()
	meta := pick(data, "revision", "source_updated_at")
	sessions, terms := arr(data["sessions"]), arr(data["terms"])
	switch path {
	case "/api/overview":
		days := M{}
		for _, v := range sessions {
			days[str(obj(v)["date"])] = true
		}
		var latest any
		if len(sessions) > 0 {
			latest = obj(data["details"])[str(obj(sessions[0])["id"])]
		}
		due := A{}
		for _, v := range terms {
			if textOr(obj(v)["next_review"], "9999") <= today() {
				due = append(due, v)
			}
		}
		return merge(meta, M{"today": today(), "counts": M{"sessions": len(sessions), "terms": len(terms), "days": len(days), "books": len(arr(data["books"]))}, "books": data["books"], "profile": data["profile"], "latest": latest, "recent": head(sessions, 4), "review_terms": head(due, 3)})
	case "/api/review":
		thread, voice := str(args["thread"]), str(args["voice"])
		sources := voiceSources(thread, voice)
		matches := A{}
		for _, v := range sessions {
			s := obj(v)
			if has(s["source_ids"], sources[0]) && has(s["source_ids"], sources[1]) {
				matches = append(matches, s)
			}
		}
		require(len(matches) <= 1, "同一场 Voice 有多份复盘，请核对来源。")
		job := reviewStatus(a.root, thread, voice)
		var saved M
		if len(matches) > 0 {
			saved = obj(matches[0])
			job["status"], job["stage"], job["elapsed_seconds"] = "saved", "saved", nil
		}
		practiceTime := textOr(saved["practiced_at"], "")
		if practiceTime == "" && num(job["created_epoch"]) > 0 {
			practiceTime = timeFromEpoch(num(job["created_epoch"]))
		}
		return merge(meta, omit(job, "source", "worker_pid"), M{"thread_id": thread, "voice_id": voice, "created_epoch": get(job, "created_epoch", get(job, "started_epoch", 0)), "title": textOr(saved["title"], textOr(job["title"], "本次英语练习")), "practice_time": practiceTime, "session_id": saved["id"]})
	case "/api/reviews":
		jobs := recentReviews(a.root)
		out := A{}
		for i, v := range jobs {
			j := obj(v)
			item := a.query("/api/review", M{"thread": j["thread_id"], "voice": j["voice_id"]})
			if i < 5 || item["status"] != "saved" {
				out = append(out, item)
			}
		}
		return merge(meta, M{"items": out})
	case "/api/sessions", "/api/terms":
		rows := terms
		if path == "/api/sessions" {
			rows = sessions
		}
		rows = filterRows(rows, args, data)
		limit := clampInt(args["limit"], 12, 1, 60)
		paged := paginate(rows, args, limit)
		scoped := terms
		if str(args["session"]) != "" {
			scoped = filterRows(terms, M{"session": args["session"]}, data)
		}
		books := data["books"]
		if path == "/api/terms" {
			books = countBooks(scoped, nil)
		}
		var latest any
		if len(sessions) > 0 {
			latest = pick(obj(sessions[0]), "id", "title")
		}
		return merge(meta, paged, M{"books": books, "scope": M{"session_id": args["session"], "session_title": obj(obj(data["details"])[str(args["session"])])["title"], "count": len(scoped), "all_count": len(terms)}, "latest_session": latest})
	case "/api/progress":
		return merge(meta, progressList(arr(data["concepts"]), args))
	case "/api/stats":
		selected := filterRows(sessions, args, data)
		ids, days, activity := M{}, M{}, M{}
		observations := A{}
		for _, v := range selected {
			s := obj(v)
			ids[str(s["id"])] = true
			date := str(s["date"])
			days[date] = true
			activity[date] = integer(activity[date]) + 1
			for _, v := range arr(s["progress"]) {
				observations = append(observations, M{"id": s["id"], "date": date, "text": v})
			}
		}
		n := 0
		for _, v := range terms {
			if ids[str(obj(v)["source_session"])] != nil {
				n++
			}
		}
		rows := periodRows(arr(data["concepts"]), args)
		highlights := append(A{}, rows...)
		priority := M{"improved": 0, "revisit": 1, "first": 2, "practiced": 3}
		sort.SliceStable(highlights, func(i, j int) bool {
			return integer(priority[str(obj(highlights[i])["change_kind"])]) < integer(priority[str(obj(highlights[j])["change_kind"])])
		})
		review := append(A{}, rows...)
		sortRows(review, func(r M) string { return fmt.Sprintf("%t/%t", !truth(r["needs_revisit"]), r["level"] == "stable") }, false)
		return merge(meta, M{"counts": M{"sessions": len(selected), "days": len(days), "terms": n}, "activity": activity, "highlights": head(highlights, 3), "progress_total": len(rows), "observations": head(observations, 3), "review": head(review, 2)})
	}
	if strings.HasPrefix(path, "/api/sessions/") {
		s := obj(obj(data["details"])[strings.TrimPrefix(path, "/api/sessions/")])
		require(len(s) > 0, "没有找到这次练习。")
		return merge(meta, s)
	}
	if strings.HasPrefix(path, "/api/terms/") {
		id := strings.TrimPrefix(path, "/api/terms/")
		for _, v := range terms {
			if obj(v)["id"] == id {
				return merge(meta, obj(v))
			}
		}
		panic(fmt.Errorf("没有找到这条表达。"))
	}
	if strings.HasPrefix(path, "/api/progress/") {
		return merge(meta, progressDetail(arr(data["concepts"]), strings.TrimPrefix(path, "/api/progress/"), args))
	}
	panic(fmt.Errorf("页面不存在。"))
}
