# v0.2.4

- 修复超长混合句和异常翻译返回影响后续内容的问题。
- 优化专名与带重音字母的处理，原样保留的专名会明确标注。
- 优化纯中文显示，翻译连接异常时仍可查看原话。
- 修复原话补充后仍沿用旧译文的问题，并限制恢复时的连续重试。
- 优化暂停阅读，新增对话和延迟译文不会挤走正在看的内容。
- 加强表达提示与复盘的中英字段检查，隔离损坏的复盘登记。
- 修复损坏转写被静默略过、结束后待补译内容缺少重试入口的问题。

## English

- Fixed long mixed-language utterances and malformed translation responses blocking later content.
- Improved names and accented words, with an explicit label for names kept in their original spelling.
- Kept Chinese originals readable during translation connection failures.
- Fixed stale translations after transcript extensions and bounded consecutive recovery retries.
- Preserved paused reading positions while new messages and delayed translations arrive.
- Aligned language checks for written hints and reviews, and isolated damaged review registrations.
- Stopped silently skipping corrupt transcript rows and restored retry access for unfinished captions after Voice ends.
