# PLAN029 H1887｜收 H1886 签名同VM同binary真实ABBA：直送未证明提升全程性能

- **来源**：[H1886原Windows2025签名Action43670529264](https://github.com/lly8666/wbd-next/actions/runs/43670529264)，真实`native-public-two-os` job132680622163，SOURCE `3391b9a26897f4e56467c84a9e40c0cd6ebbfa56`，全Action SUCCESS。原Go/Npcap签名Wintun/Rust Normal CN selective FakeIP + WSL2 Linux真实TUN/内核socket，**同一VM、同一原 Rust二进制、同一代际Wintun**。Linux物理TCP共5次、其中Windows原应用4条独立真实FakeIP Direct流，4MiB/每条、原始SHA/半关闭均PASS。Rust原接入记录`PLAN029_H1884_ABBA_ADMITTED`四条依次验证copy→bypass→bypass→copy，签名原 Go owner Stop后复核，`rust_admission_verified=true`、`PASS_BOTH_OWNED`、完整Python进程rc=0。
- 真同VM值（ms）：A1旧队列复制84.079；B1 scratch→kernel直送71.915；B2直送93.357；A2旧队列复制72.195。**旧复制平均78.137，直送平均82.636，B−A=+4.499ms（B慢5.76%）**。只表示这一组短4MiB样本；不能因单一ABBA断言新代码必然更差，也不能再援引H1882 2.453x与H1877 2.787x（跨VM）证明直送有收益。
- 阶段拆分更加关键：A与B平均回传**30.314→27.390ms**（B少2.924ms），但上传**34.282→38.878ms**（B多4.597ms），建连均值9.702→12.872ms（B多3.170ms），这三项已经能覆盖全程差值。TCP首流/建连噪声显著，H1885前一失败Action的A1=171.766ms/A2=88.612ms，83ms同算法漂移恰好提醒不可信的简单平均；失败记录必须保留。H1886本次真实物理基线37.979ms，B1 Direct71.915ms/物理1.894x，仍不是“旧/新二进制”对照。
- Tunnel小UDP与四条Direct同时执行：双OS各120/120唯一交付、Windows p99 RTT2.101ms、最大回包gap16.65ms，全时段覆盖确认。原始两端owned Stop和恢复PASS。本A/B没有用户态/内核态CPU或driver CPU归因、没有队列年龄/信号统计、没有真实Wintun128空闲＋少量活跃；P2性能仍OPEN，P1旧V4/V3 all-Tunnel CPU/GiB +9.41%另行OPEN。
- 后续**不继续微调拷贝分支**；优先记录原Rust TX中两条内核TCP腿的就绪通知、读写尝试/阻塞、短写、ready ticket最老等待、backpressure/内核CPU，低频有界且不泄露payload，不改变业务调度；并安排真正128条Wintun原流真实idle/active签名场景与owned Stop。Game4 CN、GUI真Connect/Stop、带真实IPv6 socket/D1–D5资源满依旧未闭环，PLAN029维持IN_PROGRESS、028/030未扩范围。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1887 collect exact H1886 signed source-locked original Wintun four-flow same-binary ABBA: functional PASS, bypass 5.76% slower in one run and no supported P2 performance gain, retain prior FAIL and remaining exits."}
```
