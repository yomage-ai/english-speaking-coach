// Developer release builder. The distributed program never invokes this tool.
package main

import (
	"archive/tar"
	"archive/zip"
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
)

func must(err error) {
	if err != nil {
		panic(err)
	}
}
func read(p string) []byte   { b, e := os.ReadFile(p); must(e); return b }
func digest(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func main() {
	out := flag.String("out", "dist", "Output directory")
	targets := flag.String("targets", "darwin/arm64,darwin/amd64,linux/amd64,linux/arm64,windows/amd64,windows/arm64", "OS/arch targets")
	onlyRev := flag.Bool("revision", false, "Print content revision only")
	flag.Parse()
	files := []string{"go.mod", "go.sum"}
	rootGo, e := filepath.Glob("*.go")
	must(e)
	for _, p := range rootGo {
		if !strings.HasSuffix(p, "_test.go") {
			files = append(files, p)
		}
	}
	must(filepath.WalkDir("assets", func(p string, d fs.DirEntry, e error) error {
		if e != nil {
			return e
		}
		if !d.IsDir() {
			files = append(files, p)
		}
		return nil
	}))
	sort.Strings(files)
	h := sha256.New()
	for _, p := range files {
		io.WriteString(h, filepath.ToSlash(p)+"\n")
		h.Write(read(p))
	}
	rev := hex.EncodeToString(h.Sum(nil))[:16]
	if *onlyRev {
		fmt.Println(rev)
		return
	}
	version := strings.TrimSpace(string(read("runtime-version.txt")))
	must(os.MkdirAll(*out, 0755))
	// Include dependency license texts with every distributed executable.
	modules, e := exec.Command("go", "list", "-m", "-json", "all").Output()
	must(e)
	dec := json.NewDecoder(bytes.NewReader(modules))
	var notices strings.Builder
	fmt.Fprintf(&notices, "===== Go runtime / LICENSE =====\n%s\n", read(filepath.Join(runtime.GOROOT(), "LICENSE")))
	for {
		var module struct{ Path, Version, Dir string }
		e := dec.Decode(&module)
		if e == io.EOF {
			break
		}
		must(e)
		if module.Dir == "" || module.Version == "" {
			continue
		}
		for _, pattern := range []string{"LICENSE", "LICENSE.*", "COPYING", "NOTICE"} {
			paths, e := filepath.Glob(filepath.Join(module.Dir, pattern))
			must(e)
			for _, p := range paths {
				info, e := os.Stat(p)
				must(e)
				if !info.Mode().IsRegular() {
					continue
				}
				fmt.Fprintf(&notices, "\n===== %s %s / %s =====\n%s\n", module.Path, module.Version, filepath.Base(p), read(p))
			}
		}
	}
	noticeBytes := []byte(notices.String())
	sums := []string{}
	manifest := map[string]any{"version": version, "code_revision": rev, "runtime": "go", "artifacts": []any{}}
	for _, target := range strings.Split(*targets, ",") {
		parts := strings.Split(target, "/")
		if len(parts) != 2 {
			panic("bad target")
		}
		osName, arch := parts[0], parts[1]
		binary := "english-coach"
		if osName == "windows" {
			binary += ".exe"
		}
		tmp, e := os.MkdirTemp("", "english-coach-build-")
		must(e)
		dest := filepath.Join(tmp, binary)
		cmd := exec.Command("go", "build", "-trimpath", "-ldflags", "-s -w -X main.version="+version+" -X main.revision="+rev, "-o", dest, ".")
		cmd.Env = append(os.Environ(), "CGO_ENABLED=0", "GOOS="+osName, "GOARCH="+arch)
		cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
		must(cmd.Run())
		name := fmt.Sprintf("english-coach_%s_%s_%s", version, osName, arch)
		var packed bytes.Buffer
		b := read(dest)
		if osName == "windows" {
			name += ".zip"
			z := zip.NewWriter(&packed)
			f, e := z.Create(binary)
			must(e)
			_, e = f.Write(b)
			must(e)
			for _, entry := range []struct {
				name string
				data []byte
			}{{"LICENSE", read("LICENSE")}, {"THIRD_PARTY_NOTICES.txt", noticeBytes}} {
				f, e := z.Create(entry.name)
				must(e)
				_, e = f.Write(entry.data)
				must(e)
			}
			must(z.Close())
		} else {
			name += ".tar.gz"
			gz := gzip.NewWriter(&packed)
			t := tar.NewWriter(gz)
			must(t.WriteHeader(&tar.Header{Name: binary, Mode: 0755, Size: int64(len(b))}))
			_, e = t.Write(b)
			must(e)
			for _, entry := range []struct {
				name string
				data []byte
			}{{"LICENSE", read("LICENSE")}, {"THIRD_PARTY_NOTICES.txt", noticeBytes}} {
				must(t.WriteHeader(&tar.Header{Name: entry.name, Mode: 0644, Size: int64(len(entry.data))}))
				_, e = t.Write(entry.data)
				must(e)
			}
			must(t.Close())
			must(gz.Close())
		}
		must(os.WriteFile(filepath.Join(*out, name), packed.Bytes(), 0644))
		sums = append(sums, digest(packed.Bytes())+"  "+name)
		manifest["artifacts"] = append(manifest["artifacts"].([]any), map[string]any{"name": name, "platform": target, "sha256": digest(packed.Bytes()), "binary_sha256": digest(b), "bytes": packed.Len()})
		must(os.RemoveAll(tmp))
		fmt.Println(name)
	}
	sort.Strings(sums)
	must(os.WriteFile(filepath.Join(*out, "SHA256SUMS"), []byte(strings.Join(sums, "\n")+"\n"), 0644))
	b, e := json.MarshalIndent(manifest, "", "  ")
	must(e)
	must(os.WriteFile(filepath.Join(*out, "manifest.json"), append(b, '\n'), 0644))
}
