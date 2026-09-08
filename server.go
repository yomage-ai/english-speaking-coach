package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type Server struct {
	archive  *Archive
	managed  bool
	port     int
	gate     sync.Mutex
	cancel   context.CancelFunc
	workers  sync.WaitGroup
	plans    map[string]*TransferPlan
	parent   context.Context
	instance string
}

func newServer(root string, managed bool) *Server {
	return &Server{archive: newArchive(root), managed: managed, plans: map[string]*TransferPlan{}, parent: context.Background(), instance: token()}
}
func (s *Server) startBackground() {
	if !exists(filepath.Join(s.archive.root, "profile.json")) {
		return
	}
	ctx, cancel := context.WithCancel(s.parent)
	s.cancel = cancel
	for _, f := range []func(context.Context, string){runTailer, runTranslations, runReviews} {
		s.workers.Add(1)
		go func(f func(context.Context, string), root string) {
			defer s.workers.Done()
			if err := attempt(func() { f(ctx, root) }); err != nil && ctx.Err() == nil {
				log.Printf("background worker stopped: %v", err)
			}
		}(f, s.archive.root)
	}
}
func (s *Server) stopBackground() {
	if s.cancel != nil {
		s.cancel()
		s.workers.Wait()
		s.cancel = nil
	}
}
func timeFromEpoch(e float64) string {
	return time.UnixMilli(int64(e * 1000)).Local().Format(time.RFC3339)
}
func (s *Server) identity() M {
	exe, e := os.Executable()
	must(e)
	return M{"application": "english-speaking-coach", "runtime": "go", "version": version, "code_revision": revision, "pid": os.Getpid(), "executable": exe, "data_root": s.archive.root, "skill_root": skillRoot(), "workspace_managed": s.managed, "instance_id": s.instance, "platform": runtime.GOOS + "/" + runtime.GOARCH}
}
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.gate.Lock()
	defer s.gate.Unlock()
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
	defer func() {
		if v := recover(); v != nil {
			sendJSON(w, r, 400, M{"error": fmt.Sprint(v)})
		}
	}()
	allowed := r.Host == fmt.Sprintf("127.0.0.1:%d", s.port) || r.Host == fmt.Sprintf("localhost:%d", s.port)
	if !allowed {
		sendJSON(w, r, 403, M{"error": "仅可从本机学习网页访问。"})
		return
	}
	if r.Method == "POST" {
		origin := r.Header.Get("Origin")
		if origin != "" && origin != "http://"+r.Host || subtle.ConstantTimeCompare([]byte(r.Header.Get("X-Coach-Token")), []byte(s.archive.token)) != 1 {
			sendJSON(w, r, 403, M{"error": "请从本机学习网页执行此操作。"})
			return
		}
		limit := int64(8192)
		if r.URL.Path == "/api/storage/preview" {
			limit = 360 * 1024 * 1024
		}
		typ, _, e := mime.ParseMediaType(r.Header.Get("Content-Type"))
		must(e)
		require(typ == "application/json", "无效的本地操作请求。")
		bodyBytes, e := io.ReadAll(http.MaxBytesReader(w, r.Body, limit))
		must(e)
		var body M
		must(json.Unmarshal(bodyBytes, &body))
		require(body != nil, "无效的本地操作内容。")
		switch r.URL.Path {
		case "/api/storage/open":
			require(len(body) == 0, "只能打开当前学习目录。")
			openDirectory(s.archive.root)
			sendJSON(w, r, 200, M{"status": "requested", "message": "已请求在文件管理器中打开学习目录。", "data_root": s.archive.root})
		case "/api/storage/backup":
			for k := range body {
				require(k == "include_live", "无效的备份选项。")
			}
			if v, ok := body["include_live"]; ok {
				_, ok = v.(bool)
				require(ok, "include_live must be boolean")
			}
			blob, _ := backupBytes(s.archive.root, str(s.storageInfo()["project_page"]), truth(body["include_live"]))
			w.Header().Set("Content-Disposition", "attachment; filename=english-learning-backup.zip")
			sendBytes(w, r, 200, blob, "application/zip")
		case "/api/storage/preview":
			sendJSON(w, r, 200, s.previewStorage(body))
		case "/api/storage/apply":
			sendJSON(w, r, 200, s.applyStorage(body))
		case "/api/review/retry":
			require(exactKeys(body, "thread", "voice"), "需要指定本场 Voice。")
			thread, voice := str(body["thread"]), str(body["voice"])
			p := reviewFile(s.archive.root, thread, voice)
			require(exists(p), "未找到本场复盘登记。")
			j := obj(readJSON(p))
			sendJSON(w, r, 200, omit(enqueueReview(s.archive.root, thread, voice, str(j["source"]), true), "source"))
		case "/api/live/retry":
			require(exactKeys(body, "run"), "需要指定本场字幕。")
			l := openLive(s.archive.root)
			defer l.close()
			l.retry(str(body["run"]))
			sendJSON(w, r, 200, M{"status": "retry_requested"})
		default:
			sendJSON(w, r, 404, M{"error": "操作不存在。"})
		}
		return
	}
	if r.Method != "GET" && r.Method != "HEAD" {
		sendJSON(w, r, 405, M{"error": "Method not allowed"})
		return
	}
	path := r.URL.Path
	if path == "/api/identity" {
		sendJSON(w, r, 200, s.identity())
		return
	}
	if path == "/api/storage" {
		sendJSON(w, r, 200, s.storageInfo())
		return
	}
	if strings.HasPrefix(path, "/api/") {
		args := M{}
		for k, v := range r.URL.Query() {
			args[k] = v[len(v)-1]
		}
		sendJSON(w, r, 200, s.archive.query(path, args))
		return
	}
	if strings.HasPrefix(path, "/records/") {
		id := strings.TrimSuffix(strings.TrimPrefix(path, "/records/"), ".md")
		if sessionID.MatchString(id) && obj(s.archive.load()["details"])[id] != nil {
			sendBytes(w, r, 200, readFile(filepath.Join(s.archive.root, "Sessions", id+".md")), "text/plain; charset=utf-8")
			return
		}
	}
	if path == "/" {
		path = "/index.html"
	}
	if has(stringsA("/index.html", "/app.js", "/app.css", "/live.js", "/live.css", "/storage.js", "/favicon.svg"), path) {
		b, e := bundled.ReadFile("assets/library" + path)
		must(e)
		typ := mime.TypeByExtension(filepath.Ext(path))
		sendBytes(w, r, 200, b, typ)
		return
	}
	sendJSON(w, r, 404, M{"error": "页面不存在。"})
}
func sendJSON(w http.ResponseWriter, r *http.Request, status int, v any) {
	sendBytes(w, r, status, encode(v), "application/json; charset=utf-8")
}
func sendBytes(w http.ResponseWriter, r *http.Request, status int, b []byte, typ string) {
	w.Header().Set("Content-Type", typ)
	w.Header().Set("Content-Length", fmt.Sprint(len(b)))
	w.WriteHeader(status)
	if r.Method != "HEAD" {
		_, _ = w.Write(b)
	}
}
func openDirectory(root string) {
	require(isDir(root), "学习目录暂不可用。")
	var cmd *exec.Cmd
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.CommandContext(ctx, "/usr/bin/open", root)
	case "windows":
		cmd = exec.CommandContext(ctx, "explorer.exe", root)
	default:
		cmd = exec.CommandContext(ctx, "xdg-open", root)
	}
	must(cmd.Run())
}
func serve(ctx context.Context, root string, port int, managed bool) {
	require(port >= 0 && port < 65536, "Invalid port")
	ln, e := net.Listen("tcp4", fmt.Sprintf("127.0.0.1:%d", port))
	must(e)
	s := newServer(root, managed)
	s.parent = ctx
	s.port = ln.Addr().(*net.TCPAddr).Port
	server := &http.Server{Handler: s, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 60 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 16384}
	defer ln.Close()
	s.startBackground()
	defer s.stopBackground()
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdown)
	}()
	fmt.Printf("English learning archive: http://127.0.0.1:%d\n", s.port)
	e = server.Serve(ln)
	if e != http.ErrServerClosed {
		must(e)
	}
}
