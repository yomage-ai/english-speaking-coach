package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// One release bundle includes the skill and verified programs. Installing it
// never requires a compiler, a language runtime or a first-use npm download.
func buildPlugin(root, version, revision string, programs map[string][]byte) []byte {
	manifestBytes := read(filepath.Join(root, ".codex-plugin", "plugin.json"))
	var manifest map[string]any
	must(json.Unmarshal(manifestBytes, &manifest))
	if manifest["name"] != "english-speaking-coach" || manifest["version"] != strings.TrimPrefix(version, "v") || manifest["skills"] != "./skills/" {
		panic("Plugin identity/version/layout does not match the release")
	}
	prefix := "english-speaking-coach/"
	skill := prefix + "skills/english-speaking-coach/"
	payload := map[string][]byte{prefix + ".codex-plugin/plugin.json": manifestBytes}
	// Explicit distribution roots exclude private data, caches and experiments.
	for _, name := range []string{"SKILL.md", "runtime-version.txt", "README.md", "README.en.md", "LICENSE"} {
		payload[skill+name] = read(filepath.Join(root, name))
	}
	for _, name := range []string{"README.md", "README.en.md", "LICENSE"} {
		payload[prefix+name] = read(filepath.Join(root, name))
	}
	for _, dir := range []string{"agents", "references", "assets"} {
		must(filepath.WalkDir(filepath.Join(root, dir), func(p string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if d.IsDir() {
				return nil
			}
			if d.Type()&os.ModeSymlink != 0 {
				return fmt.Errorf("No symlinks in plugin: %s", p)
			}
			if strings.HasPrefix(d.Name(), ".") {
				return nil
			}
			rel, err := filepath.Rel(root, p)
			if err != nil {
				return err
			}
			payload[skill+filepath.ToSlash(rel)] = read(p)
			return nil
		}))
	}
	// Legacy Python is a developer oracle, not an installed dependency.
	for _, name := range []string{"coach", "coach.ps1"} {
		payload[skill+"scripts/"+name] = read(filepath.Join(root, "scripts", name))
	}
	for name, b := range programs {
		payload[skill+"bin/"+name] = b
	}
	files := map[string]string{}
	for name, b := range payload {
		files[strings.TrimPrefix(name, prefix)] = digest(b)
	}
	receipt, err := json.MarshalIndent(map[string]any{"version": version, "code_revision": revision, "runtime": "go", "files": files}, "", "  ")
	must(err)
	payload[prefix+"package-manifest.json"] = append(receipt, '\n')
	names := make([]string, 0, len(payload))
	for name := range payload {
		names = append(names, name)
	}
	sort.Strings(names)
	var out bytes.Buffer
	z := zip.NewWriter(&out)
	for _, name := range names {
		h := &zip.FileHeader{Name: name, Method: zip.Deflate}
		h.SetMode(0644)
		if strings.HasSuffix(name, "/scripts/coach") || (strings.Contains(name, "/bin/") && !strings.Contains(filepath.Base(name), ".")) {
			h.SetMode(0755)
		}
		// Versioned Unix program names contain dots; distinguish their metadata.
		if strings.Contains(name, "/bin/") && (strings.HasSuffix(name, "_arm64") || strings.HasSuffix(name, "_amd64")) {
			h.SetMode(0755)
		}
		f, err := z.CreateHeader(h)
		must(err)
		_, err = f.Write(payload[name])
		must(err)
	}
	must(z.Close())
	return out.Bytes()
}
