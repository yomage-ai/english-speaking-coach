package main

import (
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

var dimensions = M{"meaning": "理解词义", "reading": "顺畅朗读", "use": "自主运用"}
var results = M{"needs_help": "当时还不明白", "explained": "获得解释", "supported": "有提示完成", "success": "成功完成"}
var supports = M{"model": "完整示范", "keywords": "关键词提示", "none": "无语言提示"}
var levels = M{"encountered": "开始认识它", "supported": "有提示能完成", "independent": "曾自主用出", "stable": "表达已较稳定"}

func validateObservations(v any) {
	_, ok := v.([]any)
	require(ok, "concept_observations must be a list")
	seen := M{}
	for _, v := range arr(v) {
		o := obj(v)
		for _, k := range []string{"id", "concept_id", "term", "meaning", "dimension", "result", "support", "modality", "context", "note", "quote_kind", "quote"} {
			require(strings.TrimSpace(str(o[k])) != "", "Concept observation missing "+k)
		}
		id := str(o["id"])
		require(regexp.MustCompile(`^OBS-[A-Za-z0-9_-]+$`).MatchString(id) && seen[id] == nil, "Invalid/duplicate observation ID")
		seen[id] = true
		require(regexp.MustCompile(`^CON-[A-Za-z0-9_-]+$`).MatchString(str(o["concept_id"])), "Invalid concept ID")
		require(dimensions[str(o["dimension"])] != nil && results[str(o["result"])] != nil && supports[str(o["support"])] != nil, "Invalid evidence classification")
		require(has(stringsA("text", "transcript", "audio"), o["modality"]) && has(stringsA("utterance", "session_note"), o["quote_kind"]), "Invalid evidence source")
		if o["result"] == "success" {
			require(o["quote_kind"] == "utterance", "Success needs actual utterance evidence")
			if o["dimension"] == "reading" {
				require(o["modality"] == "audio", "Reading fluency needs audio evidence")
			} else {
				require(o["support"] == "none", "Independent success cannot have a supplied answer")
			}
		}
		if o["result"] == "supported" {
			require(o["support"] != "none", "Supported completion must name the support")
		}
		_, ok := get(o, "expression_ids", A{}).([]any)
		require(ok, "expression_ids must be a list")
	}
}
func collectProgress(root string, state M, extra M) A {
	sessions := M{}
	expressionIDs := M{}
	records := A{}
	for _, v := range arr(state["sessions"]) {
		s := obj(v)
		sessions[str(s["id"])] = s
		records = append(records, M{"session": s["id"], "date": s["date"], "source_ids": get(s, "source_ids", A{}), "concept_observations": get(s, "concept_observations", A{})})
	}
	for _, v := range arr(state["expressions"]) {
		expressionIDs[str(obj(v)["id"])] = true
	}
	for _, p := range glob(filepath.Join(root, "Evidence", "*.md")) {
		r := extract(p, "speaking-evidence-v1")
		require(r != nil && str(r["id"])+".md" == filepath.Base(p), "Evidence file/ID mismatch")
		records = append(records, r)
	}
	if extra != nil {
		records = append(records, extra)
	}
	concepts, seen := M{}, M{}
	for _, v := range records {
		r := obj(v)
		s := obj(sessions[str(r["session"])])
		require(len(s) > 0 && r["date"] == s["date"], "Evidence must link to an actual session/date")
		obs := get(r, "concept_observations", A{})
		validateObservations(obs)
		if len(arr(obs)) > 0 {
			checkStrings(r["source_ids"], "Evidence source_ids")
			require(len(arr(r["source_ids"])) > 0, "Evidence needs source IDs")
		}
		for _, v := range arr(obs) {
			raw := obj(v)
			for _, id := range arr(raw["expression_ids"]) {
				require(expressionIDs[str(id)] != nil, "Unknown expression reference")
			}
			event := merge(raw, M{"date": r["date"], "session": r["session"], "source_ids": r["source_ids"], "session_title": s["title"]})
			if s["practiced_at"] != nil {
				event["practiced_at"] = s["practiced_at"]
			}
			id := str(event["id"])
			if seen[id] != nil {
				require(equal(seen[id], event), "Conflicting observation ID")
				continue
			}
			seen[id] = event
			cid := str(raw["concept_id"])
			c := obj(concepts[cid])
			if len(c) == 0 {
				c = M{"id": cid, "term": raw["term"], "meaning": raw["meaning"], "events": A{}}
				concepts[cid] = c
			}
			require(c["term"] == raw["term"] && c["meaning"] == raw["meaning"], "Concept ID has a different term/meaning; use a separate sense ID")
			c["events"] = append(arr(c["events"]), event)
		}
	}
	out := A{}
	for _, c := range concepts {
		out = append(out, summarizeConcept(obj(c)))
	}
	sortRows(out, func(c M) string { return str(c["last_date"]) + str(c["id"]) }, true)
	return out
}
func summarizeConcept(c M) M {
	events := arr(c["events"])
	sortRows(events, func(e M) string { return order(merge(e, M{"id": e["session"]})) + str(e["id"]) }, false)
	require(len(events) > 0, "Concept needs evidence")
	dims := M{}
	for key, label := range dimensions {
		var last M
		for _, v := range events {
			e := obj(v)
			if e["dimension"] == key {
				last = e
			}
		}
		status := any("还没有观察")
		if last != nil {
			status = results[str(last["result"])]
		}
		dims[key] = M{"label": label, "status": status, "evidence": last, "successful": last != nil && last["result"] == "success"}
	}
	days, contexts := M{}, M{}
	supported := false
	for _, v := range events {
		e := obj(v)
		if e["dimension"] == "use" && e["result"] == "success" && e["support"] == "none" {
			days[str(e["date"])] = true
			contexts[strings.ToLower(strings.TrimSpace(str(e["context"])))] = true
		}
		supported = supported || e["result"] == "supported"
	}
	independent := truth(obj(dims["use"])["successful"])
	stable := len(days) >= 2 && len(contexts) >= 2 && independent
	level := "encountered"
	if stable {
		level = "stable"
	} else if independent {
		level = "independent"
	} else if supported {
		level = "supported"
	}
	next := "下次聊到相关话题时，先自己试一句，再按需要提示。"
	if len(days) > 0 {
		next = "隔天换个场景，在没有示范的情况下试着用出来。"
	}
	if stable {
		next = "换个话题再自然用一次，看看是否仍然顺手。"
	}
	return merge(c, M{"events": events, "dimensions": dims, "level": level, "level_label": levels[level], "needs_revisit": len(days) > 0 && !independent, "first_date": obj(events[0])["date"], "last_date": obj(events[len(events)-1])["date"], "independent_days": len(days), "context_count": len(contexts), "next_step": next})
}
func briefConcept(c M) M {
	r := pick(c, "id", "term", "meaning", "level", "level_label", "needs_revisit", "first_date", "last_date", "independent_days", "context_count", "next_step")
	r["event_count"] = len(arr(c["events"]))
	dims := M{}
	for k, v := range obj(c["dimensions"]) {
		d := obj(v)
		dims[k] = merge(pick(d, "label", "status", "successful"), M{"date": obj(d["evidence"])["date"]})
	}
	r["dimensions"] = dims
	return r
}
func dateRange(a M) (string, string) {
	start, end := str(a["from"]), str(a["to"])
	for _, s := range []string{start, end} {
		if s != "" {
			checkDate(s)
		}
	}
	require(start == "" || end == "" || start <= end, "开始日期不能晚于结束日期。")
	return start, end
}
func periodRows(concepts A, a M) A {
	start, end := dateRange(a)
	out := A{}
	for _, v := range concepts {
		c := obj(v)
		selected, upto, prior := A{}, A{}, A{}
		for _, v := range arr(c["events"]) {
			e := obj(v)
			date := str(e["date"])
			if (start == "" || date >= start) && (end == "" || date <= end) {
				selected = append(selected, e)
			}
			if end == "" || date <= end {
				upto = append(upto, e)
			}
			if start != "" && date < start {
				prior = append(prior, e)
			}
		}
		if len(selected) == 0 {
			continue
		}
		cur := summarizeConcept(merge(c, M{"events": upto}))
		r := briefConcept(cur)
		last := obj(selected[len(selected)-1])
		r["period_event_count"] = len(selected)
		r["last_session"] = last["session"]
		r["latest_in_period"] = last["date"]
		kind, text := "first", "首次留下练习记录；"+str(cur["level_label"])
		if len(prior) > 0 {
			prev := summarizeConcept(merge(c, M{"events": prior}))
			improved := []string{}
			for _, k := range []string{"meaning", "reading", "use"} {
				d := obj(obj(cur["dimensions"])[k])
				if truth(d["successful"]) && !truth(obj(obj(prev["dimensions"])[k])["successful"]) {
					improved = append(improved, str(d["label"]))
				}
			}
			if truth(cur["needs_revisit"]) {
				kind, text = "revisit", "最近又需要帮助，可以再练一次"
			} else if len(improved) > 0 {
				kind, text = "improved", "有了新的成功表现："+strings.Join(improved, "、")
			} else if cur["level"] == "stable" && prev["level"] != "stable" {
				kind, text = "improved", "跨日、换场景后，仍能自主运用"
			} else {
				kind, text = "practiced", "再次练习；"+str(cur["level_label"])
			}
		}
		r["change_kind"], r["change_text"] = kind, text
		out = append(out, r)
	}
	sortRows(out, func(r M) string { return str(r["latest_in_period"]) + str(r["id"]) }, true)
	return out
}
func paginate(rows A, a M, limit int) M {
	pages := max(1, (len(rows)+limit-1)/limit)
	page := clampInt(a["page"], 1, 1, pages)
	start := (page - 1) * limit
	return M{"items": rows[start:min(start+limit, len(rows))], "page": page, "pages": pages, "total": len(rows), "limit": limit}
}
func progressList(concepts A, a M) M {
	rows := periodRows(concepts, a)
	q, stage := strings.ToLower(strings.TrimSpace(str(a["q"]))), str(a["stage"])
	require(stage == "" || stage == "revisit" || levels[stage] != nil, "未知的练习状态。")
	out := A{}
	for _, v := range rows {
		r := obj(v)
		if q != "" && !strings.Contains(strings.ToLower(str(r["term"])+" "+str(r["meaning"])), q) {
			continue
		}
		if stage != "" && !(stage == "revisit" && truth(r["needs_revisit"])) && r["level"] != stage {
			continue
		}
		out = append(out, r)
	}
	return merge(paginate(out, a, 20), M{"as_of": a["to"], "stages": merge(levels, M{"encountered": "开始学习"})})
}
func progressDetail(concepts A, id string, a M) M {
	var c M
	for _, v := range concepts {
		if obj(v)["id"] == id {
			c = obj(v)
		}
	}
	require(c != nil, "没有找到这个词句的练习历程。")
	month := str(a["month"])
	if month != "" {
		checkDate(month + "-01")
	}
	events := arr(c["events"])
	months, selected := A{}, A{}
	for _, v := range reverse(events) {
		e := obj(v)
		m := str(e["date"])[:7]
		months = append(months, m)
		if month == "" || month == m {
			selected = append(selected, e)
		}
	}
	months = unique(months)
	sort.Slice(months, func(i, j int) bool { return str(months[i]) > str(months[j]) })
	first := obj(events[0])
	milestones := A{M{"label": "首次记录", "date": first["date"], "session": first["session"]}}
	for _, pair := range [][2]string{{"meaning", "首次独立理解"}, {"reading", "首次顺畅读出"}, {"use", "首次自主用出"}} {
		for _, v := range events {
			e := obj(v)
			if e["dimension"] == pair[0] && e["result"] == "success" {
				milestones = append(milestones, M{"label": pair[1], "date": e["date"], "session": e["session"]})
				break
			}
		}
	}
	return merge(briefConcept(c), M{"history": paginate(selected, a, 10), "months": months, "milestones": milestones, "month": month})
}

var wordRE = regexp.MustCompile(`[\pL\pN]+(?:['’][\pL\pN]+)*`)

func words(s string) A {
	out := A{}
	for _, s := range wordRE.FindAllString(strings.ToLower(s), -1) {
		out = append(out, s)
	}
	return out
}
func shortText(v any, label string, limit int) {
	require(strings.TrimSpace(str(v)) != "" && len([]rune(str(v))) <= limit, label+" must be short nonempty text")
}
func exactKeys(m M, keys ...string) bool {
	if len(m) != len(keys) {
		return false
	}
	for _, k := range keys {
		if _, ok := m[k]; !ok {
			return false
		}
	}
	return true
}
func validateGuide(g M, english string) {
	require(exactKeys(g, "kind", "groups", "tone", "tone_note", "memory"), "reading_guide needs kind, groups, tone, tone_note and memory")
	require(g["kind"] == "suggestion", "Reading guidance is a suggestion")
	groups := arr(g["groups"])
	require(len(groups) >= 1 && len(groups) <= 6, "Reading guide needs 1–6 groups")
	all := []string{}
	for _, v := range groups {
		x := obj(v)
		require(exactKeys(x, "text", "stress"), "Reading group needs text and stress")
		shortText(x["text"], "Group text", 350)
		stress := arr(x["stress"])
		require(len(stress) <= 3 && len(unique(stress)) == len(stress), "Up to three unique stressed words")
		for _, v := range stress {
			w := strings.ToLower(str(v))
			require(equal(words(w), stringsA(w)) && has(words(str(x["text"])), w), "Stress must identify a word in the group")
		}
		all = append(all, str(x["text"]))
	}
	require(equal(words(strings.Join(all, " ")), words(english)), "Reading groups must preserve original words in order")
	require(has(stringsA("rise", "fall", "level", "fall-rise", "context"), g["tone"]), "Unknown reading tone")
	shortText(g["tone_note"], "Tone note", 240)
	memory := arr(g["memory"])
	require(len(memory) >= 1 && len(memory) <= 4, "Memory needs 1–4 parts")
	for _, v := range memory {
		x := obj(v)
		require(exactKeys(x, "text", "meaning"), "Memory part needs text and meaning")
		shortText(x["text"], "Memory part", 160)
		shortText(x["meaning"], "Memory meaning", 160)
	}
}
