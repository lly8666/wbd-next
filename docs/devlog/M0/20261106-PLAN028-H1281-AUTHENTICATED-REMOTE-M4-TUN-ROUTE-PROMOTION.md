# PLAN028 H1281：H1280三场原始验收及远端M4证实后才切换路由

日期 2026-11-06。旧H1280源 `ab99fa457b266bbe70809ab0f3ef754faba91afe`，原生ARM64 [Action42206643488](https://github.com/lly8666/wbd-next/actions/runs/42206643488)：build SUCCESS，但三个1800s五客户端场景**全部FAIL**，baseline/heterogeneous/pressure告警7/11/12。原始三份ZIP SHA256、逐场CPU/RSS、物理数据面故障列于[证据JSON](../evidence/M0/PLAN028-H1281-H1280-ARM64-3X1800S-VERIFIED-20261106.json)，每份验证真实SOURCE。不能拿构建成功替代性能通过。

## 复现与根因边界

- Baseline Alice Normal Off：物理TC损伤0，客户端Gen27本地M4 READY并停止旧Gen26，服务端在11:29:30拒绝其真实源端口58251，`m4_stage=rust_loop_start native_rc=3`（Rust BAD_STAGE），64.24秒双向无业务。rc3有多处Native出口，具体内部条件仍待定位，不能在本报告里猜定GlobalRepair或shared_route_publish。
- Heterogeneous Carol Game2 Gen6：11:06:12两条lane客户端M4 Ready；服务端lane2 port57798暂存，lane1 port57797在一秒后`stage=protected_tls class=other`，并非超时；双向活跃发送无接收104.6/104.7秒。Pressure Gen12同型：服务端lane2 port56172暂存，lane1 port56171`class=other`；双向99.93/100.02秒。此前六次纯TCP ACK保护并未根治这类非超时拒绝。
- Game4异构/高压仅6/5次实际热lane成功，要求至少10次；Fixed6异构3.32/3.31秒、高压2.29/1.26秒真业务空洞。R/(F+R)仅加密record字节，三场0.70106/0.81690/0.83800%，不含控制C、FEC parity或IP/TCP/L2总成本。

## 两阶段客户端产品修复

在 `crates/wbd-engine/src/v4_embedded_go.rs` 的现有单共享TUN原子route registry，Normal与完整Game2/4**重叠冷代际**不再在本地M4`loop_start`时撤销旧出站A。新B完成真实Go TLS/FakeTCP + Rust M3/M4并独立监听原RAW接收，但A仍拥有可用的出站TUN route。当B实际收到并成功在原生TUN交付**本代AEAD/PN/replay认证的反向IPv4业务包**，Go通过新增仅本地C ABI触发Rust二次检查计数、原子发布B、撤销A，然后才向原Go path supervisor报告READY。若服务端拒绝B或5秒内无真实接收，B Stop不影响A原出站路由，旧代继续工作；首次连接/旧路由已消失场景可先正常发布但客户端仍在重叠候选时要求本代收件证明。

Normal使用 `OriginalLoopPulse.RxRecords`，Game2/4整组使用 `KernelCounters.Delivered`；这些指标只有成功完成Rust M4验证和真实TUN交付后才递增。新增Rust回归覆盖已饱和旧A不被未经证实B抢占、失败B精确Stop、成功B原子切换并保护A晚到Stop；Go回归验证本地READY无接收、原生terminal/cancel、成功接收恰好promotion一次。Game4原来同组逐lane热换代不动。无新TLS私有字段、无Go逐包代理、无扩容共享队列或第二轮换调度器。

限制：业务单向完全无S2C IPv4时不能仅靠本协议外证明在5秒内安全切换，今后需研究已有认证健康控制作为证明，不能从本双向压测推广。旧H998 same-socket MTU FAIL、H1259/H1268间歇S2C继续开放。

H1281 ARM64分支预检首先成功完成了原生Go/Rust构建，但Python命令错误引用不存在的H1281测试文件导致预检步骤FAIL；文件名已纠正为原有`tools/test_m0_plan028_h1280_normal_m4_proof.py`，新同源预检及随后三场1800s严格归因仍需实际验证。验收必须保留 `rotation_verdict=PASS_ALL_FIVE_SCOPED` 和 `alert_count==0`，否则FAIL，结果不预告。

```feature-impact
{"kind":"updated","ids":["game-lanes","linux-raw-tun"],"reason":"Overlap-safe original Linux Go TLS/Rust Normal and Game2/4 group shared-TUN client route promotion requires real new-generation authenticated M4 reverse IPv4 receipt; preserve old active route on failed remote M4, no wire or FEC/PN change."}
```
