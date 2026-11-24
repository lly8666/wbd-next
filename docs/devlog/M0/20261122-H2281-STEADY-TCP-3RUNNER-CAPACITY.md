# H2281 · 两套原生三Runner改成持续高供给TCP，不让24MiB短流虚增吞吐/P99

## 为什么需要这个实验
1. 之前H2279直接/中继零损，4条bulk每条最多24MiB，固定仅96MiB；A组直连 289.574Mbps仅 **2.781s** 结束、B组108.051Mbps **7.453s** 结束；而160回显、每80ms一个，总共约12.8s。后半段（尤其直连）小TCP P99常在无大流竞争时观察到，所以不能称“持续bulk+稀疏”或用来证明业务优先级。这是测试应用供给时间窗口缺陷，不是产品Go/Rust丢包。
2. H2280双套真的 Win2025 client/ARM relay/ARM server在修正双方向tc后证实200ms+200ms、双向实际netem drops。原SOURCE `f4fcd233cdd749c84da27453b5f194811a92a2bf` [Action44928186966](https://github.com/lly8666/wbd-next/actions/runs/44928186966) 原生客户端/中继2/2 SUCCESS，ARM两组业务和4stage SERVER_ALL_TCP_STAGES_PASS，但工作流最终遗留H2279不同peer断言导致整单FAIL；收据已在 `6011ce586eed0aa48487d8f4cfad4aabdc49b820`更正并新增单测，**不重发同样高成本六机**。完整真观察数据 `docs/evidence/M0/PLAN029-H2280-REAL-WIN-ARM-DUAL-BIDIR-NETEM-20261122.json`；原整单红色绝不涂绿。
3. H2280真实400ms RTT级别双向0/1/5% loss下裸 TCP本来只有 A/B 7.952/7.681、3.491/3.178、0.789/1.001Mbps，虽然Win和ARM总体CPU都远没拉爆；因此目前主要嫌疑是**跨机网络容量、长RTT TCP窗口和丢包引发的拥塞退避，尚不能归因于WBD Rust队列**。在修产品前必须把应用供给和实际持续重叠校准。

## 施工范围
- 只修改H2276测试专用 Python wrapper，只有全局 `WBD_H2281_SUSTAINED_TCP=1` 时临时覆盖**当前wrapper进程内**的 `m0_wl_loss_tcp_probe` globals：`BULK_MAX_BYTES = 512MiB`（每条4TCP）、`BULK_SEND_S=25s`、`TIMEOUT_S=150s`。原 Windows签名Wintun/WSL2 和旧 H2271 test Python源码/CLI保持原来24MiB/18s，生产无配置变化；这样不会偷改旧H2273 SOURCE的数字。
- 强制每档实际Win本机回报的4流接收器端确认 `bulk_wall_s >= 15s` 且收到字节正数，确保至少160次小TCP覆盖整个12.8s供给时间窗口；保留接收goodput，ARM原本SERVER_DONE每档真实接收与双方CPU测量。继续分别录 P50/P95/P99、late1000、TCP已收字节、tc双向实际发包和loss（0/1/5必须两向有真实丢包）与Tailscale直连/DERP。任一方向netem缺失或bulk太短即拒绝资格。
- 新 `qa-h2281-dual-arm-relay-sustained-tcp.yml` 单Action两组三台原生机器（Win2025+ARM relay+另一ARM server各一），同一source、同序独立四档 [-1 无附加损伤、200ms每向0%、1%、5%]；只有本次明确提交tag `[m0-029-h2281-sustained-3runner]` 才触发六VM昂贵作业，普通相关push只跑廉价静态。H2279/H2280旧流程不会被无意重发。
- 性能问题的判别式：若H2281持续25s仍在200ms0%只有~8Mbps，但CPU低，则下一单因素候选是**内层TCP窗口/缓冲实际readback与适度服务窗口增大**（测Windows Winsock SO_SNDBUF、ARM Linux SO_RCVBUF和双方TCP_INFO，明确本机缓存、跨流公平与队列P99）；若底层网大幅提速，再在同一双组三机接原GoTLS/Rust Wintun/NPF，优先同一源下FEC2 OFF→fixed0/1→OFF对照，端到端记录原客户端/服务端各M1/M4、本机drop、CPU和TCP p99与超时。**测试本身不等于产品优化生效**。
- 不把25s长流的goodput直接和旧2–7s短流goodput计算百分比：原拥塞窗口尚未收敛且含启动/结束段，互相不可比。PR#68仍Draft、产品默认不晋级。

```feature-impact
{"kind":"none","reason":"H2281 changes only explicit env opt-in native Windows-to-ARM 2x3 runner TCP capacity harness bulk supply from cap-limited 24MiB/18s to 512MiB/25s, with P99 overlap gate; production Go/Rust, drivers, configs and Stop unaffected."}
```
