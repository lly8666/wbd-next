# M0 PLAN029 接班记录：H2277–H2280 三机TCP容量和双向损伤（2026-11-22）

本文件是main M0控制面恢复收据，**不代表研发分支已合入main**。任务仍为 `M0-PLAN029-THROUGHPUT`，研发实验分支 `experiment/m0-029-throughput-arm-fair`，PR#68 Draft；030未启动。至H2280源 `f4fcd233cdd749c84da27453b5f194811a92a2bf`，尚未改生产Go/Rust/Windows Wintun/NPF默认容量参数，产品性能晋级仍未发生。

## 已真实收回，不重测或改写旧结果
1. H2273 c5066db [Windows真实原Wintun/WSL2外层修复OFF 1%](https://github.com/lly8666/wbd-next/actions/runs/44923149093)和[5%](https://github.com/lly8666/wbd-next/actions/runs/44923151036)两run整体FAIL于第二阶段相同输出目录WinError183，但第一阶段四条真正TCP收发有可用**限域实测**：1% Windows发1.869Mbps/Linux发1.737Mbps，小TCP P99 938/1014ms；5% Windows发0.753Mbps/Linux发0.497Mbps，小TCP P99 1890/1522ms。160/160回复不等于及时，ON阶段未成功，不能报产品修复效果。H2278修复OFF→ON归档冲突，仅单测验证，不声称Windows产品赢得吞吐。
2. H2274 [ARM原GoTLS/Rust FEC2原off/fixed/off Action44923756259](https://github.com/lly8666/wbd-next/actions/runs/44923756259) 1% B fixed0 146.429Mbps对off 64.813/80.540，P99 480.751ms对903.56/904.14；5% B fixed1 122.740Mbps对off 43.893/41.978，P99 904.34ms对1463.87/1200.44，client CPU秒/有效GiB 19.725 vs off约25.5/28.2（5%）。**有利候选、非跨机/Windows和默认全产品资格**。
3. H2276 [Linux x86 relay Action44925523352](https://github.com/lly8666/wbd-next/actions/runs/44925523352) 两组Win2025 client/x86 Linux relay/ARM Linux server，原生tcp ALL PASS，但 Windows→x86 relay Tailscale 经DERP，干净0ms goodput 10.002/16.232Mbps，主机CPU不满。确认环境失效不是Rust瓶颈。
4. H2277 [独立ARM relay Action44926156989](https://github.com/lly8666/wbd-next/actions/runs/44926156989) 改两套每组三台原生Win2025/ARM Linux relay/另一ARM Linux server，真TCP和源身份全部通过，Win→relay与Win→server均有Direct候选。无附加损伤48.577/78.444Mbps，仍未满足高容量参考。
5. H2277后新 [H2276 source3a6e648 Action44926695235](https://github.com/lly8666/wbd-next/actions/runs/44926695235)，同两套三机真TCP：无额外时延A/B 422.511/70.890Mbps；单侧旧netem 200ms/0%19.116/15.363Mbps，1%6.318/4.259Mbps，5%2.202/1.505Mbps；CPU约2–13%，不稳定。不把旧单向netem样本当双向200ms产品性能证据。
6. H2279 source `967c3294d319c9830327a791a59c6e0f0e66585a` [run44927070942](https://github.com/lly8666/wbd-next/actions/runs/44927070942) 两组各自同一Windows→ARM真实OS TCP先直连再经独立ARM kernel DNAT/SNAT relay，均无额外loss/delay：A直连289.574Mbps→relay97.436（33.65%），B直连108.051→relay60.071（55.60%）；两段各真4TCP发送/ARM收到100663296字节、160 echo，Win主机allcore约6–15%；相同源码两组不挑最佳值。**即使0丢包，中继额外Tailscale跳数使底层容量显著下降，不能把该容量缺口归因为WBD的Rust。**

## 已证实夹具缺陷及下一精确工作
- H2276 x86初期失败：中继控制token重复KeyError、未放行TCP45902导致Win SYN零PREROUTING；已改用旧三runner证明可通信的TCP18727及独立UDP4789控制。原失败保留。
- H2280发现确切的netem回程逻辑缺陷：relay egress上的回程数据经conntrack reverse SNAT，源IP已经是relay，而旧过滤器仍按src=ARM匹配；旧 `parent 1:3` 单qdisc只可能有一个方向被损伤。原200ms echo P99仅约200–266ms与该缺陷一致。试验源 `f4fcd233cdd749c84da27453b5f194811a92a2bf` 增加两独立egress qdisc classes (1:3 Win→ARM、1:4 ARM→Win)，每档只认双方tc真实发包/损伤计数和400ms往返延迟；`qa-h2280-dual-arm-relay-bidir-netem-tcp.yml` 只在显式消息marker触发两套六VM真TCP -1/0/1/5，而旧H2279相关提交只执行静态。 [H2280 exact Action44928186966](https://github.com/lly8666/wbd-next/actions/runs/44928186966) 在本次记录时在途；静态单测已SUCCESS，三机真TCP及netem两向尚不能报告PASS。
- **另一个重要夹具限度：** H2271原TCP小测每条bulk上限24MiB，四条只96MiB，H2279干净直连2.781/7.453秒就完成，却把160 echo分布在约12.8秒。早已不受bulk竞争的回显P99不能当作高吞吐持续拥塞下的P99。后续应在两组三机改用真20–25秒持续供给/CPU+RTT+实际server bytes基线，不能继续用短流冲刺冒充稳态吞吐。
- 下一步按原M0 PLAN029依顺序：收H2280两个组真实netem双方计数/收字节/P99，夹具不过优先修夹具不改WBD参数；合格时作长时间真实窗口和/或基于H2274已在ARM原产品成功的FEC2候选，对比同一个2×3组网的Direct原生OS与原产品TCP，分别记录Windows+ARM进程CPU、源Tun/M1/M4入/出/丢、内外重传、P99/超时和原生owned Stop。不因不合格GitHub/DERP而拿CPU headroom换成无限软件排队，避免P99恶化。

本控制面事实S以后用仅cursor变更H回指；直到双组真实原 GoTLS/Rust Win→ARM、CPU/P99/可归因收益收全，PR#68保持Draft，main不晋级产品优化。
