# PLAN029 H1851｜H1850真P2超时；修单TX收发量子不对称

- [H1850 Action43603707025](https://github.com/lly8666/wbd-next/actions/runs/43603707025) SOURCE `889b28e6` 原Windows/Linux签名正常/WSL2/编译均进入真实P2，客户端进程38秒截止 **FAIL**。Direct上传1MiB于19.140s到应用发送进度，19.937s半关、21.390s收到首字节，37.671s仅917504字节下载，不得称完整交付、Stop PASS或“只是夹具失败”。失败报告本身的`stop=NOT_RUN`；原Action finally中项目owned RST/Hyper-V/邻居/Npcap/管理路由清理独立为PASS。
- H1849 1Hz分腿样本在旧`tools/m0_wl_public_normal_e2e.py` P2分支已启用，故H1850新增workflow环境开关是**重复诊断**，撤掉并保留失败结果，不刷同类P2。
- 复核单一Rust Wintun TX：每个工作轮 `stage_sources` 最多4×8=32真实Ingress，而仅8份Direct反向队列回注；`NativeTcpActor.ready` 最多256份，`direct()` 和 `kernel_return()` 满时失败，前者导致LocalDrop，可能触发原生Windows TCP超时。此前证据**未记录ready峰值／满次数，不能声称确定根因**。
- H1851只将反向处理预算从8对齐为原有32，RX本来有32上限，不增内存、不调1ms忙轮、不重构旧外层普通Tunnel/防火墙，也不另开worker。追加**现有P2-only诊断** `ready_now/ready_peak/ready_full` 每秒一次，为下个SOURCE检验上述单假设；正式产品off不增加逐包日志。纯不变量测试确保4×8与回程量子一致。
- 此提交的新SOURCE签名P2、吞吐/queue overflow和独立资源压测此时均 **NOT_RUN**；`[plan029-v3-real-p2-rebuild]` 只选一次正式Normal场景，别重复dispatch。保留H1849 PASS_SCOPED完整1MiB与H1850 FAIL事实；029非交付。继续Game4 CN、GUI真启停、D1–D5残项、IPv6/中断恢复、P1 CPU与FakeIP持久化压测。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record signed H1848 formal product PASS_SCOPED, H1849 slow P2 and H1850 real 38s P2 timeout; update bounded native Direct TCP reverse quantum and opt-in ready pressure receipts without claiming complete P2."}
```
