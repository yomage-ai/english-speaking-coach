package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode/utf8"
)

const maxLine = 8 * 1024 * 1024

type sourcePendingError struct{ reason string }

func (e sourcePendingError) Error() string { return e.reason }

// Shared by live ingestion and closed snapshots so review cannot silently cover
// a different set of utterances. Empty interim text is not a completed utterance.
func transcriptSegment(p, row M) M {
	if !has(stringsA("user", "assistant"), p["role"]) {
		return nil
	}
	text, ok := p["text"].(string)
	require(ok, "Voice 片段缺少原话文本；读取已停止。")
	if strings.TrimSpace(text) == "" {
		return nil
	}
	require(str(p["id"]) != "", "Voice 片段缺少标识；读取已停止。")
	require(len([]rune(text)) <= 12000, "Voice 片段过长；读取已停止。")
	stamp(str(row["timestamp"]))
	return merge(pick(p, "id", "role", "text"), pick(row, "timestamp", "ordinal"))
}

// Complete JSONL lines only. The byte cursor never advances over a partial UTF-8 write.
func scanLines(path string, cursor int64, budget int64, visit func(M)) (next int64, partial bool) {
	f, e := os.Open(path)
	must(e)
	defer f.Close()
	_, e = f.Seek(cursor, io.SeekStart)
	must(e)
	r := bufio.NewReaderSize(f, 64*1024)
	next = cursor
	for budget <= 0 || next-cursor < budget {
		line := []byte{}
		for {
			part, e := r.ReadSlice('\n')
			line = append(line, part...)
			require(len(line) <= maxLine, "Voice 日志行过大，读取已停止。")
			if e == bufio.ErrBufferFull {
				continue
			}
			if e == io.EOF {
				return next, len(line) > 0
			}
			must(e)
			break
		}
		require(utf8.Valid(line), "Voice 日志不是有效 UTF-8。")
		var row M
		err := json.Unmarshal(line, &row)
		require(err == nil && str(row["type"]) != "", fmt.Sprintf("Voice 日志在字节 %d 有损坏的完整行；未跳过，已有原话保留。", next))
		visit(row)
		next += int64(len(line))
	}
	return
}
func sourceIdentity(path string) string {
	f, e := os.Open(path)
	must(e)
	defer f.Close()
	line, e := bufio.NewReader(io.LimitReader(f, maxLine+1)).ReadBytes('\n')
	must(e)
	require(len(line) <= maxLine && utf8.Valid(line), "Voice 日志头不完整。")
	var row M
	must(json.Unmarshal(line, &row))
	require(row["type"] == "session_meta" && str(obj(row["payload"])["id"]) != "", "这不是可识别的 Codex 任务日志。")
	return str(obj(row["payload"])["id"])
}
func findSource(thread string) string {
	require(regexp.MustCompile(`^[0-9a-f-]{36}$`).MatchString(thread), "需要明确的当前 Codex 任务 ID。")
	paths := glob(filepath.Join(codexHome(), "sessions", "*", "*", "*", "rollout-*-"+thread+".jsonl"))
	require(len(paths) == 1, "没有找到唯一的当前任务日志；Agent 需要指定核实的源文件。")
	return paths[0]
}
func lifecycle(path string) (voice string, cursor int64) {
	cursor, _ = scanLines(path, 0, 0, func(row M) {
		if row["type"] != "realtime_item" {
			return
		}
		p := obj(row["payload"])
		if p["type"] == "realtime_session_started" {
			voice = str(p["realtime_session_id"])
		} else if p["type"] == "realtime_session_closed" && p["realtime_session_id"] == voice {
			voice = ""
		}
	})
	return
}

// Cumulative transcript revisions are accepted only if one text extends the other.
// Unrelated text or a speaker change under one ID is a source conflict, never a rewrite.
func reconcileSegment(old, new M) M {
	require(old["role"] == new["role"], "同一片段 ID 的说话人冲突；原话已保留。")
	a, b := str(old["text"]), str(new["text"])
	if a == b || strings.HasPrefix(a, b) {
		return old
	}
	require(strings.HasPrefix(b, a), "同一片段 ID 的内容冲突；原话已保留。")
	return new
}
func snapshotVoice(source, thread, voice string) M {
	voiceSources(thread, voice)
	source = absolute(source)
	require(sourceIdentity(source) == thread, "源任务身份不一致，未恢复。")
	started, closed := "", ""
	rows := A{}
	indices := map[string]int{}
	cursor, partial := scanLines(source, 0, 0, func(row M) {
		if row["type"] != "realtime_item" {
			return
		}
		p := obj(row["payload"])
		if p["realtime_session_id"] != voice {
			return
		}
		switch p["type"] {
		case "realtime_session_started":
			started = str(row["timestamp"])
		case "realtime_session_closed":
			closed = str(row["timestamp"])
		case "transcript_segment":
			s := transcriptSegment(p, row)
			if s == nil {
				return
			}
			if i, ok := indices[str(s["id"])]; ok {
				rows[i] = reconcileSegment(obj(rows[i]), s)
			} else {
				indices[str(s["id"])] = len(rows)
				rows = append(rows, s)
			}
			require(len(rows) <= 2000, "单场 Voice 超过 2000 个片段。")
		}
	})
	if started == "" || closed == "" {
		panic(sourcePendingError{"仅恢复有明确开始和结束的指定 Voice；未监听下一场。"})
	}
	require(!stamp(closed).Before(stamp(started)), "Voice 结束时间早于开始时间；未生成复盘。")
	if partial {
		panic(sourcePendingError{"源日志尾行尚未写完整，请稍后重试。"})
	}
	return M{"source": source, "thread_id": thread, "voice_id": voice, "voice_started_at": started, "voice_closed_at": closed, "snapshot_at": now(), "cursor": cursor, "segments": rows}
}
func annotateFragments(rows A) A {
	out := A{}
	tailRE := regexp.MustCompile(`^[-–—]\s*([A-Za-z]+)[.!?,]?$`)
	stemRE := regexp.MustCompile(`([A-Za-z]+)\s*$`)
	continuationRE := regexp.MustCompile(`^[.,;:]\s+\S`)
	for _, v := range rows {
		r := copyM(v)
		text := strings.TrimSpace(str(r["text"]))
		if match := tailRE.FindStringSubmatch(text); match != nil {
			for _, v := range reverse(tail(out, 4)) {
				p := obj(v)
				if p["role"] != r["role"] {
					continue
				}
				delta := -1.0
				err := attempt(func() { delta = stamp(str(r["timestamp"])).Sub(stamp(str(p["timestamp"]))).Seconds() })
				stem := stemRE.FindStringSubmatch(str(p["text"]))
				if err == nil && delta >= 0 && delta <= 3 && stem != nil {
					r["fragment"] = M{"kind": "word_tail", "previous_id": p["id"], "joined_word": stem[1] + match[1]}
				}
				break
			}
		}
		if r["fragment"] == nil && continuationRE.MatchString(text) {
			r["fragment"] = M{"kind": "continuation"}
		}
		out = append(out, r)
	}
	return out
}

func sameBytes(a, b []byte) bool { return bytes.Equal(a, b) }
