# GOV-001：公开发布与首轮核验

仓库已公开建立：`https://github.com/lly8666/wbd-next`。唯一被测源码 `b8effd936d386fa90b189e773e24d77616b94363`。

Actions `38431203189` / attempt 1 完成，34 项测试全部通过。下载 artifact `11830409659`，核 archive digest 与 manifest 五个文件的 size/SHA-256，0 mismatch。receipt 的初始 `artifact_verified=false` 表示 CI 不能自行证明外部核验，独立核验结果另存 `docs/evidence/M0/GOV-001-push.json`。

现场 continuity 为 RECOVERY_REQUIRED，因为首次提交没有 checkpoint；不是测试失败，也未改成 CLEAN 掩盖缺口。接下来推 H 后再观察。

main 已启用 Governance required check、线性历史、禁止 force push/删除；管理员 bypass 保留（单维护者初始化需要），不宣称同账号多 agent 获得安全隔离。共享用户名下仍必须遵守单写入者规则。

新增 `M0-gov-001` intent，固定 qualification ref 指向上述源码 S；请求保存在较新的 I，并通过 request_ref 传入。用于实际演练请求与源码分离、结果认领与收口，不是产品性能测试。先查询已有 run，再触发一次。

产品、物理、真实 fresh-chat 演练仍 NOT_RUN；M1–M4 未分配产品任务。旧仓库没有修改。
