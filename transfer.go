package main

import (
	"archive/zip"
	"bytes"
	"encoding/base64"
	"io"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"
)

const maxBackup = 256 * 1024 * 1024
const maxFiles = 20000

// Run after releasing the writer lock. Preserve the legacy automatic-backup
// scope; explicit external archives keep their existing backup policy.
func recoveryBackup(root string) M {
	if absolute(root) != absolute(defaultRoot()) && !within(root, skillRoot()) {
		return M{}
	}
	destination := filepath.Join(filepath.Dir(configPath()), "backups", "latest.zip")
	err := attempt(func() {
		withLock(filepath.Join(filepath.Dir(destination), ".backup.lock"), func() {
			blob, _ := backupBytes(root, "", false)
			atomicWrite(destination, blob)
		})
	})
	if err != nil {
		return M{"backup_warning": "学习原件已保存，但恢复备份未更新：" + err.Error()}
	}
	return M{"recovery_backup": destination}
}

func assertIdle(root string) {
	if exists(filepath.Join(root, "Live", "companion.sqlite3")) {
		l := openLive(root)
		defer l.close()
		for _, v := range query(l.db, "SELECT * FROM runs") {
			s := stateRow(obj(v))
			require(s["desired"] == "stopped" || terminal(s["status"]), "英语练习或字幕排空尚未结束，请稍后切换目录。")
		}
	}
	for _, v := range recentReviews(root) {
		j := obj(v)
		require(!truth(j["auto_review"]) || !has(activeReviews, j["status"]), "该目录还有未完成复盘，请先完成或处理错误。")
	}
}
func checkRoot(p string) string {
	require(filepath.IsAbs(p) || strings.HasPrefix(p, "~/"), "请填写专用学习目录的绝对路径。")
	r := absolute(p)
	require(r != filepath.VolumeName(r)+string(filepath.Separator) && r != homeDir() && !within(r, skillRoot()), "请选择 Skill 外的专用学习目录，不能使用系统或主目录。")
	return r
}
func archiveCounts(root string) M {
	require(exists(filepath.Join(root, "profile.json")) && exists(filepath.Join(root, "Archive", "legacy-v1.md")) && isDir(filepath.Join(root, "Sessions")), "目录不是完整学习档案：需要 profile.json、Sessions 和 Archive。")
	state := buildState(root)
	for _, p := range glob(filepath.Join(root, "Pending", "*.json")) {
		validatePayload(obj(readJSON(p)), true)
	}
	return M{"sessions": len(arr(state["sessions"])), "expressions": len(arr(state["expressions"])), "concepts": len(arr(state["concepts"]))}
}
func sourceFiles(root string) []string {
	out := []string{}
	if !exists(root) {
		return out
	}
	must(filepath.WalkDir(root, func(p string, d fs.DirEntry, e error) error {
		if e != nil {
			return e
		}
		require(d.Type()&os.ModeSymlink == 0, "学习目录含符号链接，未跨出目录复制："+p)
		if d.IsDir() {
			if p != root && filepath.Base(p) == "Live" && filepath.Dir(p) == root {
				return filepath.SkipDir
			}
			return nil
		}
		name := d.Name()
		if strings.HasSuffix(name, ".lock") {
			return nil
		}
		require(d.Type().IsRegular(), "学习目录含非普通文件："+p)
		out = append(out, p)
		require(len(out) <= maxFiles, "档案文件过多，请使用经核对的文件迁移。")
		return nil
	}))
	return out
}
func treeFingerprint(root string) M {
	out := M{}
	for _, p := range sourceFiles(root) {
		rel, e := filepath.Rel(root, p)
		must(e)
		out[filepath.ToSlash(rel)] = hash(readFile(p))
	}
	return out
}
func backupBytes(root, project string, includeLive bool) ([]byte, M) {
	payload := map[string][]byte{}
	var counts M
	withLock(filepath.Join(root, ".write.lock"), func() {
		counts = archiveCounts(root)
		total := 0
		for _, p := range sourceFiles(root) {
			b := readFile(p)
			total += len(b)
			require(total <= maxBackup, "档案超过网页备份上限。")
			rel, e := filepath.Rel(root, p)
			must(e)
			payload["data/"+filepath.ToSlash(rel)] = b
		}
		if project != "" {
			payload["context/project.md"] = readFile(project)
		}
		if includeLive && exists(filepath.Join(root, "Live", "companion.sqlite3")) {
			dir, e := os.MkdirTemp("", "english-coach-snapshot-")
			must(e)
			defer os.RemoveAll(dir)
			target := filepath.Join(dir, "companion.sqlite3")
			l := openLive(root)
			defer l.close()
			sqlExec(l.db, "VACUUM INTO ?", target)
			payload["data/Live/companion.sqlite3"] = readFile(target)
		}
	})
	files := M{}
	total := 0
	for name, b := range payload {
		total += len(b)
		files[name] = M{"sha256": hash(b), "size": len(b)}
	}
	require(total <= maxBackup, "备份内容超过上限。")
	manifest := M{"format": "english-speaking-coach-backup", "version": 1, "created_at": now(), "counts": counts, "includes_live": payload["data/Live/companion.sqlite3"] != nil, "includes_project_page": payload["context/project.md"] != nil, "files": files}
	var out bytes.Buffer
	z := zip.NewWriter(&out)
	for name, b := range payload {
		f, e := z.Create(name)
		must(e)
		_, e = f.Write(b)
		must(e)
	}
	f, e := z.Create("manifest.json")
	must(e)
	_, e = f.Write(encode(manifest))
	must(e)
	must(z.Close())
	inspectBackup(out.Bytes())
	return out.Bytes(), manifest
}
func inspectBackup(blob []byte) M {
	require(len(blob) <= maxBackup, "备份过大。")
	z, e := zip.NewReader(bytes.NewReader(blob), int64(len(blob)))
	must(e)
	require(len(z.File) <= maxFiles+2, "备份文件过多。")
	payload := map[string][]byte{}
	folded := map[string]bool{}
	var total uint64
	for _, f := range z.File {
		name := f.Name
		require(!f.FileInfo().IsDir() && !strings.ContainsAny(name, "\\:") && !strings.HasPrefix(name, "/") && path.Clean(name) == name && !strings.Contains(name, "../") && name != "..", "备份包含不安全路径。")
		require(f.Mode()&os.ModeSymlink == 0, "备份包含符号链接。")
		lower := strings.ToLower(name)
		require(!folded[lower], "备份包含重复文件或跨平台大小写冲突。")
		folded[lower] = true
		total += f.UncompressedSize64
		require(total <= maxBackup, "备份解压后过大。")
		r, e := f.Open()
		must(e)
		b, e := io.ReadAll(io.LimitReader(r, maxBackup+1))
		r.Close()
		must(e)
		require(uint64(len(b)) == f.UncompressedSize64, "备份内容大小不一致。")
		payload[name] = b
	}
	manifest := parseObject(string(payload["manifest.json"]))
	require(manifest["format"] == "english-speaking-coach-backup" && integer(manifest["version"]) == 1, "不是受支持的完整学习备份。")
	files := obj(manifest["files"])
	require(len(files)+1 == len(payload), "备份文件清单不一致。")
	require(files["data/profile.json"] != nil && files["data/Archive/legacy-v1.md"] != nil, "备份缺少主要学习文件。")
	for name, v := range files {
		require(strings.HasPrefix(name, "data/") || name == "context/project.md", "未知备份内容。")
		b, ok := payload[name]
		meta := obj(v)
		require(ok && len(b) == integer(meta["size"]) && hash(b) == str(meta["sha256"]), "备份校验失败："+name)
	}
	require(truth(manifest["includes_project_page"]) == (payload["context/project.md"] != nil), "项目页清单不一致。")
	return manifest
}
func extractBackup(blob []byte, target string) (M, string) {
	manifest := inspectBackup(blob)
	z, e := zip.NewReader(bytes.NewReader(blob), int64(len(blob)))
	must(e)
	page := ""
	for _, f := range z.File {
		if f.Name == "manifest.json" {
			continue
		}
		r, e := f.Open()
		must(e)
		b, e := io.ReadAll(r)
		r.Close()
		must(e)
		if strings.HasPrefix(f.Name, "data/") {
			dest := filepath.Join(target, filepath.FromSlash(strings.TrimPrefix(f.Name, "data/")))
			require(within(dest, target), "Unsafe backup destination")
			atomicWrite(dest, b)
		} else if f.Name == "context/project.md" {
			page = filepath.Join(target, "Context", "project-"+hash(b)[:12]+".md")
			if exists(page) {
				require(sameBytes(readFile(page), b), "项目页目标冲突。")
			}
			atomicWrite(page, b)
		}
	}
	for _, d := range []string{"Sessions", "Evidence", "Pending"} {
		mkdir(filepath.Join(target, d))
	}
	require(equal(archiveCounts(target), manifest["counts"]), "恢复后的记录数量与备份不一致。")
	return manifest, page
}
func detachRuntime(root string) {
	for _, p := range glob(filepath.Join(root, "Runtime", "Reviews", "*.json")) {
		j := obj(readJSON(p))
		j["auto_review"] = false
		delete(j, "source")
		delete(j, "worker_pid")
		if j["status"] != "saved" && j["status"] != "error" {
			j["status"], j["error"] = "error", "这是迁移前的未完成复盘；Agent 需要找回该场来源后继续。"
		}
		writeJSON(p, j)
	}
	must(os.RemoveAll(filepath.Join(root, "Runtime", "ReviewWatches")))
	if exists(filepath.Join(root, "Live", "companion.sqlite3")) {
		l := openLive(root)
		defer l.close()
		for _, v := range query(l.db, "SELECT id,state FROM runs") {
			l.patch(str(obj(v)["id"]), M{"desired": "stopped", "ready": false, "status": "stopped", "source": "", "imported": true})
		}
	}
}
func saveConfiguration(root, project string) M {
	if exists(configPath()) {
		writeJSON(filepath.Join(filepath.Dir(configPath()), "location-history", time.Now().Format("20060102-150405.000000000")+".json"), readJSON(configPath()))
	}
	var page any
	if project != "" {
		page = project
	}
	c := M{"schema_version": 1, "data_root": root, "project_page": page}
	writeJSON(configPath(), c)
	return c
}
func restoreBackup(blob []byte, destination string, activate bool) M {
	if activate {
		assertIdle(str(workspace("")["data_root"]))
	}
	target := checkRoot(destination)
	require(emptyDir(target), "目标目录不是空目录；没有覆盖或合并现有档案。")
	mkdir(filepath.Dir(target))
	tmp, e := os.MkdirTemp(filepath.Dir(target), ".english-restore-")
	must(e)
	defer os.RemoveAll(tmp)
	staging := filepath.Join(tmp, "archive")
	mkdir(staging)
	manifest, page := extractBackup(blob, staging)
	pageRel := ""
	if page != "" {
		pageRel, e = filepath.Rel(staging, page)
		must(e)
	}
	detachRuntime(staging)
	rebuild(staging)
	require(equal(archiveCounts(staging), manifest["counts"]), "恢复校验失败，配置未改变。")
	require(emptyDir(target), "目标目录已改变；未覆盖。")
	if exists(target) {
		must(os.Remove(target))
	}
	must(os.Rename(staging, target))
	var cfg any
	if activate {
		p := ""
		if pageRel != "" {
			p = filepath.Join(target, pageRel)
		}
		cfg = saveConfiguration(target, p)
	}
	return M{"status": "restored", "data_root": target, "counts": manifest["counts"], "configuration": cfg, "source_retained": true}
}
func adoptArchive(destination string) M {
	target := checkRoot(destination)
	counts := archiveCounts(target)
	assertIdle(target)
	assertIdle(str(workspace("")["data_root"]))
	sourceFiles(target)
	pages := glob(filepath.Join(target, "Context", "project-*.md"))
	page := ""
	if len(pages) == 1 {
		page = pages[0]
	}
	w := workspace("")
	if absolute(str(w["data_root"])) == target {
		page = str(w["project_page"])
	}
	var cfg M
	withLock(filepath.Join(target, ".write.lock"), func() { detachRuntime(target); cfg = saveConfiguration(target, page) })
	return M{"status": "adopted", "data_root": target, "counts": counts, "configuration": cfg, "source_retained": true}
}

