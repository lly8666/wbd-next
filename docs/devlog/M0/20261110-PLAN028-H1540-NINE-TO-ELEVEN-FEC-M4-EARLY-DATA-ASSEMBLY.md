# PLAN028 H1540｜修正确有产物的 64/65 条 FakeTCP 原生装配遗漏

- [H1531 原始 loss30](https://github.com/lly8666/wbd-next/actions/runs/42788212678) 原生 server log/client log ZIP13749983094：真实外层303.027 Mbps，原生六进程Stop，Dave Game4 lane3 TCP源59341、lane4源50881在 **受保护 TLS reply→原生 M4 Detach 前** 正常 DATA 排队第65包爆满，原 Go `StageTransition.Route`将 `TransitionPrepared`（2）置为 `TransitionAborted`（3），受保护 admission `protected_reply_detach`失败。客户端仅本地热Ready5而服务端真实commit3，**是真FAIL**。
- 把源文件对照后发现：`r0/go_overlay/internal/faketcp/transition.go` 于旧H1285早已按合理边界修好——64项硬上限、超额纯丢且**不 ACK**，保留已认证候选/队列；冲突payload、跨TLS边界、超wire限制仍强制Abort。原始 Linux/ARM64构建统一走`tools/m0_install_public_faketcp.py`，仅安装7个源锁文件，**漏了已有正确的 transition.go、transition_test.go及H1285两项正反例**。所以本场原生 Go 仍调用 `wobuzhidao@a7a82` 的旧Abort逻辑。
- 修复只把这4个**已有** `manifest-plan020-m0.json` 原始哈希/结果哈希验证的 overlay 文件装入原始 Go checkout：4 REPLACE中新增2、3 CREATE中新增2，精确总数11，不改 existing transition.go、Rust、ABI/TLS/record/MTU/稳态；Go cold M4 早到数据上限仍64。新增强制静态源锁单测和真实 Go `go test -v` 执行 `TestPLAN028PreDetachBurstOverflowPreservesAuthenticatedSuccessor` / `TestPLAN028PreDetachMalformedRecordStillAborts`。
- 后继定向 [H1540](https://github.com/lly8666/wbd-next/actions) 在**一个独立 Ubuntu x86 VM** 重新编译原Go两端（原Go immutable a7a82 + 此次源锁覆盖），保留原 Rust m0_v4 native加速libwbd_engine.so SHA256 `e8ac9668...` 与 ISA-L `c387163...`，记录不同 Go/Rust 源身份及完整二进制sha；只跑 loss30 一场600s/200ms/实际外层300–350，不重跑已通过loss0 333.930 Mbps；`--strict-band`、Game4服务端M4、六Stop不豁免。尚未收到新 Action 结果时**NOT_RUN**，绝不把老log当新源码验证。
- Windows五进程 route/WFP 所有权问题另行收口：原始源 a7a82 `native_owned_transaction.go` 将 server /32、两条捕获 /1 作为每个独立 Wintun 原子私有路由，每次 Apply 对已存在 route 拒绝；每个 WFP guard 同时阻止非自身LUID接口。无共享全局owner即不支持并存，不能删除保卫/接管外国路由；H1537 Windows业务未通过，非 app bind timeout 假错。
- PLAN028仍IN_PROGRESS，物理/Android NOT_RUN。

```feature-impact
{"kind":"none","reason":"Fix only previously intended exact original Go FakeTCP early-M4 64-record bounded-drop implementation missing from Linux/ARM64 source-locked assembly, retaining existing feature semantics and strict malformed-record guards; no new feature, wire or user option.","ids":[]}
```
