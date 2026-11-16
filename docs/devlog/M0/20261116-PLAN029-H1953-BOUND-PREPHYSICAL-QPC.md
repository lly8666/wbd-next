# PLAN029 H1953｜首次物理发包前：真实接纳、建连、首读三段 QPC

## 既有原生结果（不重发）
H1949 [原 Action43782426660](https://github.com/lly8666/wbd-next/actions/runs/43782426660) 的 SOURCE `e1cb1d6c8c2919e2a946e262f3c24ee475138036` 已真 PASS_SCOPED：Windows/WSL2 原 Linux TCP、4MiB SHA/FIN、Tunnel UDP120/120、owned Stop。384条 Direct 小 TCP 同 Windows QPC：FIN-first app FIN→Rust 首次物理 write p99 **14.546ms**，物理 write→read **1.829ms**，物理 read→inner.write **0.210ms**，inner.write→app首recv **0.537ms**；payload-first **5.889/1.400/0.119/0.430ms**。4MiB物理 60.209ms、Direct117.515ms；优化未合格。

## 本次两个独立场景（并行、各自 SOURCE）
- H1952 source `eb5743986191a9102dda7e0aa085c7b198d0a123` 的 CN DATA `FlowPin` 冗余 hash get 改为复用已有 first-prior，**原同VM All/CN/CN/All P1** 已在 [Action43785063606](https://github.com/lly8666/wbd-next/actions/runs/43785063606) 在途。本 H1953 commit **不含 P1 标记**，不派发旧 P1。
- 本 H1953 仅单次 **原 Windows/WSL2 P2**，原 source-locked 4MiB + 两种各384 Linux TCP echo/FIN + 120 Tunnel UDP + 双端 Stop；在 H1948 QPC 上新增**真实 kernel listener accept**、**真实 physical socket connect success**、**首次真实 inner WinSock recv success**三枚每flow QPC。记录接受的 TCP 5tuple 源端口只在 Stop 输出（最多1024），不输出 IP/负载/凭据，不新增 packet/flow 日志、线程、网络 I/O、poll 或 timeout。正常路径显式闸门关闭，三个 timestamp 不调用 QPC（仅两个 i64 零值 flow 元数据）。
- 新严格校验器在 SAME Windows VM QPC，要求与 H1948 physical.write→physical.read→inner.write 的原日志逐流一致；两策略各192真实Direct、共384/384。若任何事件缺失/顺序不对/频率不同、SOURCE不等、错误端口复用则 FAIL。client FIN→accept **允许负差**，因为 OS TCP accept 可能早于客户端半关闭；不得把负差截0或把跨 Windows/Linux 时钟做差。
- 这只能定位 prewrite 区段在 listener accept 之前、物理 connect、connected→inner read、或 inner read→physical write 哪段长；真实 p99 修复以及 D1–D5/P1 CPU/Game4/GUI/IPv6/padding/资源压力全部仍 OPEN。无新 SOURCE 原生回执前不写性能 PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1953 original Win32 signed-only physical prewrite accept/connect/inner.recv timestamp and strict H1948 384-flow join; independently preserve H1952 true P1 Action, no duplicate dispatch."}
```
