# PLAN028 H1457｜真实 Windows+Linux 600 秒 + 双端正常 Stop：PASS_SCOPED；外部Ubuntu实际时间轴

SOURCE `548a47cc708d82d45e1722540b6677342f3c8c5b` 的真实三臂 [Action42555320138](https://github.com/lly8666/wbd-next/actions/runs/42555320138) 完整 `completed/success`。我直接从 [原生artifact13647552726](https://github.com/lly8666/wbd-next/actions/runs/42555320138/artifacts/13647552726) 下载原始23文件（zip CRC PASS），逐项对照 `h1415-mixed-client-report.json`、`h1430-l3-samples.json`、Windows/Linux内核UDP原始应用日志、`direct-full.log`、OS路由和Npcap清理。600.0s已认证两客户端，同一共享Go TLS443/Rust M4服务端：Windows 5575真实UDP发送/5575回声/5590反向包；Linux 5590/5590/5590，真实双端TCP 10轮，最大Windows正/反向间隔125/188ms，Linux118.69/115.46ms，管理/32采样53次、added=0,repaired=0。真实Windows先Stop后Linux TCP+UDP继续收到10个，随后双客户端和server准确Stop，Linux原bridge/default恢复和Windows原WAL残留0、Npcap cleanup PASS。**结果仅为 `PASS_SCOPED_REAL_600S_BOTH_CLIENTS`，不能借Workflow全绿宣称1800s L3完成。**

**必须纠正旧说明：** `h1415-real-kernel-app.py` 源自H1415内联 `product_app()`，每轮select最大45ms再sleep60ms，服务端反向UDP每100ms。本次真实客户端平均仅9.292/9.317数据包/秒，**不是所谓10ms间隔/100pps**。600s确实有真实持续业务，但只代表低速功能+生命周期稳定；不包含更高PPS/吞吐资格。这是已有测试的覆盖口径漏洞，原证据未变更，诚实限定范围。后续正式L3压力依PLAN028 acceptance另取真实发送能力和内核backpressure证据。

**资源斜率：** 5组90..570s真实Windows原客户端内存：私有字节38,080,512→38,137,856（+57,344B），句柄323→317，线程15→14，RSS42,233,856→16,142,336；WSL2 server/client两个进程RSS仅+320KiB/+36KiB。没有本时段单调急增的Windows句柄/线程或明显私有内存泄漏；不证明600秒后一定没有泄漏。

第二台完全不装Wintun/WSL的 `windows-2025` 控制组 `128961150470` 实际750.2s/50次心跳 `PASS_SCOPED_CONTROL_ONLY`，原始 [artifact13648260573](https://github.com/lly8666/wbd-next/actions/runs/42555320138/artifacts/13648260573) CRC PASS。不同Ubuntu job `128961150381` 从其独立 [artifact13648435192](https://github.com/lly8666/wbd-next/actions/runs/42555320138/artifacts/13648435192) CRC PASS读70条GH状态元数据：03:32:41Z干净Windows完成SUCCESS，03:38:06Z真实Windows native job完成SUCCESS，并非凭本机日志自报控制面还活着。

发现**观察器另一个实际夹具错误**：此前源中 `latest_step:([.steps[]?]|last)` 选了末尾pending post-checkout而非在跑的step19，不能用其旧字段判断活跃stage；本次H1457只改后续只读观察口径为 `active_step`（in_progress）+ `last_completed_step`（completed），不改变已经验真的70条job时间轴、产品源或历史失败。

目前最强结论：同样编译产品机器码，在同宿主真实Windows+WSL2上**可以连续600s业务、正常Stop并把GitHub job成功上传**，排除固定360/600s必死、明显600s句柄/私有内存耗尽；此前长失败依然是原Action FAILURE/native step19未完成、最后原始业务720或960等随机时刻健康，未证明准确失联机制。仍需远端独立Windows/DUT+外部Linux业务/控制域后才能认定1800s或具体宿主路由根因。绝不追加旧同宿主1800或重复600。H998保留，Android/物理NOT_RUN，ARM64 eef2两场1800和Windows短测范围PASS保留，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked scoped original 600s receipt, exact cross-host timeline, honest packet cadence and off-host job active-step parser correction only. No product changes."}
```