type TransferPlan struct {
	action, target, root          string
	blob                          []byte
	manifest, counts, fingerprint M
	created                       time.Time
}

func (s *Server) storageInfo() M {
	w := workspace("")
	var project any
	if absolute(str(w["data_root"])) == s.archive.root {
		project = w["project_page"]
	}
	return M{"data_root": s.archive.root, "skill_root": skillRoot(), "viewer_root": "embedded://assets/library", "config_path": configPath(), "default_data_root": defaultRoot(), "backup_path": filepath.Join(filepath.Dir(configPath()), "backups", "latest.zip"), "embedded": within(s.archive.root, skillRoot()), "location": "独立的本地学习目录", "project_page": project, "open_token": s.archive.token, "can_switch": s.managed, "available": exists(filepath.Join(s.archive.root, "profile.json")), "transfer_limit_bytes": maxBackup}
}
func (s *Server) previewStorage(body M) M {
	require(s.managed, "这是绑定单个目录的预览服务，请使用工作区服务迁移。")
	for k := range body {
		require(has(stringsA("action", "destination", "backup_base64"), k), "未知迁移字段。")
	}
	assertIdle(s.archive.root)
	target := checkRoot(str(body["destination"]))
	root := s.archive.root
	require(!within(target, root) && !within(root, target), "新旧目录不能相同或相互包含。")
	p := &TransferPlan{action: str(body["action"]), target: target, root: root, created: time.Now()}
	switch p.action {
	case "adopt":
		assertIdle(target)
		p.counts = archiveCounts(target)
		p.fingerprint = treeFingerprint(target)
	case "move", "restore":
		require(emptyDir(target), "目标目录不是空目录，不会覆盖或合并。")
		if p.action == "move" {
			p.blob, p.manifest = backupBytes(root, str(s.storageInfo()["project_page"]), true)
		} else {
			b, e := base64.StdEncoding.Strict().DecodeString(str(body["backup_base64"]))
			must(e)
			p.blob = b
			p.manifest = inspectBackup(b)
			temp, e := os.MkdirTemp("", "english-backup-check-")
			must(e)
			defer os.RemoveAll(temp)
			extractBackup(b, temp)
		}
		p.counts = obj(p.manifest["counts"])
	default:
		panic("请选择搬动当前档案、恢复备份或使用已有档案。")
	}
	for k, p := range s.plans {
		if time.Since(p.created) > 10*time.Minute {
			delete(s.plans, k)
		}
	}
	require(len(s.plans) < 3, "已有三个迁移预览，请完成一个或等待过期。")
	id := token()
	s.plans[id] = p
	return M{"plan": id, "action": p.action, "destination": target, "counts": p.counts, "source_retained": root, "includes_live": p.manifest["includes_live"], "message": "校验完成。确认后网页与下次练习使用这个目录；原目录保留，不覆盖、不合并。"}
}
func (s *Server) applyStorage(body M) M {
	require(exactKeys(body, "plan"), "无效的迁移确认。")
	p := s.plans[str(body["plan"])]
	require(p != nil && time.Since(p.created) < 10*time.Minute, "预览已过期，请重新校验。")
	require(s.managed && s.archive.root == p.root, "当前目录已改变，请重新校验。")
	assertIdle(s.archive.root)
	if p.action == "adopt" {
		assertIdle(p.target)
		require(equal(archiveCounts(p.target), p.counts) && equal(treeFingerprint(p.target), p.fingerprint), "待使用档案已改变，请重新校验。")
	} else if p.action == "move" {
		_, fresh := backupBytes(p.root, str(s.storageInfo()["project_page"]), true)
		require(equal(fresh["files"], p.manifest["files"]), "源档案已改变，请重新校验，避免遗漏新记录。")
	}
	s.stopBackground()
	defer s.startBackground()
	var result M
	if p.action == "adopt" {
		result = adoptArchive(p.target)
	} else {
		result = restoreBackup(p.blob, p.target, true)
	}
	s.archive = newArchive(p.target)
	s.plans = map[string]*TransferPlan{}
	result["message"] = "已切换到校验后的学习目录。原目录仍保留。"
	return result
}
