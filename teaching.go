package main

import (
	"context"
	"encoding/json"
	"path/filepath"
	"time"
)

func (c *ModelClient) teach(ctx context.Context, teaching M) M {
	schema := json.RawMessage(`{"type":"object","properties":{"teaching":` + string(rawContracts["teaching_schema"]) + `},"required":["teaching"],"additionalProperties":false}`)
	answer := c.generate(ctx, M{"teaching_context": teaching}, schema, nil)
	return validateHint(obj(answer["teaching"]), arr(teaching["conversation"]))
}

func (l *Live) currentTeachingKey(run string) string {
	s := l.active()
	if s == nil || s["id"] != run || s["desired"] == "stopped" || terminal(s["status"]) || s["close_epoch"] != nil {
		return ""
	}
	rows := l.teachingRows(run)
	return teachingKey(M{"conversation": rows})
}

// Written help has its own bounded lane. Slow coaching never occupies the
// caption connection, and an obsolete learner turn is cancelled, not queued.
func runTeaching(ctx context.Context, root string) {
	lock, ok := tryLock(filepath.Join(root, "Runtime", ".teaching-worker.lock"))
	if !ok {
		return
	}
	defer lock.Unlock()
	l := openLive(root)
	defer l.close()
	var client *ModelClient
	closeClient := func() {
		if client != nil {
			client.close()
			client = nil
		}
	}
	defer closeClient()
	current, tried := "", ""
	failures, retryAt := 0, 0.0
	for ctx.Err() == nil {
		s := l.active()
		id := str(s["id"])
		key := l.currentTeachingKey(id)
		if id != current {
			closeClient()
			current, tried, failures, retryAt = id, "", 0, 0
		}
		if key == "" {
			closeClient()
		} else if key != tried && failures < 3 && epoch() >= retryAt {
			teaching := l.teachingContext(id)
			key = teachingKey(teaching)
			job, cancel := context.WithTimeout(ctx, 25*time.Second)
			watched := make(chan struct{})
			go func() {
				defer close(watched)
				if err := attempt(func() {
					for sleepContext(job, 250*time.Millisecond) {
						if l.currentTeachingKey(id) != key {
							cancel()
							return
						}
					}
				}); err != nil {
					cancel()
				}
			}()
			l.patch(id, M{"teaching_status": "generating", "teaching_error": nil})
			var hint M
			err := attempt(func() {
				if client == nil {
					client = newModelClient(str(s["model"]), 25*time.Second)
					client.freshTurns = true
					client.instructions = "Return only the requested JSON teaching object. Do not translate transcripts or use tools. " + str(contracts["teaching_instructions"])
					client.connect(ctx)
				}
				hint = client.teach(job, teaching)
			})
			cancel()
			<-watched
			if ctx.Err() != nil {
				return
			}
			if l.currentTeachingKey(id) != key {
				closeClient()
				l.patch(id, M{"teaching_status": "superseded", "teaching_error": nil})
				continue
			}
			if err != nil {
				closeClient()
				if _, content := err.(translationContentError); content {
					tried = key
				} else {
					failures++
					retryAt = epoch() + float64(failures*5)
				}
				l.patch(id, M{"teaching_status": "unavailable", "teaching_error": err.Error()})
			} else {
				tried, failures = key, 0
				if hint != nil {
					l.setMeta("hint:"+id, compact(hint))
				} else {
					sqlExec(l.db, "DELETE FROM meta WHERE key=?", "hint:"+id)
				}
				l.patch(id, M{"teaching_status": "ready", "teaching_error": nil})
			}
		}
		if !sleepContext(ctx, 300*time.Millisecond) {
			return
		}
	}
}
