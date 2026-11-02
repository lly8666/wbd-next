# PLAN027A H925｜Windows 冷接收预算、outer/inner 和原 Go/OS 生命周期继续修复

精确 code SOURCE `7d853983208b72443234f46aba013fc9a947b603`，入口 `docs/decisions/M0-PLAN027A-MTU-UNIFICATION-20261102.md`，唯一公式 `docs/architecture/MTU_CONTRACT.md`。

H924 新增 Rust 纯 receiver-bound ABI，在原始 RAW SYN MSS、完整外层 IPv4、DATA options、Game+FEC2 type1 之后再由 Rust 推导接收端 planned inner 能承受的 record offer；Windows 原始 Go TLS `ClientLimit` 消费该回执，移除 Go 重复的31/14/16/15以及硬帽1400。未添内层普通输入/未提高 LINK 声称。此 cap 是协商意图，非 OS Applied。

H925 原 Windows Rust Normal/FEC2 owner 曾把 **Wintun 预安装 inner** 传给 Rust `connection_mtu` 当 outer：新增 v5 scoped ABI，生产路径先受信任原始 TLS → 同一 signed Wintun Hold → Rust bind(配置完整 outer, planned inner)，无新 owner/stop 机制；v4 legacy ABI 对既存单测暂存。M4 仍必须五阶段 WAL/install/OS live readback 和真实首到，不把 planned inner 命名为 applied。Game group 另一入口仍待真实实测/独立接线，不能从 Normal 推广。

源码锁合并：`r0/go_overlay/assembly/manifest-plan020-m0.json` 同批刷新被改 Go blob hash，新增 Windows cold budget Go 文件；避免 CI 因旧 blob 断言假冒 source drift。Linux 旧测试错误把公开 outer=9000 当成合格，修为 device9000 但 outer1500 后受 peer MSS 限制，并对 outer9000 明确负例。H922/H923 既有 PASS/FAIL 历史保留；H924 PLAN020 Windows assembly FAIL 是 stale blob；H925 新跑暂未收齐，不能标产品 PASS。

本批目前不派发独立网络 Action；待固定 SOURCE 再做边界 native/DF/弱网，旧 027 不重跑。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"H924/H925 Linux public jumbo negative fixture and Windows original-TLS Rust receive-bound record offer remove Go hidden 1400; v5 authenticated owner distinguishes configured full outer IPv4 versus OS-planned receiving inner and retains OS Applied receipt authority. Native Game/DF/runtime still NOT_RUN."}
```
