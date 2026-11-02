# PLAN027 H906｜旧真实工件补定量，不擅自把 packet 乘数写成 wire 字节

- H900 [原始 Game4-FEC6 OFF 双 OS Action41407246598](https://github.com/lly8666/wbd-next/actions/runs/41407246598)，SOURCE `f3f4c86f...`，artifact `13123903909` 已下载并核内部 `mode-results/game4-fec/{client,server}.log` 和双方 `wl-n0-*-app.json`。真实同源单调钟 UDP **RTT p99** Windows发起578.000ms (549/549)、Linux发起588.233ms (600/600)，均无2s超时；跨 OS **one-way p99 NOT_MEASURED**。与此前真实双方向首到1.000000/.999973及Stop PASS相容。不可将 RTT/2冒充单程延迟。
- Linux游戏服务端 Rust实际 **source_offered=74882 records, parity_offered=100230 records, first_lane_copied=700281 records, recovered_candidate=683, expired=2, failed=102, at Stop retained_bytes=0**。四lane各自原密文/PN，首发lane总记录数/业务 source 数 **9.35179×（包计数放大，非字节放大）**；parity/source=1.33851。完整 F/C 实际 wire bytes、本端与彼端每层密文长度尚未计量。10Mbps业务若保持这种 lane/最高FEC开销，20Mbps业务理论会迫近约两倍首发操作，是否实用必须看新源真实 underlay/CPU/队列，而不是无前提外推 PASS。
- H884 [same Windows VM OFF→ON Action41395887599](https://github.com/lly8666/wbd-next/actions/runs/41395887599)：30% random kernel loss，Normal 10Mbps/dir 250ms，OFF CPU4.0625s、ON CPU3.7031s，`ΔCPU=−0.3594s`，同时双向首到 OFF约70.1%/70.3% → ON约72.5%/72.4%，真实 tc both directions drop>0，真实双端 owned Stop。ON F=86,376,838B，R=7,616,208B，C=150,863B；R/F=8.8174%，R/total=8.0900%，保留不确定驱动计量规则。绝不由单个负delta证明总性能优化；旧H880 ON异常+21.2187s已在H884当前修订未复现，当前不再盲重赛。H876 0% CPU ON−OFF仅+0.0157s，控制成本不显著。
- H905 newer source `9816f7...` 修复 Windows native dead6真实Stop 状态；在本归档时 [native Action41412666449](https://github.com/lly8666/wbd-next/actions/runs/41412666449) 尚未给出产品结论。Windows Rust lib **278 PASS**包含两个新的post-join实际导出Stop回归，Linux Rust/Windows Go 编译通过仅是预检。历史source不跨源提升H905的原生恢复。

```feature-impact
{"kind":"none","ids":[],"reason":"Archive previously incomplete exact real signed Action source-specific RTT, FEC lane-count and same-runner CPU/FRC evidence; no product or fixture changes."}
```
