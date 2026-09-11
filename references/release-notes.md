# v1.0.2 — Coaching accuracy / 教学准确性优化

- 修复意思与英文不一致时仍被判定为正确的问题，教练会先核对表达和目标意思。
- 修复“刚才没有教我”被误解为停止教学的问题，漏掉的英文帮助会在当前对话中补上。
- 改进课后复盘对提示程度的记录，照示范完成的句子和词语不再被记为独立掌握。
- 改进相关中文翻译，明确区分过去漏教与以后不再教学。

- Fix cases where an English answer could be accepted despite not matching the learner’s intended meaning.
- Fix requests about missed earlier teaching being mistaken for a request to stop teaching; the coach now supplies the missing English help.
- Improve post-session evidence so repeated model answers are not recorded as independently mastered language.
- Improve Chinese translations to distinguish missed past teaching from future teaching preferences.
