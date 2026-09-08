package main

import (
	"crypto/rand"
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"github.com/gofrs/flock"
	"github.com/google/uuid"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"time"
)

// Records deliberately retain unknown fields: Markdown remains the portable authority.
type M = map[string]any
type A = []any

//go:embed assets/library/* assets/runtime/*
var bundled embed.FS
var version = "dev"
var revision = "dev"
var contracts M
var rawContracts map[string]json.RawMessage
var speakingTemplates M

func init() {
	must(json.Unmarshal(readAsset("assets/runtime/contracts.json"), &contracts))
	must(json.Unmarshal(readAsset("assets/runtime/contracts.json"), &rawContracts))
	must(json.Unmarshal(readAsset("assets/runtime/speaking.json"), &speakingTemplates))
}
func readAsset(p string) []byte { b, e := bundled.ReadFile(p); must(e); return b }

// A failed contract unwinds to an explicit command/request/worker boundary. Defers
// release locks and transactions; recoverError never treats a failure as success.
func must(e error) {
	if e != nil {
		panic(e)
	}
}
func require(ok bool, message string) {
	if !ok {
		panic(fmt.Errorf("%s", message))
	}
}
func recoverError(err *error) {
	if v := recover(); v != nil {
		if e, ok := v.(error); ok {
			*err = e
		} else {
			*err = fmt.Errorf("%v", v)
		}
	}
}
func attempt(f func()) (err error) { defer recoverError(&err); f(); return }
func obj(v any) M {
	if x, ok := v.(map[string]any); ok && x != nil {
		return x
	}
	return M{}
}
func arr(v any) A {
	if x, ok := v.([]any); ok && x != nil {
		return x
	}
	return A{}
}
func str(v any) string { x, _ := v.(string); return x }
func num(v any) float64 {
	switch x := v.(type) {
	case float64:
		return x
	case int:
		return float64(x)
	case int64:
		return float64(x)
	case json.Number:
		n, _ := x.Float64()
		return n
	}
	return 0
}
func integer(v any) int { return int(num(v)) }
func truth(v any) bool  { x, _ := v.(bool); return x }
func textOr(v any, d string) string {
	if s := str(v); s != "" {
		return s
	}
	return d
}
func get(m M, k string, d any) any {
	v, ok := m[k]
	if ok {
		return v
	}
	return d
}
func clone(v any) any { var out any; must(json.Unmarshal(encode(v), &out)); return out }
func copyM(v any) M   { return obj(clone(v)) }
func merge(ms ...M) M {
	out := M{}
	for _, m := range ms {
		for k, v := range m {
			out[k] = v
		}
	}
	return out
}
func pick(m M, keys ...string) M {
	out := M{}
	for _, k := range keys {
		if v, ok := m[k]; ok {
			out[k] = v
		}
	}
	return out
}
func omit(m M, keys ...string) M {
	out := merge(m)
	for _, k := range keys {
		delete(out, k)
	}
	return out
}
func encode(v any) []byte      { b, e := json.MarshalIndent(v, "", "  "); must(e); return append(b, '\n') }
func compact(v any) string     { b, e := json.Marshal(v); must(e); return string(b) }
func readFile(p string) []byte { b, e := os.ReadFile(p); must(e); return b }
func readJSON(p string) any    { var v any; must(json.Unmarshal(readFile(p), &v)); return v }
func maybeJSON(p string, d any) any {
	if !exists(p) {
		return clone(d)
	}
	return readJSON(p)
}
func exists(p string) bool { _, e := os.Stat(p); return e == nil }
func isDir(p string) bool  { s, e := os.Stat(p); return e == nil && s.IsDir() }
func mkdir(p string)       { must(os.MkdirAll(p, 0700)) }
func atomicWrite(p string, b []byte) {
	mkdir(filepath.Dir(p))
	f, e := os.CreateTemp(filepath.Dir(p), "."+filepath.Base(p)+"-")
	must(e)
	tmp := f.Name()
	defer os.Remove(tmp)
	defer f.Close()
	_, e = f.Write(b)
	must(e)
	must(f.Sync())
	must(f.Close())
	must(os.Rename(tmp, p))
}
func writeJSON(p string, v any) { atomicWrite(p, encode(v)) }
func hash(b []byte) string      { s := sha256.Sum256(b); return hex.EncodeToString(s[:]) }
func token() string {
	b := make([]byte, 32)
	_, e := rand.Read(b)
	must(e)
	return hex.EncodeToString(b)
}
func absolute(p string) string {
	require(p != "", "A directory path is required")
	if p == "~" {
		p = homeDir()
	} else if strings.HasPrefix(p, "~/") || strings.HasPrefix(p, "~\\") {
		p = filepath.Join(homeDir(), p[2:])
	}
	a, e := filepath.Abs(p)
	must(e)
	if r, e := filepath.EvalSymlinks(a); e == nil {
		return r
	}
	// Resolve existing parents too: a new directory below a symlink must not
	// evade the Skill/data separation or source/target containment checks.
	suffix := []string{}
	parent := filepath.Clean(a)
	for {
		if r, e := filepath.EvalSymlinks(parent); e == nil {
			for i := len(suffix) - 1; i >= 0; i-- {
				r = filepath.Join(r, suffix[i])
			}
			return r
		}
		next := filepath.Dir(parent)
		if next == parent {
			break
		}
		suffix = append(suffix, filepath.Base(parent))
		parent = next
	}
	return filepath.Clean(a)
}
func homeDir() string { h, e := os.UserHomeDir(); must(e); return h }
func codexHome() string {
	return absolute(textOr(os.Getenv("CODEX_HOME"), filepath.Join(homeDir(), ".codex")))
}
func configPath() string {
	return filepath.Join(codexHome(), "english-speaking-coach", "workspace.json")
}
func defaultRoot() string { return filepath.Join(filepath.Dir(configPath()), "data") }
func skillRoot() string {
	if p := os.Getenv("ENGLISH_COACH_SKILL_ROOT"); p != "" {
		return absolute(p)
	}
	exe, e := os.Executable()
	must(e)
	p := filepath.Dir(exe)
	if filepath.Base(p) == "bin" {
		p = filepath.Dir(p)
	}
	return p
}
func within(p, root string) bool {
	r, e := filepath.Rel(root, p)
	return e == nil && r != ".." && !strings.HasPrefix(r, ".."+string(filepath.Separator))
}
func today() string            { return time.Now().Format("2006-01-02") }
func now() string              { return time.Now().UTC().Format(time.RFC3339Nano) }
func epoch() float64           { return float64(time.Now().UnixMilli()) / 1000 }
func stamp(s string) time.Time { t, e := time.Parse(time.RFC3339Nano, s); must(e); return t }
func checkDate(v any) {
	s, ok := v.(string)
	require(ok, "Date must be YYYY-MM-DD")
	t, e := time.Parse("2006-01-02", s)
	must(e)
	require(t.Format("2006-01-02") == s, "Date must be YYYY-MM-DD")
}
func order(m M) string {
	t := ""
	if s := str(m["practiced_at"]); s != "" {
		t = stamp(s).UTC().Format("2006-01-02T15:04:05.000000000Z")
	}
	return str(m["date"]) + "/" + t + "/" + textOr(m["id"], str(m["session"]))
}
func sortRows(a A, key func(M) string, reverse bool) {
	sort.SliceStable(a, func(i, j int) bool {
		if reverse {
			return key(obj(a[i])) > key(obj(a[j]))
		}
		return key(obj(a[i])) < key(obj(a[j]))
	})
}
func stringsA(ss ...string) A {
	a := A{}
	for _, s := range ss {
		a = append(a, s)
	}
	return a
}
func has(a any, v any) bool {
	for _, x := range arr(a) {
		if reflect.DeepEqual(x, v) {
			return true
		}
	}
	return false
}
func unique(a A) A {
	out := A{}
	seen := map[string]bool{}
	for _, v := range a {
		k := compact(v)
		if !seen[k] {
			seen[k] = true
			out = append(out, v)
		}
	}
	return out
}
func reverse(a A) A {
	out := append(A{}, a...)
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return out
}
func tail(a A, n int) A {
	if len(a) > n {
		return a[len(a)-n:]
	}
	return a
}
func head(a A, n int) A {
	if len(a) > n {
		return a[:n]
	}
	return a
}
func equal(a, b any) bool { return compact(a) == compact(b) }
func checkStrings(v any, label string) {
	_, ok := v.([]any)
	require(ok, label+" must be a list")
	for _, x := range arr(v) {
		require(strings.TrimSpace(str(x)) != "", label+" needs nonempty strings")
	}
}
func glob(p string) []string { r, e := filepath.Glob(p); must(e); sort.Strings(r); return r }
func emptyDir(p string) bool {
	if !exists(p) {
		return true
	}
	r, e := os.ReadDir(p)
	must(e)
	return len(r) == 0
}
func withLock(p string, f func()) {
	mkdir(filepath.Dir(p))
	lock := flock.New(p)
	must(lock.Lock())
	defer lock.Unlock()
	f()
}
func tryLock(p string) (*flock.Flock, bool) {
	mkdir(filepath.Dir(p))
	l := flock.New(p)
	ok, e := l.TryLock()
	must(e)
	return l, ok
}
func voiceSources(thread, voice string) A {
	t, e := uuid.Parse(thread)
	must(e)
	v, e := uuid.Parse(voice)
	must(e)
	return stringsA("codex-thread:"+t.String(), "codex-voice:"+v.String())
}
func reviewRoute(thread, voice string) string {
	voiceSources(thread, voice)
	return "#review?thread=" + thread + "&voice=" + voice
}
func workspace(root string) M {
	if root != "" {
		return M{"data_root": absolute(root), "project_page": nil, "mode": "explicit", "config_path": configPath()}
	}
	if exists(configPath()) {
		c := obj(readJSON(configPath()))
		require(integer(c["schema_version"]) == 1 && filepath.IsAbs(str(c["data_root"])), "Invalid workspace configuration; no empty replacement created")
		return merge(c, M{"mode": "configured", "config_path": configPath()})
	}
	old := filepath.Join(skillRoot(), "data")
	if isDir(old) && !emptyDir(old) {
		return M{"data_root": old, "project_page": nil, "mode": "legacy-skill-data", "config_path": configPath()}
	}
	return M{"data_root": defaultRoot(), "project_page": nil, "mode": "user-data", "config_path": configPath()}
}
func assetFiles() fs.FS { f, e := fs.Sub(bundled, "assets/library"); must(e); return f }
