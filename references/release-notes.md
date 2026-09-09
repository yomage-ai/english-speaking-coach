# v0.2.8 — System reading / 系统朗读

- 闪卡、表达详情、课次复盘及整理中的表达建议新增系统朗读，只读标准英文，不读学习者原话。
- 支持播放／停止和慢速；切换页面、关闭详情或离开页面会停止播放，连续点不同句子不会叠加。声音不可用、启动超时和播放失败会显示具体提示。
- 只用浏览器报告为本地的英语声音，无 API Key、付费 TTS、麦克风或新增练习日志。听音不改变学习状态。
- 更新中英文说明，并把朗读与页面行为测试加入正式发布检查。

Flashcards, expression details, saved reviews and pending expression suggestions now offer system speech for canonical English only. Play/stop, slow rate, cancellation and unavailable-voice feedback are included. Only browser-reported local English voices are used; no microphone, remote TTS or new practice log is added. Listening does not change learning evidence or mastery. Speech tests now gate releases alongside page and backend checks.

This release retains the standalone Go backend. It does not claim a Codex plugin or hosted Node migration.
