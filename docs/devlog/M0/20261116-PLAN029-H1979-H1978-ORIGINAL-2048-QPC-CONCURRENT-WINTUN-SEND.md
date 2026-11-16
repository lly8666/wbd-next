# PLAN029 H1979｜收原H1978 2048次真QPC；修正 SendPacket调用返回的错误因果假设

## 原SOURCE唯一证据，不覆写原Action失败

- 真Windows 2025 原Go/Rust、Wintun/Npcap、WSL2原Linux socket同SOURCE `a07e62fe4ee62ba90b5a1fd60a2699c36ee2ab11`，原 [Action43817058020](https://github.com/lly8666/wbd-next/actions/runs/43817058020) `native-public-two-os` job133133158554，**failure**仅在第19步原Python诊断 `H1966 QPC: H1977 causal boundary ordering invalid`，Artifact14202784333 `report.json` / `mode-results/normal/client.log`。
- 业务**本身正确**：物理与Wintun Direct各32预热+2048个正常1KiB已建连请求，每臂Linux内核真实收2,129,920字节，双方同SHA `0c5cfc1733c1b0e54b53e2b67a1777dc4f7d27a0e77669f625aa8d8af40fa927`，FIN、原报告 `stop=PASS_BOTH_OWNED` 和 `p2.stop=PASS_BOTH_OWNED`。嵌套`steady.stop=PENDING...`因下游Python析构失败，**绝不补改或借Stop覆写原FAIL**。
- 原真Win32同一QPC频率10MHz；Direct Windows源port60357→原NAT listener proxy32770，已验证**2080条Wintun原DATA记录、4160条两腿WinSock服务、2080条TX邮箱/2080条RX SendPacket/2080条FD_READ**，全部零采样丢失，**2048/2048** app窗口有唯一源port/真实SEQ/1024B和真实FD/内核read链，**TCP重传0**。

## 误判根因和正确时间模型

- 原分析器认为 `NAT≤TX mailbox≤RX SendPacket调用开始≤RX SendPacket返回≤inner内核read≤app回包`。
- 实际Windows多线程：**Wintun SendPacket调用已经开始且内核拿到发送packet之后，可以在本Win32函数尚未返回时，另一TX线程经真实WinSock FD_READ读到该TCP字节**。唯一两个原日志窗口 index495、index2042，inner.read分别比`SendPacket`返回**早22.8μs、2.6μs**。它们没有数据/时钟错误，也没有并发两笔应用请求。2046窗口满足旧严序，离线用正确偏序重算**全部2048窗口均合法**。
- H1979诊断修正为 `NAT≤TX mailbox排队≤RX SendPacket开始≤inner kernel read≤app recv`，要求`RX SendPacket返回≤app recv`但**不要求返回早于inner读取**；分别报告真 **RX调用开始→内核读取** 的非负耗时、**RX调用返回→内核读取** 可为负的有符号观测值和重叠具体窗口。正例合成测试注入真实允许的重叠；反例必须拒绝`inner.read`早于`SendPacket`**开始**，保留原source/端口/SEQ/每窗1024B/时钟/Chunk/drop/重传标记严门，不容通过跳过坏样本获得绿色。
- 此为源锁器械修正，不改原Rust/Wintun/NAT产品语义、线程、既有signed同轮交付规则，也没有声称整个内核消耗/ACK发生在函数返回。

## 不绕开用户的大差距优先级

| H1978同一Windows VM 2048条真实普通1KiB请求 | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|
| 物理socket RTT | 269μs | 334μs | 381μs | 916μs |
| 原Wintun Direct RTT | 521μs | 620μs | 682μs | 901μs |
| 分位数差（非成对因果） | +252μs | +286μs | +301μs | — |

| 离线从原Win QPC真事件重算（非原Action PASS） | p50 | p95 | p99 |
|---|---:|---:|---:|
| NAT入队→TX mailbox | 2.4μs | 5.1μs | 7.6μs |
| TX mailbox→RX SendPacket调用**开始** | 36.0μs | 43.2μs | 65.6μs |
| RX SendPacket调用耗时 | 11.0μs | 15.6μs | 26.4μs |
| RX SendPacket**开始**→inner kernel read | 46.2μs | 66.3μs | 89.5μs |
| NAT→inner kernel read | 84.2μs | 111.9μs | 139.3μs |

- H1978原Direct所有2048个应用请求**无≥8ms**延迟，也无TCP重复序列，**但此前 H1974 SOURCE bd611 原有5个61–63ms异常和4个重传未被修复/推翻**。不同 SOURCE/VM/p50物理也明显不同，不能宣称signed post-ingress交付解决了偶发严重尾延迟；原普通产品postflush及early preconnect皆OFF。
- 当前下一行动优先处理**61ms偶发失联/内核事件再唤醒**，不是优化0.2μs classifier/NAT；对没有复现的单次结果不能报永久优化。后续有明确因果修复时，需同源normal负载与Stop/QPC可验证对照。
- feature-card 16KB保护：保留之前52条`verification.status/source_sha/evidence`**完全不变**；仅收紧24条过长原scope摘要，原字句可从父提交`a07e62fe4ee62ba90b5a1fd60a2699c36ee2ab11`及对应原证据逐条恢复。本次登记H1978原失败53rd条，不写成PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-lock true H1978 Win2025/WSL2 2048x1KiB original FAIL and correct false causal assumption that Wintun SendPacket must return before another thread's kernel TCP read; preserve all source/status/evidence links and full PLAN029 OPEN."}
```
