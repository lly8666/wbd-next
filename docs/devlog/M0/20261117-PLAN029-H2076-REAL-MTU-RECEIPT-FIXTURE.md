# PLAN029 H2076｜原产品第二代 Health/OS 真通过，验收夹具误用单代 OS 回执

[GUI Action44032936928](https://github.com/lly8666/wbd-next/actions/runs/44032936928) ZIP14306122644、[域名 Action44034346200](https://github.com/lly8666/wbd-next/actions/runs/44034346200) ZIP14307200911、[TTL Action44034352986](https://github.com/lly8666/wbd-next/actions/runs/44034352986) ZIP14306961543 均为 **SOURCE `498a5a61a8e8eff1d8263529457f1523f3b21ff7` 真 Windows2025签名Wintun/Npcap↔WSL2**：三条记录各有两次真 Windows OS Applied/Ready、outer1460/inner1389 两份数值回执；服务器 `V4_PUBLIC_NORMAL_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX generation=2 verified_client_cold_health=1`，B路由/旧A精确退役/最后shared-TUN Stop；TTL 三阶段 `198.18.0.1` 均真实回。**H2072的产品 Health 修复已由三条原始 native 证据证明**，但完整 TCP/UDP business 阶段未到，原 Action 结论保持 **FAIL**。

新的共同**首个异常属于夹具**：`tools/m0_wl_public_normal_e2e.py` 在 `p029_gui_reconnect` 场使用 `verified_native_windows_inner_mtu(winlog,...)`，而这个原封不动的单代校验器必须恰好1条。实际两独立 WinForms Go 子进程各有1条、共2条；PLAN028双代有特殊分支，PLAN029没复用，于是三个场景在 TCP/UDP 断言前抛 `missing/duplicate live Windows numeric OS MTU receipt`。这不是 OS 未应用，也不是 B Health 未验证。

H2076 **只改测试夹具**：新增独立两代 helper 检验恰好两条完整数值 receipt，每条仍调用旧严格单代 verifier，支持普通 Windows CRLF；`p029_gui_reconnect` 与旧 PLAN028 双代按场景单独写 report。原 `verified_native_windows_inner_mtu` 不放宽，单代旧模式行为不变；新增纯单测覆盖一条/三条/伪造行、MTU 不匹配和 CRLF。

不重编 Go/Rust产品：沿现有 `wiring-contract` H2062 三场 coordinator，只为 `[plan029-h2076-fixture-reuse]` 指定真实 H2075 已上传 binary SOURCE `498a5a61a8e8eff1d8263529457f1523f3b21ff7` / run44032936928，下一 fixture SOURCE 与 product SOURCE 单独记录。三 Action 分场、各有真实 Windows/WSL2/owned Stop，晚于本次提交才收结果；不重复 H2070 RAW 诊断、不启动旧高负载矩阵。仍需完整 Direct/Tunnel TCP/UDP + 域名 TC TCP53 + TTL3 + GUI Stop 才能收日常范围。

```feature-impact
{"kind":"none","ids":[],"reason":"H2076 strictly fixes signed native E2E test-only double-generation OS receipt fixture and reuse coordinator, no product code/feature semantics changed"}
```
