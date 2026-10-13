# GOV-001：公开治理骨架

类型：G1，用户明确授权创建新公开仓库与治理结构。产品方案尚未授权定稿。

发布 intent：依据用户授权，创建公开仓库 `lly8666/wbd-next` 并推送此治理骨架；不改旧仓库、不启动产品开发。自动 push CI 由提交事件标识；只有手动测试请求使用独立 request 文件。

## 做了什么

- 审阅 longcycle-core 的固定角色、主线 reservation、分支 cursor、S/H、远端事实优先与按需历史机制。
- 新增轻量 project/registry/cursor、固定提示词、Actions 请求/证据身份、恢复与上下文预算检查。
- 编写自动反例演练：漏 H、change-then-revert、错误 epoch、越界写入、伪通过、重复请求与配置不一致等。
- 代码为独立编写的 Python 标准库治理工具，不移植 Longcycle 业务代码或数据。

## 范围

只涉及本新仓库；旧 wobuzhidao 和 longcycle-core 不修改。M1–M4 是候选职责，未激活产品开发。

## 验证

初始提交时 `NOT_RUN`。所有执行检查在本仓库 GitHub Actions。以精确 run/source 的后续 receipt 与核验记录为准，本文不是 PASS 证据。

## 下一步

推送初始 S → 运行治理 CI → 修复真实失败 → 记录结果 → H 确认远端 → 等待具体产品方案讨论。
