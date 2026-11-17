# PLAN029 H2050｜真实 GUI Npcap DLL 入口和冷物理 DNS WSL 受限入站修复

- H2048真实Win2025 signed Action [43995805550](https://github.com/lly8666/wbd-next/actions/runs/43995805550) 原Go/Rust已读回 `configured_outer=1460 effective_outer=1460 inner_mtu_planned=1389`，但GUI可移植EXE工作目录缺少`wpcap.dll`，原Go FFI装载错误并没有 Applied/业务/Stop。现在只从**同一 Action 已做官方安装、精确hash/签名核对的** Npcap 1.88 `result/wl-public/wpcap.dll` 与 `Packet.dll` 拷到当前源GUI产品根，逐byte校验；没有使用PATH模糊备选。
- H2047真实Action [43995525313](https://github.com/lly8666/wbd-next/actions/runs/43995525313) `physical A query timeout`：原WSL Hyper-V唯一允许的原始物理TCP443/46112规则没有授予bootstrap开始前的UDP53。新增仅**显式**TC场景、且仅这个Linux guest / 实Win physical source、UDP53+TCP53 的独立有界规则，写INTENT再Apply，精确协议/地址/端口/Creator readback，始终通过自身名称和receipt CAS清理，不放宽默认策略。未来必需原始UDP TC/TCP receipt才可标PASS。
- 两条上一个SOURCE原生实网均FAIL，不抹掉。此提交`[plan029-real-gui-cn]`仅触发真实原WinForms场景；随后另一个SOURCE的TC场景单独触发，不叠双场。不做 IPv6/P1/P2/共享 CDN 或重复padding。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","dns-split-ipv6"],"reason":"Fix H2048 genuine WinForms original client missing signed Npcap DLL and H2047 physical DNS bootstrap WSL HyperV firewall scoped UDP53/TCP53 receipt without changing product routing."}
```
