package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func textLog(t *testing.T, payload M) string {
	t.Helper()
	p := filepath.Join(t.TempDir(), "text-task.jsonl")
	atomicWrite(p, nil)
	appendLog(p, M{"type": "session_meta", "payload": payload})
	appendLog(p, M{"type": "world_state", "payload": M{"state": M{"realtime": M{"active": false}}}})
	return p
}

func TestPrepareRequiresActiveVoiceBeforeAnySideEffects(t *testing.T) {
	for _, kind := range []string{"text", "ended", "host-inactive", "host-active-without-identity", "wrong-task", "missing", "corrupt"} {
		t.Run(kind, func(t *testing.T) {
			t.Setenv("CODEX_HOME", t.TempDir())
			root := filepath.Join(t.TempDir(), "not-created")
			source := textLog(t, M{"session_id": testThread})
			want := "waiting_voice"
			switch kind {
			case "ended":
				source = voiceLog(t, true)
			case "host-inactive":
				source = voiceLog(t, false)
				appendLog(source, M{"type": "world_state", "payload": M{"state": M{"realtime": M{"active": false}}}})
			case "host-active-without-identity":
				appendLog(source, M{"type": "world_state", "payload": M{"state": M{"realtime": M{"active": true}}}})
			case "wrong-task":
				source = textLog(t, M{"id": testVoice})
				want = "source_unavailable"
			case "missing":
				source += ".absent"
				want = "source_unavailable"
			case "corrupt":
				appendLog(source, M{"payload": "complete row without type"})
				want = "source_unavailable"
			}
			// An unusable service URL must never even be visited on this path.
			result := preparePractice(M{"thread-id": testThread, "source": source, "root": root, "auto-scene": true, "opening": true, "service-url": "http://invalid.invalid"})
			if result["status"] != want || truth(result["conversation_may_start"]) || truth(result["companion_ready"]) || result["url"] != nil || result["binding"] != nil {
				t.Fatal(result)
			}
			if exists(root) || exists(configPath()) || exists(serviceReceipt()) {
				t.Fatal("Preparation mutated storage or service state for an unverified Voice")
			}
		})
	}
}

func TestSourceIdentityAcceptsHostAliasButRejectsConflict(t *testing.T) {
	for _, payload := range []M{{"id": testThread}, {"session_id": testThread}, {"id": testThread, "session_id": testThread}} {
		if got := sourceIdentity(textLog(t, payload)); got != testThread {
			t.Fatal(got)
		}
	}
	source := textLog(t, M{"id": testThread, "session_id": testVoice})
	reject(t, func() { sourceIdentity(source) })
}

func TestUnboundPreparePreservesExistingArchiveAndPractice(t *testing.T) {
	root := testRoot(t)
	l := openLive(root)
	defer l.close()
	active := l.bind(testThread, voiceLog(t, false), defaultModel, true)
	profile := readFile(filepath.Join(root, "profile.json"))
	for _, enabled := range []bool{true, false} {
		l.setMeta("enabled", fmt.Sprint(enabled))
		source := textLog(t, M{"id": testVoice})
		result := preparePractice(M{"thread-id": testVoice, "source": source, "root": root, "auto-scene": true})
		if result["status"] != "waiting_voice" || l.active()["id"] != active["id"] || len(query(l.db, "SELECT * FROM runs")) != 1 {
			t.Fatal("Unbound preparation replaced the active practice", result)
		}
		if len(glob(filepath.Join(root, "Runtime", "ReviewWatches", "*.json"))) != 0 || exists(filepath.Join(root, "Runtime", "scene-history.json")) || !bytes.Equal(profile, readFile(filepath.Join(root, "profile.json"))) {
			t.Fatal("Text task wrote a watcher, scene history or preferences")
		}
		reject(t, func() { l.bind(testVoice, source, defaultModel, true) })
	}
}

