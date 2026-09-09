package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"unicode"
)

// Content failures belong to an utterance/request, never to the connection.
// Only a completed model response is decoded here; transport failures stay errors.
type translationContentError struct{ cause error }

func (e translationContentError) Error() string { return e.cause.Error() }
func decodeModelObject(raw string) M {
	var out M
	if err := json.Unmarshal([]byte(raw), &out); err != nil || out == nil {
		panic(translationContentError{fmt.Errorf("模型返回的内容格式无效；原话已保留。")})
	}
	return out
}

func hasOtherLetters(text string) bool {
	return strings.IndexFunc(text, func(r rune) bool {
		return unicode.IsLetter(r) && !unicode.In(r, unicode.Latin, unicode.Han)
	}) >= 0
}

// Extract each utterance independently. A long/malformed mixed utterance cannot
// consume the connection retry budget or prevent later utterances from translating.
func planTranslations(segments A) (valid, units A, rejected M) {
	valid, units, rejected = A{}, A{}, M{}
	for _, v := range segments {
		r := obj(v)
		var part A
		if err := attempt(func() { part = translationUnits(A{r}) }); err != nil {
			rejected[str(r["id"])] = err.Error()
		} else {
			valid = append(valid, r)
			units = append(units, part...)
		}
	}
	return
}

// Chinese/numbers already have a readable original. Showing it does not require
// model login, and must not be held behind an English translation outage.
func (l *Live) copyLocalTranscripts(run string) {
	for _, v := range query(l.db, "SELECT id,text FROM segments WHERE run=? AND status IN ('pending','failed')", run) {
		r := obj(v)
		text := str(r["text"])
		if !latinRE.MatchString(text) && !hasOtherLetters(text) {
			l.translated(run, A{M{"id": r["id"], "chinese": text}}, 0, M{str(r["id"]): text})
		}
	}
}

func teachingKey(teaching M) string {
	rows := arr(teaching["conversation"])
	for i := len(rows) - 1; i >= 0; i-- {
		if obj(rows[i])["role"] != "user" {
			continue
		}
		// A coach reply can answer the pending question or change the next action.
		// Bind help to both sides of this exchange, not just the learner's text.
		version := A{}
		for _, v := range rows[i:] {
			version = append(version, pick(obj(v), "id", "role", "text"))
		}
		return hash([]byte(compact(version)))
	}
	return ""
}

func validExpressionLanguages(x M) bool {
	return latinRE.MatchString(str(x["english"])) && !hanRE.MatchString(str(x["english"])) && !hasOtherLetters(str(x["english"])) && hanRE.MatchString(str(x["chinese"]))
}
