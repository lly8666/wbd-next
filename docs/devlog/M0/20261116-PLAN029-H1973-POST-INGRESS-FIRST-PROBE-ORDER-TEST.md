# PLAN029 H1973｜修正新顺序测试误判，不改交付逻辑

H1972 SOURCE `af5c7f88f17fa2b398065c7eddce21ca8472c8a8`，[廉价 Action43808305797](https://github.com/lly8666/wbd-next/actions/runs/43808305797) `test_m0_plan029_h1972_post_ingress` 5例中4例PASS。仅`test_original_wintun_rx_ownership_and_signed_only`断言失败，因测试把`let mut fresh_direct_ingress=false`的**变量声明**误作业务`stage_sources`读包开始；真实的旧Direct reverse队列仍在声明之后、读取真实Wintun包之前优先送往原RX，因此业务优先级符合预期。

H1973只将测试的基准位置从变量声明改为**首次真正`stage_sources(...)`调用**。保持旧32条reverse先处理、新签名8条post-ingress次之、全部`try_send`非阻塞、满邮箱TCP FIFO requeue、单一RX Wintun写者、普通产品OFF。原QPC 2048条、SHA/FIN/Stop联动完全不变。

H1972 Linux Rust纯组件原码PASS；Windows Rust独立编译等原Action收齐后再做一次同SOURCE原生实测。H1970旧真实基线，NAT→inner read 34.4μs/59.8μs，innerWrite→app 47.9μs/75.1μs（p50/p99）不变。没有新实网性能声明。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct only source-order static regression to compare original reverse drain before actual stage_sources call; no socket/runtime/feature behavior changed."}
```
