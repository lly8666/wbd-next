# M0/PLAN029 P0 H2312 · 真实 Windows NPF 单变量 A/B/A′（2026-11-22）

## 源锁与结论

- Draft [PR #68](https://github.com/lly8666/wbd-next/pull/68)；实验 branch `experiment/m0-029-throughput-arm-fair`；**实测 compiled/product + fixture SOURCE** `a8ea2e9159f90333cdc6e7ee7f86708e142d2f46`，原 GoTLS EXE 继续核真 `c5066db61fc51bafd7c2ad2def3029e615efa777`，真实 ARM64 GoTLS/Rust 原构件有 manifest/hash 门。real [Action 45028638145](https://github.com/lly8666/wbd-next/actions/runs/45028638145)。
- 独立两组各3 runner；Win2025 signed Wintun/Npcap + GoTLS/Rust → Linux ARM relay → ARM GoTLS/Rust AF_PACKET/TUN，0ms/0% 完整原内层 4×25s TCP + 160 sparse TCP echo，三条腿各独立冷会话 + 原 owned Stop。**A TX8/NPF16KiB/8p → B TX8/NPF64KiB/16p → A′ TX8/NPF16KiB/8p**，唯一变因是 NPF queue；三个真实 Rust DLL feature manifests 都为本 SOURCE 冻结编译/核 hash，绝不将 H2292 旧二进制冒充当前业务。
- **两个真实 Win client Job 与两个真实 ARM server Job 都 SUCCESS，全部六条客户端产品腿 receipt/GoTLS/Rust/owned Stop/160 echo PASS；relay a,b Job FAIL** 是原 H2292 汇总检查仍只接受 `real_windows_npcap_64k_16_profile` = [False,True,False]，新单变量有意三腿都 False。原红保持红；后继源 `438f679385ed4e2ace2efe755f7c4ecc9250bf1e` 已将 relay 校验扩展为新模式实际 NPF 16/64 queue trace + 真实 receipt/Stop/qdisc，不取消原业务门。**该扩展尚未回判历史 Action 为绿，旧 Action 继续 FAIL**。
- 实测表：

| group | stage | receiver Mbps | TCP P99 ms | Win whole-process CPU s/actual GiB | actual ARM bulk bytes | NPF queue calls / submitted frames | queue profile |
|---|---|---:|---:|---:|---:|---:|---|
| a | A TX8/NPF16 | 116.378 | 328 | 48.9812 | 371638272 | 39901 / 319135 | 16KiB/8 |
| a | B TX8/NPF64 | 144.430 | 266 | 35.9625 | 459522048 | 49323 / 394431 | 64KiB/16 |
| a | A′ TX8/NPF16 | 134.966 | 282 | 44.6641 | 430473216 | 46204 / 369495 | 16KiB/8 |
| b | A TX8/NPF16 | 176.758 | 219 | 31.9195 | 560300032 | 60739 / 485774 | 16KiB/8 |
| b | B TX8/NPF64 | 193.775 | 219 | 28.2947 | 613105664 | 65833 / 526536 | 64KiB/16 |
| b | A′ TX8/NPF16 | 215.334 | 188 | 29.5484 | 681345024 | 73083 / 584478 | 16KiB/8 |

- B 对各同机 A/A′均值：a goodput **+14.93%**、Win CPU/GiB **−23.19%**；b goodput **−1.16%**、Win CPU/GiB **−7.94%**。**不能以 a 的单组 Mbps 或 CPU 派生因果晋级**；b A′比 A 大幅上漂，按计划算 INCONCLUSIVE/NOT_QUALIFIED for sustained improvement。
- 有效机制新事实：NPF 中真实已提交帧数 / 实际 queue call **六条腿全在 7.997–7.998**，包括 B NPF64KiB/16p；因此**扩容 NPF queue 对 TX8 满源批次几乎无法增加每调用帧数**。本次每腿 `queue_short_calls=0`，`queue_bytes_copied=queue_bytes_submitted`，不是 NPF 短前缀丢包。不能仅因为成本下降宣称内核单个调用瓶颈已解决，也不能用 NPF driver copy 冒充 peer receipt。

## 后继 / STOP 判定

- 下一步已在独立新 SOURCE `438f679385ed4e2ace2efe755f7c4ecc9250bf1e` [Action 45029306636](https://github.com/lly8666/wbd-next/actions/runs/45029306636) 复用**同一 H2292 夹具**启动 P0 第二单变量：A TX8/NPF64 → B TX16/NPF64 → A′ TX8/NPF64；NpF不变、TX batch 才变化。真实交付/CPU/NPF queue frames/call/P99 应同步对照。同样若环境异动或物理容量不足，以真实资格记录，勿造假合格。
- **没有合入生产**，所有实验 compile-time feature opt-in；P1机会修复和P2 fixed maximum 尚未开工。P0 绝对600–800 Mbps **NOT_QUALIFIED**。
