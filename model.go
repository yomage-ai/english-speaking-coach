package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/pelletier/go-toml/v2"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
	"unicode"
)

const defaultModel = "gpt-5.6-sol"

type ModelClient struct {
	model        string
	timeout      time.Duration
	instructions string
	cmd          *exec.Cmd
	stdin        io.WriteCloser
	events       chan M
	done         chan struct{}
	cancel       context.CancelFunc
	scratch      string
	thread       string
	serial       int
	turns        int
	contextTail  A
	mu           sync.Mutex
}

func newModelClient(model string, timeout time.Duration) *ModelClient {
	return &ModelClient{model: model, timeout: timeout, instructions: str(contracts["translation_instructions"])}
}
func codexExecutable() string {
	candidates := []string{os.Getenv("ENGLISH_COACH_CODEX"), "/Applications/Codex.app/Contents/Resources/codex", "/Applications/ChatGPT.app/Contents/Resources/codex"}
	if p, e := exec.LookPath("codex"); e == nil {
		candidates = append(candidates, p)
	}
	if local := os.Getenv("LOCALAPPDATA"); local != "" {
		candidates = append(candidates, glob(filepath.Join(local, "Programs", "*", "resources", "codex.exe"))...)
	}
	for _, p := range candidates {
		if p == "" || !exists(p) {
			continue
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		out, e := exec.CommandContext(ctx, p, "app-server", "--help").Output()
		cancel()
		if e == nil && bytes.Contains(out, []byte("--listen")) {
			return absolute(p)
		}
	}
	panic(fmt.Errorf("找不到支持 app-server 的 Codex。Agent 需要检查桌面内置 CLI；无需安装 Python。"))
}
func modelCommand(binary string) []string {
	cfg := M{}
	p := filepath.Join(codexHome(), "config.toml")
	if exists(p) {
		must(toml.Unmarshal(readFile(p), &cfg))
	}
	overrides := M{"web_search": "disabled", "project_doc_max_bytes": 0, "history.persistence": "none", "forced_login_method": "chatgpt", "agents.enabled": false}
	for _, v := range arr(contracts["disabled_features"]) {
		overrides["features."+str(v)] = false
	}
	for k := range obj(cfg["mcp_servers"]) {
		require(regexp.MustCompile(`^[\pL\pN_-]+$`).MatchString(k), "MCP 配置名称无法安全覆盖；未启动模型连接。")
		overrides["mcp_servers."+k+".enabled"] = false
	}
	args := []string{}
	for k, v := range overrides {
		args = append(args, "-c", k+"="+compact(v))
	}
	return append(args, "app-server", "--listen", "stdio://")
}
func (c *ModelClient) close() {
	c.mu.Lock()
	cancel, done, dir := c.cancel, c.done, c.scratch
	c.cancel = nil
	c.scratch = ""
	c.thread = ""
	c.mu.Unlock()
	if cancel != nil {
		cancel()
	}
	if done != nil {
		select {
		case <-done:
		case <-time.After(4 * time.Second):
		}
	}
	if dir != "" {
		_ = os.RemoveAll(dir)
	}
}
func (c *ModelClient) connect(ctx context.Context) {
	c.close()
	dir, e := os.MkdirTemp("", "english-coach-model-")
	must(e)
	c.scratch = dir
	child, cancel := context.WithCancel(ctx)
	c.cancel = cancel
	binary := codexExecutable()
	cmd := exec.CommandContext(child, binary, modelCommand(binary)...)
	cmd.Dir = dir
	stdout, e := cmd.StdoutPipe()
	must(e)
	stdin, e := cmd.StdinPipe()
	must(e)
	cmd.Stderr = io.Discard
	cmd.WaitDelay = 3 * time.Second
	c.cmd, c.stdin = cmd, stdin
	c.events = make(chan M, 256)
	c.done = make(chan struct{})
	must(cmd.Start())
	events, done := c.events, c.done
	go func() {
		defer close(done)
		defer close(events)
		defer cmd.Wait()
		scanner := bufio.NewScanner(stdout)
		scanner.Buffer(make([]byte, 64*1024), 16*1024*1024)
		for scanner.Scan() {
			var row M
			if json.Unmarshal(scanner.Bytes(), &row) != nil {
				continue
			}
			select {
			case events <- row:
			case <-child.Done():
				return
			}
		}
	}()
	c.request(ctx, "initialize", M{"clientInfo": M{"name": "english_coach_companion", "version": version}, "capabilities": M{"experimentalApi": true}})
	c.send("initialized", M{}, nil)
	account := obj(c.request(ctx, "account/read", M{"refreshToken": false})["account"])
	require(account["type"] == "chatgpt", "后台 Codex 未读到 ChatGPT 登录。Agent 需要检查现有登录；不会改用 API Key。")
	models := A{}
	var cursor any
	for i := 0; i < 10; i++ {
		res := c.request(ctx, "model/list", M{"includeHidden": true, "cursor": cursor})
		models = append(models, arr(res["data"])...)
		cursor = res["nextCursor"]
		if str(cursor) == "" {
			break
		}
	}
	supported := false
	for _, v := range models {
		m := obj(v)
		if m["model"] != c.model {
			continue
		}
		for _, v := range arr(m["supportedReasoningEfforts"]) {
			if obj(v)["reasoningEffort"] == "low" {
				supported = true
			}
		}
	}
	require(supported, "当前登录未提供所选模型的 low 模式；未自动切换模型。")
	c.startThread(ctx)
}
func (c *ModelClient) startThread(ctx context.Context) {
	res := c.request(ctx, "thread/start", M{"model": c.model, "ephemeral": true, "cwd": c.scratch, "sandbox": "read-only", "approvalPolicy": "never", "baseInstructions": c.instructions, "config": M{"model_reasoning_effort": "low"}})
	require(res["model"] == c.model, "后台返回了不同模型，连接已停止。")
	c.thread = str(obj(res["thread"])["id"])
	require(c.thread != "", "Model did not return a thread ID")
	c.turns = 0
}
func (c *ModelClient) send(method string, params M, id any) {
	row := M{"method": method, "params": params}
	if id != nil {
		row["id"] = id
	}
	require(c.stdin != nil, "后台 Codex 连接尚未建立。")
	_, e := io.WriteString(c.stdin, compact(row)+"\n")
	must(e)
}
func (c *ModelClient) receive(ctx context.Context, deadline time.Time) M {
	select {
	case <-ctx.Done():
		panic(ctx.Err())
	case <-time.After(max(time.Millisecond, time.Until(deadline))):
		panic(fmt.Errorf("模型未在本次等待上限内返回；原文和待办仍保留，可重试。"))
	case row, ok := <-c.events:
		require(ok, "后台 Codex 进程退出；Agent 需要检查 CLI 配置与登录。")
		if row["id"] != nil && row["method"] != nil {
			panic(fmt.Errorf("模型请求了额外操作，已拒绝并停止本次连接。"))
		}
		method := str(row["method"])
		if method == "item/started" || method == "item/completed" {
			typ := obj(obj(row["params"])["item"])["type"]
			require(has(stringsA("userMessage", "agentMessage", "reasoning"), typ), "模型出现非文本操作，已停止本次连接。")
		}
		return row
	}
}
func (c *ModelClient) request(ctx context.Context, method string, params M) M {
	c.serial++
	id := c.serial
	c.send(method, params, id)
	deadline := time.Now().Add(c.timeout)
	for {
		row := c.receive(ctx, deadline)
		if integer(row["id"]) == id && row["id"] != nil {
			require(row["error"] == nil, "Codex 拒绝后台请求；Agent 需要检查协议、模型与账户状态。")
			return obj(row["result"])
		}
	}
}
func (c *ModelClient) generate(ctx context.Context, payload M, schema any, stream func(string)) M {
	if c.thread == "" {
		c.connect(ctx)
	} else if c.turns >= 20 {
		c.startThread(ctx)
	}
	res := c.request(ctx, "turn/start", M{"threadId": c.thread, "effort": "low", "input": A{M{"type": "text", "text": compact(payload)}}, "outputSchema": schema})
	turn := str(obj(res["turn"])["id"])
	require(turn != "", "Model did not return a turn ID")
	output := []string{}
	streamed := map[string]string{}
	deadline := time.Now().Add(c.timeout)
	for {
		event := c.receive(ctx, deadline)
		p := obj(event["params"])
		if str(p["turnId"]) != "" && p["turnId"] != turn {
			continue
		}
		switch event["method"] {
		case "item/agentMessage/delta":
			key := textOr(p["itemId"], "answer")
			streamed[key] += str(p["delta"])
			require(len(streamed[key]) <= 8*1024*1024, "Model output exceeded limit")
			if stream != nil {
				stream(streamed[key])
			}
		case "item/completed":
			item := obj(p["item"])
			if item["type"] == "agentMessage" && (item["phase"] == nil || item["phase"] == "final_answer") {
				output = append(output, str(item["text"]))
				if stream != nil {
					stream(str(item["text"]))
				}
			}
		case "turn/completed":
			t := obj(p["turn"])
			if t["id"] == turn {
				require(t["status"] == "completed", "模型生成未完成；原话和待办已保留。")
				c.turns++
				return parseObject(strings.Join(output, ""))
			}
		}
	}
}

// A JSON decoder stops at incomplete objects. It never guesses missing braces or
// displays unvalidated fragments. Complete array items can be published early.
func arrayPrefix(text, key string, limit int) (A, bool) {
	re := regexp.MustCompile(`^\s*\{\s*"` + regexp.QuoteMeta(key) + `"\s*:\s*\[`)
	loc := re.FindStringIndex(text)
	if loc == nil {
		return A{}, false
	}
	rest := strings.TrimLeft(text[loc[1]:], " \r\n\t")
	out := A{}
	for len(out) < limit {
		if strings.HasPrefix(rest, "]") {
			return out, true
		}
		var v any
		dec := json.NewDecoder(strings.NewReader(rest))
		if dec.Decode(&v) != nil {
			return out, false
		}
		out = append(out, v)
		rest = strings.TrimLeft(rest[dec.InputOffset():], " \r\n\t")
		if strings.HasPrefix(rest, ",") {
			rest = strings.TrimLeft(rest[1:], " \r\n\t")
		} else if !strings.HasPrefix(rest, "]") {
			return out, false
		}
	}
	return out, false
}

var hanRE = regexp.MustCompile(`[\x{3400}-\x{9fff}]`)
var englishRE = regexp.MustCompile(`[A-Za-z][A-Za-z0-9\s’…'.,!?;:\-]*`)
var latinRE = regexp.MustCompile(`[A-Za-z]+`)

func translationUnits(segments A) A {
	units := A{}
	for _, v := range segments {
		s := obj(v)
		text := str(s["text"])
		offsets := [][2]int{}
		if !hanRE.MatchString(text) && latinRE.MatchString(text) {
			offsets = append(offsets, [2]int{0, len(text)})
		} else {
			for _, m := range englishRE.FindAllStringIndex(text, -1) {
				end := m[0] + len(strings.TrimRightFunc(text[m[0]:m[1]], unicode.IsSpace))
				if m[0] > 0 && text[m[0]-1] == '\'' && end > m[0] && text[end-1] == '\'' {
					end--
				}
				offsets = append(offsets, [2]int{m[0], end})
			}
		}
		require(len(offsets) <= 40, "单个转写包含过多英文片段。")
		for i, m := range offsets {
			units = append(units, M{"id": fmt.Sprintf("%s/english/%d", str(s["id"]), i), "segment_id": s["id"], "text": text[m[0]:m[1]], "start": m[0], "end": m[1]})
		}
	}
	return units
}
func normalizeLatin(s string) string {
	return strings.Join(latinRE.FindAllString(strings.ToLower(s), -1), " ")
}
func assembleTranslations(segments, units, translated A) A {
	byID := M{}
	for _, v := range translated {
		t := obj(v)
		id := str(t["id"])
		require(id != "" && byID[id] == nil, "Duplicate/missing translation ID")
		byID[id] = t
	}
	require(len(byID) == len(units), "英文片段未全部获得译文；原话已保留。")
	for _, v := range units {
		u := obj(v)
		t := obj(byID[str(u["id"])])
		zh := str(t["chinese"])
		require(strings.TrimSpace(zh) != "" && len([]rune(zh)) <= 12000, "无效译文。")
		ws := latinRE.FindAllString(str(u["text"]), -1)
		if t["kind"] == "name" {
			require(len(ws) >= 1 && len(ws) <= 3 && normalizeLatin(zh) == normalizeLatin(str(u["text"])), "Invalid proper-name translation")
			for _, w := range ws {
				require(w[0] >= 'A' && w[0] <= 'Z', "Ordinary vocabulary is not a proper name")
			}
		} else {
			require(t["kind"] == "translation" && hanRE.MatchString(zh), "译文未给出中文句意。")
			if len(ws) >= 2 {
				require(!strings.Contains(normalizeLatin(zh), normalizeLatin(str(u["text"]))), "译文只是英文回声。")
			}
		}
	}
	out := A{}
	for _, v := range segments {
		s := obj(v)
		zh := str(s["text"])
		for _, v := range reverse(units) {
			u := obj(v)
			if u["segment_id"] == s["id"] {
				zh = zh[:integer(u["start"])] + str(obj(byID[str(u["id"])])["chinese"]) + zh[integer(u["end"]):]
			}
		}
		require(len([]rune(zh)) <= 24000, "译文过长。")
		out = append(out, M{"id": s["id"], "chinese": strings.TrimSpace(zh)})
	}
	return out
}
func validateHint(value M, conversation A) M {
	var latest M
	for _, v := range reverse(conversation) {
		if obj(v)["role"] == "user" {
			latest = obj(v)
			break
		}
	}
	if latest == nil || value["kind"] == "none" || obj(latest["fragment"])["kind"] == "word_tail" {
		return nil
	}
	if !has(stringsA("help", "continue"), value["kind"]) || value["source_id"] != latest["id"] {
		return nil
	}
	quote := str(value["quote"])
	if strings.TrimSpace(quote) == "" || !strings.Contains(str(latest["text"]), quote) {
		return nil
	}
	for _, k := range []string{"english", "chinese", "next_cue"} {
		if _, ok := value[k].(string); !ok || len([]rune(str(value[k]))) > 600 {
			return nil
		}
	}
	en, cue := strings.TrimSpace(str(value["english"])), strings.TrimSpace(str(value["next_cue"]))
	if hanRE.MatchString(en+cue) || len(strings.Fields(en)) > 25 || len(strings.Fields(cue)) > 12 {
		return nil
	}
	groups := arr(value["groups"])
	if len(groups) > 2 {
		return nil
	}
	parts := []string{}
	for _, v := range groups {
		if _, ok := v.(string); !ok || len([]rune(str(v))) > 400 {
			return nil
		}
		parts = append(parts, str(v))
	}
	if value["kind"] == "help" {
		if en == "" || strings.TrimSpace(str(value["chinese"])) == "" || !equal(words(strings.Join(parts, " ")), words(en)) {
			return nil
		}
		if len(words(en)) <= 7 {
			value["groups"] = stringsA(en)
		}
	} else if en != "" || str(value["chinese"]) != "" || len(groups) > 0 || cue == "" {
		return nil
	}
	return merge(pick(value, "kind", "source_id", "quote", "english", "chinese", "next_cue", "groups"), M{"source_text": latest["text"]})
}
func (c *ModelClient) translate(ctx context.Context, segments A, teaching M, publish func(A, float64)) (A, M, float64) {
	units := translationUnits(segments)
	if len(units) == 0 && teaching == nil {
		return assembleTranslations(segments, units, A{}), nil, 0
	}
	start := time.Now()
	payloadRows, unitRows := A{}, A{}
	for _, v := range segments {
		payloadRows = append(payloadRows, pick(obj(v), "id", "role", "text"))
	}
	for _, v := range units {
		unitRows = append(unitRows, pick(obj(v), "id", "segment_id", "text"))
	}
	payload := M{"segments": payloadRows, "prior_context": c.contextTail, "units": unitRows}
	var schema any = rawContracts["translation_schema"]
	if teaching != nil {
		payload["teaching_context"] = teaching
		var transport struct {
			Properties map[string]json.RawMessage `json:"properties"`
		}
		must(json.Unmarshal(rawContracts["translation_schema"], &transport))
		schema = json.RawMessage(`{"type":"object","properties":{"translations":` + string(transport.Properties["translations"]) + `,"teaching":` + string(rawContracts["teaching_schema"]) + `},"required":["translations","teaching"],"additionalProperties":false}`)
	}
	published := false
	answer := c.generate(ctx, payload, schema, func(raw string) {
		if publish == nil || published {
			return
		}
		part, complete := arrayPrefix(raw, "translations", 200)
		if complete {
			var visible A
			if attempt(func() { visible = assembleTranslations(segments, units, part) }) == nil {
				publish(visible, time.Since(start).Seconds())
				published = true
			}
		}
	})
	out := assembleTranslations(segments, units, arr(answer["translations"]))
	var hint M
	if teaching != nil {
		hint = validateHint(obj(answer["teaching"]), arr(teaching["conversation"]))
	}
	c.contextTail = tail(append(c.contextTail, payloadRows...), 4)
	return out, hint, time.Since(start).Seconds()
}

// Publish four complete phrase fields before optional notes/groups have finished.
// No text repair or closing-brace guessing; each included field decoded in full.
func suggestionPrefix(text string) A {
	re := regexp.MustCompile(`^\s*\{\s*"expressions"\s*:\s*\[`)
	loc := re.FindStringIndex(text)
	if loc == nil {
		return A{}
	}
	rest := strings.TrimSpace(text[loc[1]:])
	items := A{}
	for len(items) < 3 && strings.HasPrefix(rest, "{") {
		rest = strings.TrimSpace(rest[1:])
		fields := M{}
		finished := false
		for len(rest) > 0 {
			if strings.HasPrefix(rest, "}") {
				rest = strings.TrimSpace(rest[1:])
				finished = true
				break
			}
			var key string
			dec := json.NewDecoder(strings.NewReader(rest))
			if dec.Decode(&key) != nil {
				break
			}
			rest = strings.TrimSpace(rest[dec.InputOffset():])
			if !strings.HasPrefix(rest, ":") {
				break
			}
			rest = strings.TrimSpace(rest[1:])
			var value any
			dec = json.NewDecoder(strings.NewReader(rest))
			if dec.Decode(&value) != nil {
				break
			}
			fields[key] = value
			rest = strings.TrimSpace(rest[dec.InputOffset():])
			if strings.HasPrefix(rest, ",") {
				rest = strings.TrimSpace(rest[1:])
			} else if !strings.HasPrefix(rest, "}") {
				break
			}
		}
		if fields["source_turn_ids"] != nil && fields["original"] != nil && fields["english"] != nil && fields["chinese"] != nil {
			items = append(items, pick(fields, "source_turn_ids", "original", "english", "chinese"))
		}
		if !finished || !strings.HasPrefix(rest, ",") {
			break
		}
		rest = strings.TrimSpace(rest[1:])
	}
	return items
}
