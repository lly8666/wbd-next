# PLAN029 H1956｜H1955 真 ON/OFF 小流 PASS；原 4MiB OFF 出现波动，单 SOURCE 补四臂

## 收到的真实 H1955 源锁动作
- 原 [Action43788677966](https://github.com/lly8666/wbd-next/actions/runs/43788677966) SOURCE `4bab00bdc38fa410180dcecf4e8f0415c0b544b9`，Win2025 + 真 WSL2 Linux kernel、一个 Rust TX + 原 Wintun/WAL/Stop，原 artifact14191093972。
- QPC 真 **384/384** Direct：FIN-first 和 payload-first Linux 回声，各96 ON（真实首 SYN 提前物理非阻塞 TCP 连接）+96 OFF（原 listener.accept 后连接）。FIN→首次真实物理写 p95 (ON/OFF)：**0.234/4.798ms**、**0.253/13.749ms**；p99 **8.156/14.685ms**、**0.314/35.476ms**。物理连接时间 p99 ON6.006/0.105ms，OFF19.213/14.863ms。两组原业务/FIN/SHA OK。
- 原物理4MiB 34.260ms、原 Direct4MiB 462.673ms，Windows Direct上传396.420ms，Tunnel 96B UDP120/120、持续634、双方 owned Stop PASS。**从首个应用 Direct32KiB 和第二个4MiB Direct 原同 Windows QPC 时序看，H1955 这唯一4MiB真实 Direct 属于 OFF**：首原32KiB port56375 是 ON，4MiB port56378 OFF，accept 514.486354s 与4MiB app start 514.485835s 对齐。此4MiB 462ms 不是提前建连的退化证据；与 H1953 不同 SOURCE Direct120.698ms 比较只说明尚有无因果解释的测试/运行波动。
- **界限**：96样本/臂不是随机分配，p99 是观察而非全体性能保证；小流改善成立于该一 SOURCE/VM，4MiB提前建连组尚 NOT_RUN，故不启用产品 preconnect。

## 本 SOURCE 的下一步小而完整实验
- 仍然保持 **独立原 Win2025+WSL2 两端产品**、原 P2 4MiB 16KiB 块、Linux原 TCP46112 kernel listener、一个已存在的 Windows Rust TX/Wintun NAT 物理 ifindex 和持续 Tunnel 96B UDP；不添加新的网络进程/线程/端口/OS路由/WFP。
- 仅 `m0_v4_probe` + GitHub Actions + 原 V3 + 全 H1945/H1948/H1953/H1955 签名及新 `WBD_PLAN029_P2_PRECONNECT_BULK_ABBA_SCENE=1`，原 32KiB Direct 控制仍第一位 ON，然后四次原 kernel Direct 4MiB **ON→OFF→OFF→ON**，之后原 384 Direct 小 TCP 仍每策略96 ON+96 OFF。没有启动第二个 Linux TCP listener，已有 listener 明确接受 1 physical baseline +4 Direct，并用 OS TCP 4MiB/FIN/SHA 5次验真；原 P2 UDP 连续覆盖全部。
- 四次同 SOURCE 同 VM，不拼接历史不同 Runner；Windows app receipt新增**原 kernel socket 本地端口**用于 Stop 后将 4条正宗进程 QPC 与 Rust first-SYN/accept 一一匹配，且必须与原384小流端口无碰撞。缺行、模式不匹配、Linux少一连接、SHA/FIN错误、来源漂移、Stop失败即 fail-closed，性能高低不影响证据透明。
- 计算四臂各两次 elapsed/upload/download 均值、ON/OFF ratio；**n=2/臂不算峰值、CPU归因或充分因果证明**。退出前检查大流是否出现严重稳定回退；观察不足则保持正式产品 preconnect OFF。未跑前证据 PENDING。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect H1955 original source-locked 384/384 signed small-Direct ON/OFF QPC and STOP; add one same original SOURCE 4x4MiB ON/OFF/OFF/ON physical preconnect diagnostic with exact guest/port/QPC/FIN/SHA/UDP proof, not production enablement."}
```
