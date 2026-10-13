# GOV-001：治理验收完成，产品规划待讨论

## 结果

公开仓库 `lly8666/wbd-next` 可用。参考 Longcycle 的持久角色、main reservation / worker cursor、S/H 与按需历史，建立独立的轻量治理层；未复制其业务实现，也未修改旧仓库。

正式工具源码仍是 `b8effd936d386fa90b189e773e24d77616b94363`。自动 push run `38431203189` 与真实手动请求 run `38431615407` 均通过 34 项演练。后者实际从 tag S 执行、从独立提交 I 读取 intent，排除了请求/源码自引用。

两份 artifact 均已下载：archive digest、manifest 文件 size/hash、SOURCE、配置、run/attempt 与 GitHub success 逐项核过，0 mismatch。证据在 `docs/evidence/M0/GOV-001-push.json` 与 `GOV-001-manual.json`。原始包仅数 KiB，无大抓包或业务数据。

## 实际接续观测

- 初次无 checkpoint 时返回 RECOVERY_REQUIRED，不冒充 CLEAN。
- 推 H 后准确指向已核对的实质提交。
- 手动测试进行时，live audit 找到 request 对应的实际 run `38431615407`，返回 READ_EXISTING_RUN；没有把没登记结果当成应重复 dispatch。
- 本提交登记已核验结果、关闭请求；下一次 cursor-only H 确认本提交。之后的 Actions continuity 输出应为 CLEAN。该观察会留在 Actions artifact；不为了把最终 H 的结果再写回同一个 H 而制造无限收据提交。

## 已知边界

真实“全新聊天独立接手”演练没有运行；自动模拟与真实 API 请求成功不替代它。没有产品代码、性能资格或物理测试。

main 有 required Governance、线性历史和禁止 force push/删除，管理员 bypass 保留且本次初始化确实使用了它。角色 epoch 与路径契约不是同账号之间的安全隔离；继续依靠单写入者和远端刷新。

检查器会拒绝当前引用缺失，但不证明所有被归档历史的语义都完整；历史整理仍须看 diff。API 查询与上下文都有上界，超限明确停止猜测，由接手者分段核对，不退回全库阅读。

## 下一步

GOV-001 到此收口。M0 等待与用户讨论具体 Rust 架构、模块接口、旧功能迁移清单、指标与阶段计划；M1–M4 继续 reserved。使用固定提示词接手，不把旧开发年表或已有实现数值自动升级成新项目硬门。
