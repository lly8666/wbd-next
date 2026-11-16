# PLAN029 H1959｜收 H1958 真 Win/WSL2 P2 四臂＋D3 冷 FakeIP 目标校验

## 原 H1958 真实源锁 P2 结果
- [Action43792684618](https://github.com/lly8666/wbd-next/actions/runs/43792684618)，固定 SOURCE `ab224ae03cd362f758f98fb59fd097285e436ca6`，Windows原 Go+Rust内核Wintun及WSL2 Linux真 TCP 内核 socket、Artifact14193726167 的 `report.json` 和 Stop 原日志已核对。唯一一次构建，原 SHA/FIN/4MiB、共 **5次Linux physical kernel TCP收件**（1个物理baseline +4个经Wintun Direct），120/120条原 Tunnel UDP、持续632条跨全四臂及小TCP、**PASS_BOTH_OWNED**。
- 真原 Direct 4MiB 四条严格 ON→OFF→OFF→ON，单条 elapsed 95.133/90.504/70.980/82.832ms，upload 49.397/47.086/33.622/27.176ms，download 27.687/29.017/23.687/30.874ms。ON均值 **88.982ms**，OFF均值 **80.742ms**，ON/OFF **1.1021**。本轮物理4MiB baseline **38.868ms**；OFF/物理 **2.08x**，ON/物理 **2.29x**。Windows原应用本地source-port和Rust Stop H1955 QPC **4/4** 精确联合；原32KiB cold单独一条，无掺混四臂。
- 同一个 SOURCE 的原384 Direct小流（Linux fin-first/payload-first各96 ON+96 OFF），Rust/Windows QPC **384/384** 关联。FIN-first FIN→首次物理write p95 ON **0.261ms** / OFF **14.854ms**，p99 **0.573/15.735ms**；payload-first p95 **0.215/14.317ms**，p99 **0.245/15.360ms**。大于8ms: ON 0/0 vs OFF 8/8。H1955另一台真实VM的首到收益方向亦相同，支持缩短真实建连等待。
- **关键限定**：四臂分别只有两条真实4MiB，ON重复相差12.301ms，OFF重复相差19.524ms；速度顺序/VM噪声不可忽略。虽然源锁并完全部署，**不能认定+10.21%为稳定因果退化，也不能认定大流性能合格**。Direct 4MiB仍比物理socket慢约2倍。原生 Stop和所有流正确性 PASS_SCOPED；P2性能出口 **OPEN**；普通用户的 first-SYN physical preconnect **OFF**，不推灰度，没有压力/恶意半开连接合格证据。

## 不与 P2 串联的一处 D3 冷数据缺口
- `SplitPolicy::announced_fake_target` 对 FakeIP 映射的真实目标已拒绝0/broadcast/另一FakeIP；但 `remember_announced_fake` 冷恢复入口只拒绝fake range，**过去仍可装入0.0.0.0或255.255.255.255**，造成后来 `destination(fake)` 向无效物理目的地Direct，尽管 DNS分配器自身也过滤这两个地址。
- H1959最小修正让冷恢复复用同一个 `announced_fake_target` 验证；1个Rust回归覆盖0/broadcast/另一FakeIP拒绝且不污染已有健康映射。只在已有映射构建/恢复入口执行，不增加普通DATA逐包处理、系统calls、Go热泵或另一socket。
- 本批修复是源码+原生组件单测**待CI**，不是新 SOURCE 的实际 DNS/GUI/IPv6运行证据；D3总体仍OPEN。H1958原生SOURCE独立存证，下次CI不附 P2 scene flags，避免无假设重测。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Archive actual H1958 one-source 4x4MiB Direct ON/OFF/OFF/ON, small QPC384, Tunnel UDP/owned Stop; unify invalid real-A guard for cold FakeIP mapping restore without altering normal data or claiming full D3/P2."}
```
