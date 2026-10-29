# PLAN027 H404｜回收 H401 预检与 Quality START/CLOSE wire

2026-10-30。重新读取 main prompt、AGENTS、PROJECT_CHARTER、registry.goal、cursor、PLAN027；checkpoint b34a568d 后仅 H403 3355950b 新提交，已核 diff，未重做旧 native。

**recovered**：H401 [Action40946233322](https://github.com/lly8666/wbd-next/actions/runs/40946233322) 已 SUCCESS；Windows Go compile、Windows/Linux Rust unit、Go+Linux peer compile、签名 Npcap/Wintun+WSL2 public two-OS job 均 SUCCESS，旧 SOURCE c8dad610。job/产物 ID 在 [H404 evidence](../../evidence/M0/PLAN027-H404-RECOVERED-PREFLIGHT-20261030.json)。这仍是线上 M2 旧路径，非 PLAN027 A/B/C 或新 SOURCE。

**候选实现**：`v4_native_health` 加 32B 严格 v3 START/CLOSE 窗口控制，携带 id/PN 范围/首发 F/完整与容量标志，复用 AEAD kind1 Health+LegacyQuality、MTU 限额和 idle hint；畸形 v2/v3 不再退化为 opaque Quality。新增单元反例覆盖双边界、无 Receipt、idle、MTU、保留位、错误事件/计数/长度。**此代码尚未接入 Windows/Linux live owner，也未完成能力门或 M2 退役；新 SOURCE 待 Actions 结果。**

PLAN027 §0: ①PARTIAL（双端线上 M2 仍 LIVE），②A NOT_RUN，③B OPEN，④C NOT_RUN，⑤OPEN。继续先完成产品接线，再 A→B→C→长测/结果修复；不跨 SOURCE 冒认旧 PASS。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Document strict encrypted Quality START/CLOSE wire candidate, preserving live Auto and M2 retirement as NOT_RUN."}
```
