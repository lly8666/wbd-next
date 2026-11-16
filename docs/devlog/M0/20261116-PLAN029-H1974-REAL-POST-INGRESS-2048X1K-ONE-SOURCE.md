# PLAN029 H1974｜一轮真实Windows/WSL2小请求同轮回送对照

## 为什么值得这一轮，不追1微秒规则
旧原SOURCE `dc2d1904ee3e487b9ac307086be189a8ba053a83` Windows2025→WSL2 2048次已建连单流1KiB真QPC：物理/Direct RTT p50 94.5/218.8μs、p99 159.2/318.0μs；Direct分流分类/NAT p99 0.6/1.1μs，**NAT入队→inner socket读到 p50 34.4μs/p99 59.8μs**，内核inner写出→原应用收到 p50 47.9μs/p99 75.1μs。优先消除前者的冗余一次TX turn；其余物理Linux echo 104.5μs既有跨OS开销不归咎Rust。

## H1974 签名单轮
- 原H1972 `af5c7f88` [Action43808305830](https://github.com/lly8666/wbd-next/actions/runs/43808305830) **Win/Linux Rust组件PASS**，但H1973 [Action43808522515](https://github.com/lly8666/wbd-next/actions/runs/43808522515) 5项合成中4项PASS，第5项误要求从源码截断段内看到英语单词`original`。H1974只修复该无意义字符串断言；保留实际旧reverse32优先→Wintun stage_sources→新可选8同轮reverse顺序、满邮箱重回TCP FIFO和单RX owner防线。
- 单commit标记 `[plan029-v3-real-p2-rebuild]` + `[plan029-v3-real-p2-steady-qpc]` + `[plan029-v3-real-p2-post-ingress-flush]`，原Windows/Go/Rust+WSL2 single SOURCE、Normal原1MiB+Tunnel96B先做功能、然后物理及Direct**32预热+2048×1KiB已建连Echo**。同一Windows QPC、Linux真Kernel TCP SHA/FIN、原owned Stop后严格分析；绝不宣称从合成单测得真实延迟。
- 源锁特性只用于签名CI，**普通产品OFF**，提前建连OFF。原TX在接收本轮Wintun packet之后最多8条新reverse直接交给**原同一个RX worker**；旧32-return优先级和256消息原FIFO通道不改，不增线程/循环。最终原Rust Stop必须有`PLAN029_H1972_POST_INGRESS_DIRECT_FINAL delivered>0 max_per_turn=8 sole_original_rx_owner=1`，否则FAIL。
- 真正决定保留/撤销的是原Windows同一个SOURCE的响应、全2048正确字节和新的`NAT入队→inner kernel read`与`inner write→app receive`大项。相对于H1970跨VM历史SOURCE若未显现至少约**20μs p50量级**改善不得声称解决大差异；即便显现，跨运行对照仍只有观察性，若推广产品默认须后续同VM无trace OFF/ON重复。若失败只按原Action日志修正，绝不偷偷降低Stop、样本或SHA门槛。
- 完整PLAN029 D1–D5/P1/P2/GUI/Game4/IPv6仍OPEN；不碰极端共享真实CDN IP。

```feature-impact
{"kind":"none","ids":[],"reason":"Trigger exactly one signed original Windows2025/WSL2 steady 2048x1KiB TCP post-ingress fast FIFO experiment with unchanged feature default, while correcting the last irrelevant synthetic string assertion."}
```
