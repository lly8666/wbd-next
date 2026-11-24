# M0 PLAN029 H2281–H2283：真双组三Runner TCP窗口/吞吐恢复收据（2026-11-22）

本文是 main M0 权限控制面 **已验证实验结果**，不是将测试源码或产品优化合入 main。当前有效任务仍 `M0-PLAN029-THROUGHPUT`，实验分支 `experiment/m0-029-throughput-arm-fair` 与 Draft PR [#68](https://github.com/lly8666/wbd-next/pull/68)，M0仍未满足全产品 P99+CPU+Drop 验收，绝不晋级默认配置。

## 已收真双组三Runner无损25秒连续TCP，不再被24MiB短流困住
- H2280 SOURCE `f4fcd233cdd749c84da27453b5f194811a92a2bf` [Action44928186966](https://github.com/lly8666/wbd-next/actions/runs/44928186966) static、两组Win client及两组ARM relay均成功完成真双向kernel netem；两ARM server实际四stage收发完整，但最后继承H2279不同peer断言失败，**整单FAIL**。后续纯报告修复 `6011ce586eed0aa48487d8f4cfad4aabdc49b820` 静态SUCCESS，不篡改原失败。
- H2281 SOURCE `e49b1ecf651063ae1a2e8c141a14ed7ea6f83dc3` [Action44929074737](https://github.com/lly8666/wbd-next/actions/runs/44929074737)，七job全部SUCCESS、双独立 Win2025 client＋ARM64 Linux kernel relay＋另一ARM64 server；真原生 4TCP 25s、160小TCP、双方向各200ms、netem真实包/丢失读回。A/B 无附加延迟吞吐67.794/60.644Mbps；双向200ms 0% **8.485/8.409Mbps**、1%3.361/3.449、5%1.113/0.970Mbps。200ms0%小TCP P99两组皆469ms。Win CPU1.94/2.47% 、ARM host1.08/1.23%，两端都远没满；但 **relay tailscaled 热核、interrupt/softirq另需观测**，不得假设所有三机CPU都没瓶颈。
- 跨机裸TCP本身零loss/400ms RTT约8.4Mbps，因此产品GoTLS/Rust队列不是这个结果的已证明根因；24MiB短bulk在旧H2279提前结束的夹具弱点已经解决。

## H2282：真实Windows和ARM端点socket buffer是关键低速因素
- 精确SOURCE `cb09a27013e391b338a782b21ead9b82a8f3d675`、[Action44930023496](https://github.com/lly8666/wbd-next/actions/runs/44930023496) attempt1 **七job全SUCCESS**。同两组真实三机、同一个固定双向400ms/0% netem和25s原生TCP，顺序**A默认→B两端8MiB SO_SNDBUF/RCVBUF→A′默认**。Win各四条bulk socket原默认send/recv 131072B，B实际getsockopt8388608B；ARM server listener默认rcvbuf131072B，B Linux实际readback16777216B（Linux加倍记账），真实ARM收字节与Windows RECEIVER_GOODPUT及两个方向netem packet计数齐全。OS sysctl16MiB上限整个A/B/A′相同，server Owned finally恢复。所有160/160小TCP回复，无每档>1s尾回。
- A组三段接收吞吐 **8.829 / 227.397 / 8.909Mbps**，B相对默认两值均值**25.64倍**；小TCP P99 **453/984/454ms**（B延迟变差），Win整机CPU1.214/12.272/1.341%，ARM1.523/8.688/0.833%。B组吞吐 **8.095 / 339.676 / 8.605Mbps**，**40.68倍**；P99 **469/594/469ms**（B也升高），Win4.685/39.682/1.744%，ARM1.428/17.576/1.162%。真实原始ZIP A client14717272408/server14717651387、B client14717730532/server14717397234，实验分支结构化证据 `docs/evidence/M0/PLAN029-H2282-WIN-ARM-SOCKET-BUFFER-A-B-APRIME-20261122.json`。
- 结论严格界定：**裸TCP端点缓冲/窗口限制非常明显**，有CPU余量；但8MiB使P99显著变坏，且两端同时改变，不能只归责Windows或ARM，绝不是原WBD产品吞吐PASS或应该修改SharedTun M1/M4队列/安全默认。应找更小大小及端点单因素，**吞吐＋P99共同评估**。

## 在途和下一动作
- H2283 SOURCE `96a72df9941b543fac8564f9c8f295dd4c09297b`、[A/B/A′ 双组三Runner Action44930676830](https://github.com/lly8666/wbd-next/actions/runs/44930676830) 本记录时已静态SUCCESS、六个不同原生Windows/ARM机器启动；唯一实验变化 B仅请求**2MiB 两端buffers**（A/A′仍默认），同双向200ms/0%、真25s四TCP+160回声，输出真实Goodput、CPU、OS socket readback、P99、实际kernel tc。最终结论以原run和两组artifact为准；本记录仍 NOT_YET_RECEIVED。
- H2274 ARM原GoTLS/Rust Normal FEC2在1%/5%真实原内核弱网的OFF→固定档→OFF对照有明显业务吞吐和P99候选收益，但**Windows真实Wintun/NPF↔另一ARM原GoTLS/Rust跨机还没跑**；必须将有效OS容量结果同WBD原产品实际client/server M1/M4、source drop、CPU/有效GiB、跨流HOL/owned Stop及外层修复隔离出来验证，杜绝裸TCP test替代产品业务。需要定位ARM/Linux relay tailscaled单核使用与Windows OS TCP sock窗口。PR#68仍Draft，PLAN029 Open。

主线只记录真实SOURCE/局限，原本H2280之前所有FAIL记录保留。
