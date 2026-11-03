# PLAN028 H1068｜标准 TLS 首轮 CI 失败的源锁与单测接线修复

H1067 真实 SOURCE `00fdb00d0e60f6a8c4d6b052f0561674885e9232` 已移除 H1048 的 `WB-R1` 入口/文件、强制32B 离线密钥与证书校验，当前仍**没有获得外观通过资格**。首轮 H1067 下发的大部分 CI 的失败来自测试装配遗留引用，而非真实 TLS 经过抓包发现非标准报文。

- 新定向 Linux/x86 原 Go TLS/网测 [Action 41688220163](https://github.com/lly8666/wbd-next/actions/runs/41688220163) **FAIL**：manifest 原 Go source 锁已正确装配、Rust release 编译通过，实际 Go `go test` 编译因为旧 donor 单元测试仍使用历史 `faketcp.DefaultMSS`，并且夹具 `glob(*.go)` 不加判断把不相关 `bridge_v4_embedded_linux_test.go` 带进了当前 tags、缺 `v4RawCheckSum`。现在仅把需要的 TLS 负面测试编进该定向 Action，调用既有 `m0_prepare_original_go_mss_test_fixtures.py` 的**仅测试常量**迁移，不扩大 tag 或制造 helper。
- 原 Windows source-lane [Action 41688220149](https://github.com/lly8666/wbd-next/actions/runs/41688220149) 的 Windows Go test compile 同时指出新增负面测试 `Authenticate` 写错到 `ServerAdmissionConfig`，实际接口是 `V4ServerOptions`；修复测试单文件并同步 exact manifest result_blob。该 Action 的 cheap/source preflight SUCCESS，Windows/Linux Rust 相关单测 SUCCESS，不能假称整 Action 成功。
- 治理 [41688220339](https://github.com/lly8666/wbd-next/actions/runs/41688220339) 的 Governance PASS、Feature Catalog FAIL 来自功能卡 code_refs 指向被禁止并删除的 `v4_route_prelude.go`；从卡删除旧源码引用，历史文档保留 H1048 失败事实。
- `r0-v4-tls.yml`、`r0-v4-cold-native.yml`、`tools/r0_go_control_patch.py` 及旧 Normal/Windows Rust fixture 仍硬拷旧 prelude 或未复制带 `RootCAs` 的原 `tls.go`；本次全部同步到新的公共冷 TLS source，不恢复旧私有前导。历史旧包的 Rust parser tests 证据保留旧 scope，不冒称现在标准握手资格。

H1067 的 Windows 原 Go 5/5 preREADY 通知单元 [Action 41688220362](https://github.com/lly8666/wbd-next/actions/runs/41688220362) SUCCESS；PLAN026 Linux自动Health [41688220155](https://github.com/lly8666/wbd-next/actions/runs/41688220155) SUCCESS；这些非握手外观证据另记，不覆盖当前 TLS 外观 NOT_RUN。老 PLAN012 大矩阵因 `[tls-cold-only]` SKIPPED，符合不重复刷弱网/CPU要求。

原生 TCP reassembly/ClientHello-first、服务端提前载荷缺席、SessionID长度/变化、wrong-key/pass/cert、真 Rust业务仍待新 Action。Linux 这完整测试工作包仍是 x86_64+ x86_64，下一 Linux 工作包必须原生 ARM64 双端；Windows不占轮换。
```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1068 exact source graph cleanup after H1067 compile-only failures: no deleted WB-R1 references, target Go tests corrected, original tls.go installed in existing workflow; native TLS wire remains NOT_RUN until exact Action."}
```
