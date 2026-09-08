package main

import (
	"context"
	"fmt"
	"github.com/google/uuid"
	"path/filepath"
	"time"
)

func recoverCaptions(root, thread, voice, source, model string, refresh bool) M {
	return recoverCaptionsContext(context.Background(), root, thread, voice, source, model, refresh)
}
func recoverCaptionsContext(ctx context.Context, root, thread, voice, source, model string, refresh bool) M {
	require(exists(filepath.Join(root, "profile.json")), "学习档案不可用，未创建空替代。")
	if source == "" {
		source = findSource(thread)
	}
	l := openLive(root)
	defer l.close()
	lock, ok := tryLock(filepath.Join(root, "Live", ".recover-"+hash([]byte(thread + "/" + voice))[:24]+".lock"))
	require(ok, "这场字幕恢复正在运行，未启动重复翻译。")
	defer lock.Unlock()
	snap := snapshotVoice(source, thread, voice)
	matches := A{}
	for _, v := range query(l.db, "SELECT * FROM runs") {
		s := stateRow(obj(v))
		if s["thread_id"] == thread && s["voice_id"] == voice {
			matches = append(matches, s)
		}
	}
	require(len(matches) <= 1, "同一 Voice 有多个缓存，需要先核对。")
	var s M
	if len(matches) > 0 {
		s = obj(matches[0])
		require(terminal(s["status"]) || s["status"] == "recovering", "这场实时绑定还未排空，未并行恢复。")
		require(absolute(str(s["source"])) == absolute(source), "已有 Voice 来源路径不同。")
	} else {
		s = M{"id": uuid.NewString(), "thread_id": thread, "voice_id": voice, "source": absolute(source), "created_at": now(), "created_epoch": epoch(), "demo": false, "model": model, "effort": "low", "status": "recovering", "ready": false, "error": nil, "recovery_reason": "missing_binding"}
		sqlExec(l.db, "INSERT INTO runs VALUES (?,?,?)", s["id"], "stopped", compact(s))
	}
	id := str(s["id"])
	old := query(l.db, "SELECT * FROM segments WHERE run=?", id)
	wanted := M{}
	for _, v := range arr(snap["segments"]) {
		wanted[str(obj(v)["id"])] = v
	}
	for _, v := range old {
		r := obj(v)
		require(wanted[str(r["id"])] != nil, "缓存有不在源快照中的片段。")
		reconcileSegment(r, obj(wanted[str(r["id"])]))
	}
	if !refresh && s["status"] == "ended" && len(old) == len(wanted) && integer(l.counts(id)["translated"]) == len(old) {
		return M{"status": "already_complete", "run_id": id, "segments": len(old), "model_batches": 0}
	}
	l.insertSegments(id, arr(snap["segments"]))
	l.patch(id, merge(pick(snap, "voice_started_at", "voice_closed_at", "snapshot_at", "cursor"), M{"desired": "stopped", "status": "recovering", "translation_status": "translating", "translation_error": nil, "ready": false, "error": nil, "recovery_mode": "after_voice", "model": model, "heartbeat_epoch": epoch()}))
	sqlExec(l.db, "UPDATE segments SET status='pending',attempts=0 WHERE run=? AND (status!='translated' OR ?)", id, refresh)
	client := newModelClient(model, 45*time.Second)
	defer client.close()
	batches := 0
	failure := attempt(func() {
		for {
			must(ctx.Err())
			rows := l.batch(id)
			if len(rows) == 0 {
				break
			}
			expected := M{}
			for _, v := range rows {
				expected[str(obj(v)["id"])] = obj(v)["text"]
			}
			l.patch(id, M{"heartbeat": now(), "heartbeat_epoch": epoch()})
			err := attempt(func() {
				out, _, rejected, latency := client.translate(ctx, rows, nil, nil)
				l.translated(id, out, latency, expected)
				l.failBatch(id, rows)
				l.rememberTranslationErrors(id, out, rejected)
				if latency > 0 {
					batches++
				}
			})
			if err != nil {
				client.close()
				l.failBatch(id, rows)
				require(integer(l.counts(id)["failed"]) == 0, err.Error())
			}
		}
	})
	if failure != nil {
		if ctx.Err() != nil {
			panic(failure)
		}
		l.patch(id, M{"status": "error", "ready": false, "translation_error": failure.Error(), "error": fmt.Sprint(failure)})
		panic(failure)
	}
	failed := integer(l.counts(id)["failed"])
	status := "recovered_after_voice"
	if failed > 0 {
		status = "partially_recovered_after_voice"
	}
	l.patch(id, M{"status": "ended", "translation_status": "ready", "ready": false, "error": nil, "translation_error": nil, "recovery_finished_at": now()})
	return M{"status": status, "run_id": id, "segments": len(wanted), "untranslated_segments": failed, "model_batches": batches, "prior_binding_existed": len(matches) > 0}
}

// Explicit browser retries are durable and scoped to an already closed Voice.
// This worker owns neither the microphone nor the active transcript binding.
func runCaptionRecoveries(ctx context.Context, root string) {
	lock, ok := tryLock(filepath.Join(root, "Runtime", ".caption-recovery-worker.lock"))
	if !ok {
		return
	}
	defer lock.Unlock()
	l := openLive(root)
	defer l.close()
	for ctx.Err() == nil {
		for _, v := range query(l.db, "SELECT * FROM runs") {
			s := stateRow(obj(v))
			if !truth(s["recovery_requested"]) {
				continue
			}
			err := attempt(func() {
				recoverCaptionsContext(ctx, root, str(s["thread_id"]), str(s["voice_id"]), str(s["source"]), textOr(s["model"], defaultModel), false)
			})
			if ctx.Err() != nil {
				return // keep request for restart
			}
			fields := M{"recovery_requested": false}
			if err != nil {
				fields["translation_error"] = err.Error()
			}
			l.patch(str(s["id"]), fields)
		}
		if !sleepContext(ctx, 500*time.Millisecond) {
			return
		}
	}
}
