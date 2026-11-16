# PLAN029 H1952｜H1949 真原生 QPC 已收；CN 热包 FlowPin 单次查表 P1

## 已收真实 SOURCE
- 原 Windows/WSL2 [Action43782426660](https://github.com/lly8666/wbd-next/actions/runs/43782426660) 结论 success，SOURCE `e1cb1d6c8c2919e2a946e262f3c24ee475138036`，原 4MiB SHA/FIN/Tunnel UDP120/120、双端 owned Stop PASS_SCOPED。物理 60.209ms；FakeIP Direct 117.515ms（1.952×），主要附加上传 47.204ms、下载 31.656ms，不能当满速性能 PASS。
- **同 Windows QPC 384/384 匹配**，两种原 Linux echo 顺序各192个 Direct：FIN-first client FIN→首次 Rust **真实物理 socket write** p99 14.546ms；物理 write→首次物理 recv p99 1.829ms；物理 recv→内层 kernel write p99 0.210ms；inner.write→Windows app首recv p99 0.537ms。payload-first 相应 5.889/1.400/0.119/0.430ms。H1949 额外2个 bulk 时间戳所以原 Rust 共386行，解析器严格只用384个真实小 TCP app 对齐。
- **首到根因仍 OPEN，但大部分长尾定位在首次物理写之前**，该区间涵盖 app/Wintun SYN、NAT、listener accept、physical connect、已缓冲请求读入与事件调度；跨 OS 时钟没有混算。不再把问题推给 Linux echo 或 Rust 回包注入。
- H1947 已存在同 Rust All/CN/CN/All 原 P1：CN4104、业务与Stop四次 PASS_SCOPED，但 CN Windows Go+Rust CPU/实际GiB 比 All +11.942%，B两臂自身10.17%波动，**性能未验过/OPEN**。

## 本 SOURCE 独立 P1 假设
- CN/DATA 原先在同一包决策中 `prior=self.pins.get(&key)` 后又 `self.pins.get(&key)`；中间没有改同一 flow pin。现在复用 first prior，已固定的 FakeIP Direct 仍优先，只有真正新流调用 `FlowPin::first`，同时补 128次旧Fake Direct复用、Tunnel压力不干扰、Direct硬限与未知FakeIP拒绝回归单测。**不变更出口语义/协议/线程/内存上限**。
- 本 SOURCE 仅一个新的原 Win2025/WSL2 All→CN→CN→All P1，源锁 Rust V3、50Mbps业务、真实Stop及4104 CN规则；独立于即将开展的 P2 prewrite QPC。无结果前不能宣称 CPU 优化达标或跳过 P1 漂移。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect H1949 genuine first physical write/read Windows QPC 384/384, 4MiB/Tunnel UDP/Stop; eliminate one duplicated CN packet FlowPin hash lookup, native P1 causal qualification pending."}
```