func TestActiveVoicePrepareReusesBindingAndSeparatesReadiness(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root, source := testRoot(t), voiceLog(t, false)
	s := newServer(root, false)
	h := httptest.NewServer(s)
	defer h.Close()
	s.port = h.Listener.Addr().(*net.TCPAddr).Port
	args := M{"root": root, "thread-id": testThread, "source": source, "auto-scene": true, "opening": true, "service-url": h.URL}
	first := preparePractice(args)
	if obj(first["policy"])["missing_expression_help"] != "immediate_before_content" || str(first["turn_guidance"]) == "" || first["written_scene"] != nil {
		t.Fatal("Compact preparation lost teaching policy or returned a second scene script", first)
	}
	if !truth(first["conversation_may_start"]) || truth(first["companion_ready"]) || obj(first["binding"])["voice_id"] != testVoice || str(first["review_url"]) == "" {
		t.Fatal(first)
	}
	l := openLive(root)
	defer l.close()
	l.patch(str(l.active()["id"]), M{"ready": true})
	connected := preparePractice(args)
	if connected["status"] != "backend_ready" || truth(connected["companion_ready"]) {
		t.Fatal("Model connection alone claimed live captions", connected)
	}
	l.readTail(l.active())
	ready := preparePractice(args)
	if !truth(ready["companion_ready"]) || !equal(first["binding"], ready["binding"]) || !equal(first["scene"], ready["scene"]) || len(sceneHistory(root)) != 1 {
		t.Fatal("Exact retry changed the scene or binding", ready)
	}
	if integer(l.view(M{})["total"]) != 3 || len(query(l.db, "SELECT * FROM runs")) != 1 {
		t.Fatal("Source segments or binding identity lost")
	}
	// Reusing a configured local supervisor never creates a second manager.
	if exists(serviceReceipt()) {
		t.Fatal("Prepared a competing service manager")
	}
}

func TestTailerKeepsConcreteDiagnosticsAndValidCaptions(t *testing.T) {
	root, source := testRoot(t), voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	s := l.bind(testThread, source, defaultModel, true)
	l.readTail(s)
	f, err := os.OpenFile(source, os.O_APPEND|os.O_WRONLY, 0600)
	must(err)
	_, err = f.WriteString("{broken complete JSON}\n")
	must(err)
	must(f.Close())
	var diagnostic bytes.Buffer
	previous := log.Writer()
	log.SetOutput(&diagnostic)
	defer log.SetOutput(previous)
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { defer close(done); runTailer(ctx, root) }()
	deadline := time.Now().Add(3 * time.Second)
	for l.active()["status"] != "error" && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	cancel()
	<-done
	state := obj(l.view(M{})["state"])
	if state["status"] != "error" || !strings.Contains(str(state["error"]), "字节") || integer(l.view(M{})["total"]) != 3 {
		t.Fatal(state)
	}
	if !strings.Contains(diagnostic.String(), str(s["id"])) || !strings.Contains(diagnostic.String(), str(state["error"])) || strings.Contains(diagnostic.String(), "I want two bread") {
		t.Fatal("Missing diagnostic or unexpected raw learner transcript in log", diagnostic.String())
	}
}

func TestDisabledCaptionsKeepExactVoiceReviewWithoutLiveBinding(t *testing.T) {
	t.Setenv("CODEX_HOME", t.TempDir())
	root, source := testRoot(t), voiceLog(t, false)
	l := openLive(root)
	defer l.close()
	l.setMeta("enabled", "false")
	_, server := testHTTP(t, root)
	r := preparePractice(M{"root": root, "source": source, "thread-id": testThread, "auto-scene": true, "opening": true, "service-url": server.URL})
	if r["status"] != "conversation_only" || !strings.HasSuffix(str(r["url"]), "/#overview") || !strings.Contains(str(r["review_url"]), testVoice) || truth(r["companion_ready"]) || l.active() != nil {
		t.Fatal(r)
	}
	if reviewStatus(root, testThread, testVoice)["status"] != "practicing" {
		t.Fatal("Caption preference disabled the exact Voice review")
	}
}

