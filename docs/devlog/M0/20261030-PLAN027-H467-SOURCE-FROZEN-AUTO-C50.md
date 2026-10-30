# PLAN027 H467｜一份修复产物，独立Auto复验与C50严格升级

H466原始Linux Rust M1合法50ms过期ready批次直接INVALID，导致7个已封装parity与可能的M2控制草稿不被NotSent结算；修复只允许空batch走原完成路径，不伪造copy/新PN。H466 actual source a61 CI build Action41002998813尚在途，H467只允许该workflow_run真实源和main对应事件，在同run确实存在Windows与Linux签名/源码产物时派发一次Auto 10Mbps/25ms/0% 60s独立Windows↔WSL2实测（不是repeat旧二进制）。

C10原H464 Action41000374541 artifact12952983950真实Normal双向1.0 first、9.9974/10Mbps、Stop BOTH PASS。C50 fanout要求上份C10真实report以及H466新源full workflow的Normal短时双向Stop PASS，再重用H466真正source二进制独立C50 60s。两条dispatch各一Windows VM，互不共享进程或测量统计；任何真实fail都不伪称容量达标。H466 Normal若不可证实，则C50不发；避免无依据大矩阵。

A4自动120s、A5 CPU A/B、B完整生命周期、C100-200/5min/损耗场景均仍未完成，不扩大旧证据范畴。

```feature-impact
{"kind":"none","ids":[],"reason":"One-shot pinned product-source test dispatches; no runtime protocol change."}
```
