# PLAN028 H1460｜一场4并行原生压测＋6份历史原物证离线严格复判；找准队列丢包分支

四路SOURCE548 Linux原生5客户端180s真实负载Action42567898270源锁成功、各6个原始Stop/源manifest/4独立ZIP CRC_PASS。因Normal75出现真实零损应用失包和共享TUN队列溢出而旧专用审计仍回PASS，不通过重派网络去凑结果。H1459新增独立[离线Action42569573991](https://github.com/lly8666/wbd-next/actions/runs/42569573991) SUCCESS：它从GitHub拉4份原H1458 + 旧6c5 Normal75和Game4共6份source锁的真实ZIP，只重新解析原记录。原始[artifact13652915541](https://github.com/lly8666/wbd-next/actions/runs/42569573991/artifacts/13652915541) CRC_PASS、zip SHA256 `87ccf62ca988bbf0e5542a690fbc5cc65170c320b74c62ae4f1cb2787d05a407`，含`h1459-review.json`及审计日志。

**正式差分：** SOURCE548 x86 Normal50实际50Mbps/方向PASS_SCOPED，零丢零队列溢出；Normal75实际75.001Mbps/方向，30s overload阶段Alice上行缺25下行缺3，warmup、25M、50M sustained和50M recovery阶段**0失包**；server lease 10.66.0.149 `pending_overflow=5`、`pending_peak_packets=8`，老audit却`PASS_SCOPED`，新完整严格结果 `FAIL_SCOPED_ZEROLOSS_UDP_MISSING_OR_SERVER_LEASE_QUEUE_OVERFLOW`。Game4 Fixed6真实20Mbps、回落10Mbps、无失包无队列溢出PASS_SCOPED；异构弱网含30%源网络真qdisc29.93/29.84%，原转轮且六Stop PASS_SCOPED（该场真实物理设损导致UDP缺1852是预期，不能按零损门槛处理）。历史6c5 Normal75虽0失包/0溢出，但OS VM负载74.93%与SOURCE548 90.03%不同、产品二进制也不同，**无法证明回归归因**。历史旧6c5 Game4 CI42567898293 FAILURE保留，20M原始业务/Stop确实PASS_SCOPED，仅旧Workflow把正确20Mbps枚举写成不含20的10Mbps字符串导致最后AssertionError，列`HARNESS_STALE_RESULT_ENUM`，不修路径而意外重启昂贵测试。

**定位到真正执行的Rust分支，而不是笼统猜想**：`crates/wbd-engine/src/v4_embedded_go.rs` 的 `enqueue_shared_tun`（约4321-4392行）在下游 `SyncSender::try_send` 已Full且每租约pending queue达到 `SHARED_TUN_PENDING_PER_ROUTE=8` 时明示`d.overflow+=1;return d`，当场不把新包入队；`run_shared_tun_reader`（约4960-5044）按每租约`M0_SHARED_TUN_LEASE_QUEUE_DIAG`将该原始丢弃累计出来。原native log正是`pending_peak_packets=8 pending_overflow=5`，所以这5次确实是真队列满丢弃，**不是统计误差或报告漏抓**。但尚未证明下游处理不及的第一因是产品worker背压、共享Linux VM单核忙、短突发还是别的OS条件，也无法一一解释28个缺包。因此不未经验证地直接扩大队列、隐藏丢包、放宽源业务门槛。

**实施**：测试工具`tools/m0_plan028_h1458_stress_verdict.py`的新范围门禁将零损原始UDP缺包或server pending queue overflow直接FAIL_SCOPED，旧4个Action/原始旧报告保留，`tools/m0_plan028_h1459_offline_rejudge.py`及其unit确保从原始ZIP可复算，并按不同比例网络损伤区分真实物理配置丢包。原生Go/Rust产品代码未修改，不重跑Windows1800/其他网测。下一步若要修产品先在相同SOURCE/同规格VM做有控压力对照，采样下游Full与队列恢复时序、OS每核忙与发送产生速率；不要将跨VM/跨二进制差异宣称产品回归。

PLAN028保持IN_PROGRESS；H998历史HOT FAIL、Android/物理NOT_RUN、Windows原1800仍NOT_QUALIFIED；ARM64两场1800及Windows600局部PASS不受影响。

```feature-impact
{"kind":"none","ids":[],"reason":"Original-source immutable offline 6-artifact rejudge, scoped red/green evidence and exact Rust shared TUN queue attribution, no Go/Rust product changes or new network traffic."}
```