func TestCopiedLauncherRepairsVerifiedModeAndRejectsChangedBytes(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("POSIX shell launcher; Windows uses PowerShell")
	}
	root := t.TempDir()
	launcher := filepath.Join(root, "scripts", "coach")
	mkdir(filepath.Dir(launcher))
	atomicWrite(launcher, readFile(filepath.Join("scripts", "coach")))
	must(os.Chmod(launcher, 0644))
	atomicWrite(filepath.Join(root, "runtime-version.txt"), []byte("v0.0.1\n"))
	binary := filepath.Join(root, "bin", "english-coach_v0.0.1_"+runtime.GOOS+"_"+runtime.GOARCH)
	mkdir(filepath.Dir(binary))
	program := []byte("#!/bin/sh\nprintf 'verified runtime: %s\\n' \"$1\"\n")
	atomicWrite(binary, program)
	must(os.Chmod(binary, 0644))
	atomicWrite(binary+".sha256", []byte(hash(program)+"\n"))
	out, err := exec.Command("sh", launcher, "version").CombinedOutput()
	if err != nil || !strings.Contains(string(out), "verified runtime: version") {
		t.Fatal(err, string(out))
	}
	info, err := os.Stat(binary)
	must(err)
	if info.Mode()&0111 == 0 {
		t.Fatal("Verified cache was not made executable")
	}
	atomicWrite(binary, []byte("#!/bin/sh\necho UNVERIFIED_EXECUTED\n"))
	out, err = exec.Command("sh", launcher, "version").CombinedOutput()
	if err == nil || strings.Contains(string(out), "UNVERIFIED_EXECUTED") {
		t.Fatal("Changed cached bytes executed", string(out))
	}
}

func TestRealMaintenanceDoesNotBecomeWrittenLanguageHelp(t *testing.T) {
	if os.Getenv("ENGLISH_COACH_REAL_MAINTENANCE_TEST") != "1" {
		t.Skip("Explicit isolated account integration opt-in required")
	}
	c := newModelClient(defaultModel, 45*time.Second)
	defer c.close()
	c.freshTurns = true
	c.instructions = "Return only the requested JSON teaching object. Do not translate transcripts or use tools. " + str(contracts["teaching_instructions"])
	schema := json.RawMessage(`{"type":"object","properties":{"teaching":` + string(rawContracts["teaching_schema"]) + `},"required":["teaching"],"additionalProperties":false}`)
	conversation := A{M{"id": "a1", "role": "assistant", "text": "Welcome to the gift shop. What are you looking for?"}}
	for i, item := range []struct{ text, kind string }{
		{"检查双语网页为什么没有翻译，我现在要排查问题。", "none"},
		{"换成 JS 会不会简单一点？", "none"},
		{"好了，继续买礼物的练习。围巾这个词怎么说？", "help"},
	} {
		conversation = append(conversation, M{"id": fmt.Sprintf("u%d", i), "role": "user", "text": item.text})
		payload := M{"teaching_context": M{"conversation": conversation, "scene": M{"setting": "A gift shop"}, "profile": M{"correction": "in_character", "input_support": "short_turns"}}}
		answer := c.generate(context.Background(), payload, schema, nil)
		hint := obj(answer["teaching"])
		if hint["kind"] != item.kind || item.kind == "none" && (str(hint["english"]) != "" || str(hint["next_cue"]) != "") {
			t.Fatalf("case %d: %v", i, hint)
		}
		if item.kind == "help" {
			word := strings.Trim(strings.ToLower(str(hint["english"])), " .!\"'“”")
			if validateHint(hint, conversation) == nil || (word != "scarf" && word != "a scarf") {
				t.Fatal("Word lookup invented a scene intention instead of supplying the word", hint)
			}
		}
		t.Logf("case %d: %s; response=%v", i, item.kind, hint)
	}
}
