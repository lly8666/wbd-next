# PLAN027 H411｜回收 Windows 旧 M2 owner 与 H410 治理修复

2026-10-30。精确 SOURCE `361265256d58d18ea0b36badf04668c16fb19e1c` [Windows owner Action40962693602](https://github.com/lly8666/wbd-next/actions/runs/40962693602) SUCCESS：Windows MSVC Rust DLL + 原 Go TLS 签名 Wintun 真正双向 kernel UDP、AEAD/PN、重放/篡改拒绝、same-generation Hold/Quiesce/Stop；Go Windows client/server 原生编译。精确 DLL/client/server sha256、artifact/receipt/log hash 见 [H411 evidence](../../evidence/M0/PLAN027-H411-WINDOWS-OLD-M2-OWNER-AND-GOVERNANCE-20261030.json)。此验证**仍是旧逐 record M2**，非新 Quality/ACK/SACK 线上验收；host-global WFP/route/GUI Applied 均 NOT_RUN。

H410 [治理40963709657](https://github.com/lly8666/wbd-next/actions/runs/40963709657) FAIL：cursor.last_tested_source 改为 H407，却仍保留 PLAN026 不同 SOURCE 的 evidence_ref；校验必须逐引用同源。H411 将 cursor.evidence_refs 仅保留 H407 SOURCE 的 H410/H411；旧 PLAN026 证据文件原样保留，失败记录不删除。无产品行为修改。

PLAN027 ①仍 PARTIAL；②A NOT_RUN；③B OPEN；④C NOT_RUN；⑤OPEN。下一步接 Windows/Linux live Quality/Auto/ACK 与 M2 退役，随后 A/B/C；不重复同源 native 已通过项。

```feature-impact
{"kind":"none","ids":[],"reason":"Collect exact Windows owner Action and correct cursor evidence SOURCE references; no product code or feature behavior changed."}
```
