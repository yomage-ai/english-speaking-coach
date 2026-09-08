v0.2.3 — 双语页更好读，翻译恢复更可靠 / Clearer captions and reliable recovery

- 优化：双语页压缩顶部区域，将场景、场次和学习目录收入“更多”，保留更多对话与译文。
- 修复：iPad 等专名误报导致中文中断；单句失败单独重试，后续句子继续翻译。
- 新增：已结束场次可在网页重试补译；暂停滚动时仍继续接收新内容。
- 优化：复盘保留已核对的预览，有提示的表达不再误记独立掌握并触发整份重做，入口直接显示整理状态。
- 修复：开发测试目录不会覆盖正式自动备份。

- Improved: More room for conversation and translations; scene, history and archive links move into More.
- Fixed: Mixed-case names such as iPad no longer interrupt Chinese captions. Failed sentences retry independently.
- Added: Retry captions after Voice ends; pausing scrolling keeps receiving new content.
- Improved: Reviews retain checked previews and conservatively record supplied wording without regenerating the entire draft. The review link shows progress.
- Fixed: Development fixtures cannot overwrite the managed recovery backup.
