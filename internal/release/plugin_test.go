package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestPluginShipsVerifiedProgramsWithoutPrivateOrDeveloperRuntime(t *testing.T) {
	root := t.TempDir()
	put := func(name, text string) {
		p := filepath.Join(root, filepath.FromSlash(name))
		must(os.MkdirAll(filepath.Dir(p), 0755))
		must(os.WriteFile(p, []byte(text), 0644))
	}
	put(".codex-plugin/plugin.json", `{"name":"english-speaking-coach","version":"0.2.9","skills":"./skills/"}`)
	for _, name := range []string{"SKILL.md", "runtime-version.txt", "README.md", "README.en.md", "LICENSE", "scripts/coach", "scripts/coach.ps1", "agents/openai.yaml", "references/runtime-installation.md", "assets/library/speech.js"} {
		put(name, "fixture")
	}
	for _, name := range []string{"data/profile.json", "Live/companion.sqlite3", ".env", "scripts/legacy.py", "node/experiment.mjs", "bin/old-program", "assets/.DS_Store"} {
		put(name, "MUST_NOT_SHIP")
	}
	binary := []byte("verified fixture program")
	programs := map[string][]byte{"english-coach_v0.2.9_darwin_arm64": binary, "english-coach_v0.2.9_darwin_arm64.sha256": []byte(digest(binary) + "\n")}
	blob := buildPlugin(root, "v0.2.9", "revision-fixture", programs)
	z, err := zip.NewReader(bytes.NewReader(blob), int64(len(blob)))
	must(err)
	files := map[string][]byte{}
	for _, f := range z.File {
		r, err := f.Open()
		must(err)
		b, err := io.ReadAll(r)
		must(err)
		r.Close()
		if bytes.Contains(b, []byte("MUST_NOT_SHIP")) {
			t.Fatalf("Private/runtime input leaked: %s", f.Name)
		}
		files[strings.TrimPrefix(f.Name, "english-speaking-coach/")] = b
		if strings.HasSuffix(f.Name, "_darwin_arm64") && f.Mode()&0111 == 0 {
			t.Fatal("Bundled Unix program is not executable")
		}
	}
	var receipt struct {
		Files            map[string]string
		Version, Runtime string
	}
	must(json.Unmarshal(files["package-manifest.json"], &receipt))
	if receipt.Version != "v0.2.9" || receipt.Runtime != "go" || len(receipt.Files) != len(files)-1 {
		t.Fatal("Incomplete package receipt")
	}
	for name, expected := range receipt.Files {
		if digest(files[name]) != expected {
			t.Fatalf("Checksum mismatch: %s", name)
		}
	}
	base := "skills/english-speaking-coach/bin/english-coach_v0.2.9_darwin_arm64"
	if string(files[base+".sha256"]) != digest(files[base])+"\n" {
		t.Fatal("Offline launcher lacks a valid executable receipt")
	}
}
