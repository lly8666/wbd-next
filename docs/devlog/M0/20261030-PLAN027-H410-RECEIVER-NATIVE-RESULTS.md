# PLAN027 H410｜H407 接收闭合质量窗口原生回归回收

2026-10-30。精确 SOURCE `361265256d58d18ea0b36badf04668c16fb19e1c` 的 [native Action40962693585](https://github.com/lly8666/wbd-next/actions/runs/40962693585) SUCCESS：recovery 94/94、engine 136/136（1项既有可选 ignored）、receipt 11/11、kernel 6/6、fec 3/3、normal 3/3；新增三项 RX CLOSE 反例和一项 Health+Quality→summary→TX 匹配全部实际执行。统一 release 编译产物 manifest sha256 `0f67c41e1f8b719f08b6302eb0220ceda19444c699f091416f29505950b5a3c0`，build zip、binary、test log、artifact digest 见 [H410 evidence](../../evidence/M0/PLAN027-H410-RECEIVER-QUALITY-SOURCE-NATIVE-RESULTS-20261030.json)。同源 [ABI40962693614](https://github.com/lly8666/wbd-next/actions/runs/40962693614) 和 [cross ABI40962693789](https://github.com/lly8666/wbd-next/actions/runs/40962693789) SUCCESS。

同源 [Linux Auto/Health40962693776](https://github.com/lly8666/wbd-next/actions/runs/40962693776) SUCCESS，但仍为旧逐 record M2 生产路径；1% netem offered512/首到508/缺4，双 Stop，不能转作新 Quality 验收。[Windows owner40962693602](https://github.com/lly8666/wbd-next/actions/runs/40962693602) 在本次回收时仍在途。H407/H408 两次治理失败保留，H409 [治理40963036802](https://github.com/lly8666/wbd-next/actions/runs/40963036802) SUCCESS。

PLAN027 §0：①PARTIAL（纯接收链 PASS，双端线上 M2 仍 LIVE），②A NOT_RUN，③B OPEN，④C NOT_RUN，⑤OPEN。未取得新机制真实业务 p99/CPU/RSS/drop/网络容量；下一步先回收 Windows，再接双端生产调用/能力门/机会修复并退役 M2，后 A→B→C。

```feature-impact
{"kind":"none","ids":[],"reason":"Exact-source Action/artifact collection only; no product code, feature defaults, config or behavior changed."}
```
