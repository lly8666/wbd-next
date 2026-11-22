# PLAN029/H2313 · 真 NPF 队列形状：TX16 凑满却两组相反，2026-11-22

原始源 `93702d5a4558ca0d37f053cd02140b74713adc1e`、真实 [Action 45031290436](https://github.com/lly8666/wbd-next/actions/runs/45031290436) **9/9 Jobs SUCCESS**；两套独立 Windows2025 原 signed Npcap/Wintun→ARM relay→ARM 原 GoTLS/Rust AF_PACKET/TUN 三runner，每套 `A TX8/NPF64KiB → B TX16/NPF64KiB → A′ TX8/NPF64KiB`，逐腿冷 TLS/完整真实 ARM TCP 接收和160小TCP echo/owned Stop。NPF same queue 容量16p/64KiB，全 6 腿队列 `queue_short_calls=0`，完整 copied_prefix；不等于 peer receipt。

| 组 | A Mbps | B Mbps | A′ Mbps | B对两端基线均值 | B CPU s/GiB | A/A′ CPU s/GiB |
|---|---:|---:|---:|---:|---:|---:|
|a|148.922|123.464|151.814|**-17.892%**|49.0944|36.6804 / 35.7852|
|b|137.416|198.789|132.045|**+47.546%**|27.5149|44.2448 / 43.4216|

原 NPF stop 同步直方图 **真实 driver 调用，而非伪队列变量**：a B `queue_16=21090 / queue_calls=21186` = **99.5469%**；b B `33794/34004` = **99.3824%**。所有 A/A′ 几乎都是恰8帧；B 的每次 send queue 大部分凑满16帧。a B direct calls 186（其中 ≤256B 185），a A/A′分别193/150；上一次 H2312 group a B 特有的 `9372` 次 direct 调用 **这次没出现**，不可把它判为稳定原因。b B direct 532，其 ≤256B 414，>256B 118。大小桶本身**不能准确当作 FEC/ACK/业务协议分类**。

组a候选下降**-17.892%**且 CPU/GiB **+35.497%**；组b候选上涨**+47.546%**且 CPU/GiB **-37.228%**。批次容量能用满、底层 driver copied prefix 完整，但吞吐提升不稳定，说明不能继续简单加大批次。下一步应固定真正 independent physical direct+relay 容量，分 sender pacing/inner TCP cwnd、平台 kernel/user 时、一次批次两端资源及一帧公网时间占比；绝不将两个不同 group 的 A 绝对值误归为同链路归因。

判定：**FUNCTIONAL_SAME_SOURCE_PASS / NPF_BATCH_SHAPE_PROVED / PERFORMANCE_QUALIFICATION_NO**；真实 WBD 600–800Mbps 未达，不能默认晋级 TX16。P1机会修复、P2最高档 FEC 由不同 SOURCE 独立资格。
