# PLAN029B H2122｜原Go/Win/Linux Rust廉价门PASS、B4真Win在途；修正cursor实证SOURCE指向

H2121 main SOURCE `3811cb1446b7a609c3b7276ffe36aa6dbdf9e0c8` 原 [Action44135003298](https://github.com/lly8666/wbd-next/actions/runs/44135003298) 首个cheap **FAIL**：旧 `tests/test_m0_plan029_h1749_signed_direct_order.py:265` 锁定 `if p029_cdn and ...` 原始测试拥有的/32 CAS route文本；新的B4只复用该既有owner，静态测试文本失配，无真实Windows网络测试。后续源 `b1ab51be87c6d0c0aadd57283ac12da34ca238bf` 仅修改该一个静态断言，原Route CAS没改，原 [Action44135197316](https://github.com/lly8666/wbd-next/actions/runs/44135197316) cheap全部PASS（含B4四项）、Windows Go+B4实际命名单测PASS、Win/Linux Rust eligible PASS、Linux真实原source peer构建PASS；**本记录时signed Windows2025/WSL2 native job134226463265正在执行，B4真实产品结果NOT_RUN/待采样，不能宣称PASS**。

源 `b1ab51b` 主线 [治理Action44135197359](https://github.com/lly8666/wbd-next/actions/runs/44135197359) 原治理结构**FAIL** 首因 `evidence is for a different SOURCE`：H2121 cursor的 `last_tested_source` 仍为H2120真实 `224736...`，而 `evidence_refs` 错放H2121尚未真跑的 staged `PENDING_SOURCE...`，违反仓库source一致性治理约束。H2122只将 `evidence_refs` 恢复H2120真实已验Go/Win/Linux Rust纯PASS证据；H2121原B4 staged NOT_RUN仍在 `context_refs`，补实际初始候选SOURCE `3811...`，原first FAIL保留。不修改正在跑的二进制、工作流、产品、业务路由或原签名Action；此文档/治理修复不带原生触发marker，不并发重新派发。B4原生成功/失败依据原产物ZIP/SHA/CRC和完整owned Stop另行采集。

H2112 B3真发包仅/128限域PASS不扩大为全宿主IPv6禁用；Game2/Game4、B5同VM容量内CPU/交付GiB/host CPU/RSS/唤醒/TCP-UDP p99仍NOT_RUN。029/029B OPEN，030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"H2122 only corrects archived last-tested SOURCE vs staged NOT_RUN cursor references while signed H2122 original native is in progress; no runtime or test scheduling change"}
```
