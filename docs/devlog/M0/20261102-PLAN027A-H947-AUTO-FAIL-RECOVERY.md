# PLAN027A H947｜自动FAIL按最小根因恢复

收集H945来源 `f09395c4d38e59da8789b8d4e275a45d8691a901` governance Action `41451477835` FAIL：M0 cursor context_refs 9超出≤8；H946来源 `1151a4da7e4e86125f95bc635cc0a5ef21b8980f` governance `41452055396` 同因FAIL，原生push `41452055617` 便宜入口在Python新增回执单测FAIL、尚未构建/运行真正Win↔Linux。并未发生数据面失败或MTU默认变更。

本批将cursor上下文引用仅保留最新8个，历史原文/evidence/devlog均不删除；将H946回执正则多余反斜线和测试literal \\n 改成实际换行匹配。没有新网络dispatch，已完成H943旧SOURCE测试继续源限定保留。

```feature-impact
{"kind":"none","reason":"Correction to test fixture escaping and scoped cursor metadata after precise CI failures; no product code or MTU default change, prior path-mtu-budget feature card remains accurate."}
```
