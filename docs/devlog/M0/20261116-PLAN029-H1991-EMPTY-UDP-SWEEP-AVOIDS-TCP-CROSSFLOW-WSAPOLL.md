# PLAN029 H1991｜普通混合流去重复 UDP 空 WSAPoll（不是极端压力工况）

- 用户要求沿 H1965→H1970→H1974 正常性能优化，不做高额度、长压或反复2048旧诊断。H1990 SOURCE `620d35419c8ab6e0edd47661f54c101bbb65b187` 的 [治理43834103182](https://github.com/lly8666/wbd-next/actions/runs/43834103182)、[维护43834103172](https://github.com/lly8666/wbd-next/actions/runs/43834103172) **SUCCESS**，原H1989旧H1940源码断言失败被更严格新轮换检查替换，未撤销生产性能改动。
- 同时收在途 [H1988 M0 native43832554963](https://github.com/lly8666/wbd-next/actions/runs/43832554963) **success**：原 `SOURCE=22c44a70...` 正常Normal/off Windows↔Linux TLS/Wintun/Npcap OS WAL Ready、真kernel TCP/UDP 双向及双方owned Stop全PASS。这个场景不启CN Direct和P2采样，**不能**报本轮CPU/p99收益或H1974 61ms已消失。[H1989 normal原native43833451125](https://github.com/lly8666/wbd-next/actions/runs/43833451125) 收件时仍在运行，原结果未知且不重复dispatch。
- Rust `NativeSplitWorker::poll_udp_reverse` 的 UDP lane 每次到达都做 `WSAPoll(timeout=0)`；若同一轮32个真实 TCP return 不断到来而一个普通 Direct UDP socket 空闲，可能对同一空socket执行几十次无意义syscall。这与 H1988 的DNS反复轮询同类，开销落在同一个Rust TX，不该让TCP为无关UDP空探针买单。
- 本次只在 Rust TX原 `tick` 重置栈/struct计数；UDP lane仍公平轮转，每次负探针增加真实WSAPoll覆盖的量子（默认16个live sockets），最多扫完整活跃UDP socket一次后本轮跳过空轮询；任何真实收到的 UDP packet 清零计数可继续出队；下一轮(原事件或<=10ms已有DNS/UDP等待)重新允许轮询。即使活跃UDP>16，也必须至少经过ceil(active/16)个已有扫描机会才抑制，而不是只看最早16个；绝不增加轮询线程、Wintun writer或大队列，不改变Tunnel/TCPTLS/Stop。
- 加一个不建真socket的纯Rust测试，普通单UDP +32 TCP回包空查询最多一次、真UDP有回复可继续、33-flow三量子覆盖全表、下一轮重置。这个新 SOURCE 的 Rust/真实网络 **NOT_RUN**，原H1974 61ms及p99/CPU增益仍OPEN；下一行动只收自动CI和已有在途结果，不派发极端压力场景。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1991 reduce redundant empty physical UDP WSAPoll during ordinary Direct TCP bursts to one full rotating live-UDP sweep per TX turn; retain every UDP flow's chance and bounded fairness; pure Rust test, real perf not claimed."}
```
