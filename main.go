package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

func parseArgs(args []string) ([]string, M) {
	commands := []string{}
	opts := M{}
	flags := stringsA("workspace", "auto-scene", "opening", "with-project", "compact", "companion", "demo", "manual", "check", "with-transcript", "include-live", "copy-existing", "refresh-translations", "no-browser", "retry", "probe")
	for i := 0; i < len(args); i++ {
		s := args[i]
		if !strings.HasPrefix(s, "--") {
			commands = append(commands, s)
			continue
		}
		k := strings.TrimPrefix(s, "--")
		if k == "help" {
			opts["help"] = true
			continue
		}
		if a := strings.SplitN(k, "=", 2); len(a) == 2 {
			opts[a[0]] = a[1]
			continue
		}
		if has(flags, k) {
			opts[k] = true
			continue
		}
		require(i+1 < len(args), "Missing value for --"+k)
		i++
		opts[k] = args[i]
	}
	if str(opts["thread-id"]) == "" {
		opts["thread-id"] = os.Getenv("CODEX_THREAD_ID")
	}
	return commands, opts
}
func runCLI(args []string) any {
	commands, o := parseArgs(args)
	if len(commands) == 0 || truth(o["help"]) {
		return M{"application": "english-speaking-coach", "version": version, "commands": stringsA("prepare --auto-scene --opening --with-project", "resume --compact --with-project", "serve --workspace --port 8897", "service start|status|stop|resume", "doctor [--probe]", "paths", "init|rebuild|validate", "add-session|finish-review --input FILE", "review-begin|review-context --thread-id UUID --voice-id UUID", "set-preferences --input FILE --expected-profile-sha256 HASH", "checkpoint|recover|add-evidence|export", "live start|status|stop|resume|disable|probe", "recover-voice --thread-id UUID --voice-id UUID", "storage backup|inspect|restore|adopt|move|configure"), "runtime": "Standalone Go; no Python, Node.js or Go installation needed"}
	}
	cmd := commands[0]
	require(has(stringsA("version", "prepare", "paths", "serve", "service", "doctor", "open", "live", "review-begin", "review-context", "resume", "validate", "storage", "recover-voice", "init", "migrate", "rebuild", "render", "add-session", "finish-review", "set-preferences", "checkpoint", "recover", "add-evidence", "export"), cmd), "Unknown command: "+cmd)
	for flag, name := range map[string]string{"codex-home": "CODEX_HOME", "skill-root": "ENGLISH_COACH_SKILL_ROOT", "codex-executable": "ENGLISH_COACH_CODEX"} {
		if value := str(o[flag]); value != "" {
			must(os.Setenv(name, absolute(value)))
		}
	}
	if cmd == "version" {
		return M{"version": version, "code_revision": revision, "runtime": "go"}
	}
	if cmd == "prepare" {
		return preparePractice(o)
	}
	w := workspace(str(o["root"]))
	if str(o["vault"]) != "" {
		base := filepath.Join(absolute(str(o["vault"])), "vault", "Work", "Projects")
		w = M{"data_root": filepath.Join(base, "English-Speaking"), "project_page": filepath.Join(base, "PRJ-ENGLISH-SPEAKING.md"), "mode": "vault", "config_path": configPath()}
	}
	root := str(w["data_root"])
	thread, voice := str(o["thread-id"]), str(o["voice-id"])
	source := str(o["source"])
	day := textOr(o["today"], today())
	checkDate(day)
	if cmd == "paths" {
		return w
	}
	if cmd == "serve" {
		ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer cancel()
		serve(ctx, root, clampInt(o["port"], 8897, 0, 65535), str(o["root"]) == "")
		return nil
	}
	if cmd == "service" {
		action := "status"
		if len(commands) > 1 {
			action = commands[1]
		}
		switch action {
		case "start":
			ensureWorkspace(w)
			return serviceStart(root, str(o["root"]) == "")
		case "resume":
			receipt := obj(maybeJSON(serviceReceipt(), M{}))
			require(len(receipt) == 0 || truth(receipt["stopped"]), "Only a deliberately stopped service can be resumed; inspect an unavailable manager first")
			if exists(serviceReceipt()) {
				must(os.Remove(serviceReceipt()))
			}
			ensureWorkspace(w)
			return serviceStart(root, str(o["root"]) == "")
		case "stop":
			serviceStop()
			return M{"status": "stopped"}
		case "status":
			return checkService(textOr(o["service-url"], "http://127.0.0.1:8897"), root, false)
		}
		panic("Unknown service command")
	}
	if cmd == "doctor" {
		result := M{"runtime": "go", "version": version, "code_revision": revision, "workspace": w, "archive_available": exists(filepath.Join(root, "profile.json"))}
		if exists(filepath.Join(root, "profile.json")) {
			result["archive"] = archiveCounts(root)
		}
		result["review_watch_diagnostics"] = glob(filepath.Join(root, "Runtime", "ReviewWatches", "*.error"))
		if err := attempt(func() { result["codex_executable"] = codexExecutable() }); err != nil {
			result["codex_error"] = err.Error()
		}
		if truth(o["probe"]) {
			c := newModelClient(defaultModel, 45*time.Second)
			defer c.close()
			if err := attempt(func() { c.connect(context.Background()) }); err != nil {
				result["translation_error"] = err.Error()
			} else {
				result["translation"] = M{"status": "ready", "auth": "chatgpt", "model": defaultModel, "effort": "low"}
			}
		}
		return result
	}
	if cmd == "open" {
		ensureWorkspace(w)
		base := str(o["service-url"])
		if base == "" {
			base = str(serviceStart(root, str(o["root"]) == "")["url"])
		} else {
			checkService(base, root, true)
		}
		return M{"url": strings.TrimRight(base, "/") + "/#" + textOr(o["page"], "overview"), "page_display": "not_verified"}
	}
	if cmd == "live" {
		action := "status"
		if len(commands) > 1 {
			action = commands[1]
		}
		if action == "probe" {
			c := newModelClient(defaultModel, 45*time.Second)
			defer c.close()
			c.connect(context.Background())
			return M{"model": defaultModel, "effort": "low", "auth": "chatgpt", "ephemeral": true}
		}
		require(exists(filepath.Join(root, "profile.json")), "学习档案不可用，未创建空替代。")
		l := openLive(root)
		defer l.close()
		id := str(o["run"])
		switch action {
		case "start":
			if source == "" {
				source = findSource(thread)
			}
			s := l.bind(thread, source, textOr(o["model"], defaultModel), truth(o["demo"]))
			return merge(pick(s, "thread_id", "voice_id"), M{"status": "bound", "run_id": s["id"]})
		case "stop":
			s := l.run(id)
			require(s != nil, "没有这个绑定。")
			desired := "drain"
			if terminal(s["status"]) {
				desired = "stopped"
			}
			l.patch(id, M{"desired": desired})
			return M{"status": desired, "run_id": id}
		case "resume":
			s := l.active()
			require(s != nil && s["id"] == id, "只能恢复当前明确绑定。")
			require(sourceIdentity(str(s["source"])) == s["thread_id"], "源文件身份已改变。")
			l.patch(id, M{"status": "starting", "error": nil, "translation_error": nil, "translation_retry": true, "ready": false, "desired": "running", "last_activity_epoch": epoch(), "created_epoch": epoch()})
			return M{"status": "resume_requested", "run_id": id}
		case "disable":
			if s := l.active(); s != nil {
				l.patch(str(s["id"]), M{"desired": "drain"})
			}
			l.setMeta("enabled", "false")
			return M{"status": "disabled"}
		case "status":
			return l.view(o)
		}
		panic("Unknown live command")
	}
	if cmd == "review-begin" && !truth(o["manual"]) {
		return enqueueReview(root, thread, voice, source, truth(o["retry"]))
	}
	if cmd == "review-context" || cmd == "review-begin" {
		state := buildState(root)
		matches := matchingRecords(state, thread, voice)
		records := A{}
		for _, v := range matches {
			r, _ := readRecord(root, obj(v))
			records = append(records, r)
		}
		catalog := A{}
		for _, v := range reverse(arr(state["expressions"])) {
			e := obj(v)
			q := strings.ToLower(str(o["query"]))
			if q == "" || strings.Contains(strings.ToLower(compact(e)), q) {
				catalog = append(catalog, pick(e, "id", "english", "chinese"))
			}
		}
		result := M{"date": day, "source_ids": voiceSources(thread, voice), "archive_route": reviewRoute(thread, voice), "existing_records": records, "expression_catalog": head(catalog, 60), "concept_catalog": state["concepts"], "finish_contract": contracts["finish_contract"]}
		if truth(o["with-transcript"]) {
			if source == "" {
				source = findSource(thread)
			}
			result["transcript"] = merge(snapshotVoice(source, thread, voice), M{"status": "observed_closed", "coverage": "available_unique_segments"})
		}
		return result
	}
	if cmd == "resume" {
		ensureWorkspace(w)
		var scene M
		if str(o["scene"]) != "" {
			scene = obj(readJSON(str(o["scene"])))
		}
		result := transitionContext(resumeContext(root, day, str(o["phase"]), scene), str(o["event"]))
		result["workspace"] = w
		if truth(o["with-project"]) && str(w["project_page"]) != "" {
			result["project_context"] = string(readFile(str(w["project_page"])))
		}
		return result
	}
	if cmd == "validate" {
		return validateArchive(root)
	}
	if cmd == "storage" {
		require(len(commands) > 1, "storage action required")
		action := commands[1]
		file, dest := str(o["file"]), str(o["destination"])
		if dest == "" {
			dest = str(o["data-root"])
		}
		switch action {
		case "show":
			return w
		case "backup":
			require(file != "" && !exists(file), "Provide a new backup file; existing files are preserved")
			blob, manifest := backupBytes(root, str(w["project_page"]), truth(o["include-live"]))
			atomicWrite(file, blob)
			return manifest
		case "inspect":
			return inspectBackup(readFile(file))
		case "restore":
			return restoreBackup(readFile(file), dest, true)
		case "adopt":
			return adoptArchive(dest)
		case "move", "configure":
			target := checkRoot(dest)
			if absolute(root) == target {
				return w
			}
			assertIdle(root)
			if exists(filepath.Join(root, "profile.json")) {
				require(action == "move" || truth(o["copy-existing"]), "Existing data found; use --copy-existing to preserve it")
				require(!within(root, target) && !within(target, root), "Source and target cannot contain one another")
				blob, _ := backupBytes(root, textOr(o["project-page"], str(w["project_page"])), true)
				return restoreBackup(blob, target, true)
			}
			require(str(w["mode"]) != "configured", "Configured archive missing; restore it instead of replacing it")
			require(emptyDir(target), "Destination is not empty")
			withLock(filepath.Join(target, ".write.lock"), func() { initialize(target); rebuild(target) })
			return saveConfiguration(target, str(o["project-page"]))
		}
		panic("Unknown storage action")
	}
	if cmd == "recover-voice" {
		return recoverCaptions(root, thread, voice, source, textOr(o["model"], defaultModel), truth(o["refresh-translations"]))
	}
	var result M
	withLock(filepath.Join(root, ".write.lock"), func() {
		initialize(root)
		input := func() M { require(str(o["input"]) != "", "--input required"); return obj(readJSON(str(o["input"]))) }
		switch cmd {
		case "init", "migrate", "rebuild", "render":
			rebuild(root)
			result = validateArchive(root)
			if cmd == "init" && str(o["root"]) == "" && str(o["vault"]) == "" {
				saveConfiguration(root, str(w["project_page"]))
			}
		case "add-session":
			result = commitRecord(root, input())
			if truth(o["check"]) {
				result["validation"] = validateArchive(root)
			}
		case "finish-review":
			result = finishReview(root, reconcileReview(input(), str(obj(readJSON(filepath.Join(root, "profile.json")))["help_language"])), thread, voice, source)
		case "set-preferences":
			changes := input()
			checkStrings(changes["source_ids"], "source_ids")
			require(len(arr(changes["source_ids"])) > 0, "Preference change needs a real user decision source")
			p := filepath.Join(root, "profile.json")
			if expected := str(o["expected-profile-sha256"]); expected != "" {
				require(hash(readFile(p)) == expected, "Preferences changed; reread and merge the current decision")
			}
			for k := range changes {
				require(profileDefault()[k] != nil, "Unknown preference field")
			}
			profile := merge(obj(readJSON(p)), changes)
			validateProfile(profile)
			writeJSON(p, profile)
			rebuild(root)
			result = M{"status": "preferences_saved"}
		case "checkpoint":
			d := input()
			validatePayload(d, true)
			require(!exists(filepath.Join(root, "Sessions", str(d["id"])+".md")), "Session already committed")
			p := filepath.Join(root, "Pending", str(d["id"])+".json")
			if exists(p) {
				require(textOr(obj(readJSON(p))["end_status"], "ended") != "ended", "Ended checkpoint cannot be replaced")
			}
			writeJSON(p, d)
			result = M{"status": "checkpointed", "session": d["id"]}
		case "recover":
			rows := A{}
			for _, p := range glob(filepath.Join(root, "Pending", "*.json")) {
				d := obj(readJSON(p))
				validatePayload(d, true)
				require(str(d["id"])+".json" == filepath.Base(p), "Pending filename mismatch")
				if textOr(d["end_status"], "ended") == "ended" {
					rows = append(rows, commitRecord(root, d))
				} else {
					rows = append(rows, M{"status": "needs_session_context", "session": d["id"]})
				}
			}
			rebuild(root)
			result = M{"recovered": rows}
		case "add-evidence":
			d := input()
			require(strings.HasPrefix(str(d["id"]), "EVD-") && regexpEvidenceID(str(d["id"])), "Invalid evidence ID")
			shortText(d["reason"], "Evidence reason", 10000)
			collectProgress(root, buildState(root), d)
			p := filepath.Join(root, "Evidence", str(d["id"])+".md")
			status := "saved"
			if exists(p) {
				require(equal(extract(p, "speaking-evidence-v1"), d), "Conflicting evidence file")
				status = "already_saved"
			} else {
				atomicWrite(p, []byte(recordFrontmatter(d)+"# 知识点学习记录 / Concept practice record\n\n"+str(d["reason"])+"\n\n"+block("speaking-evidence-v1", d)))
			}
			rebuild(root)
			result = M{"status": status, "evidence": d["id"]}
		case "export":
			output := absolute(str(o["output"]))
			require(!within(output, root), "Export destination must be outside the canonical learning directory")
			state := buildState(root)
			require(emptyDir(output), "Export destination must be empty")
			atomicWrite(filepath.Join(output, "dashboard.html"), readFile(filepath.Join(root, "dashboard.html")))
			for _, v := range arr(state["sessions"]) {
				name := str(obj(v)["id"]) + ".md"
				atomicWrite(filepath.Join(output, "Sessions", name), readFile(filepath.Join(root, "Sessions", name)))
			}
			result = M{"status": "exported", "path": filepath.Join(output, "dashboard.html")}
		default:
			panic(fmt.Errorf("Unknown command: %s", cmd))
		}
	})
	return merge(result, recoveryBackup(root))
}
func regexpEvidenceID(id string) bool {
	if len(id) != 16 || !strings.HasPrefix(id, "EVD-") {
		return false
	}
	return expressionID.MatchString("EXP-" + id[4:])
}
func main() {
	var result any
	err := attempt(func() { result = runCLI(os.Args[1:]) })
	if err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
	if result != nil {
		fmt.Print(string(encode(result)))
		if obj(result)["ok"] == false {
			os.Exit(1)
		}
	}
}
