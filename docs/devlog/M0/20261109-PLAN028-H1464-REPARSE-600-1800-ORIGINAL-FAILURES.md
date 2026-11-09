# PLAN028 H1464 | 原生五客户端600/1800已经真实运行：严格缺包、队列溢出与报告器变量覆盖必须分账

H1461 SOURCE `66fb6b4454b1ce4297ab04efa20c7f931ff12383` 原生 x86 原Go TLS443/Rust M4/ISA-L 一套已冻结机器码，真实 GitHub Action [42578056120](https://github.com/lly8666/wbd-next/actions/runs/42578056120) 的构建 PASS，600s job `129031068927` 和1800s job `129031068987` 均在各自独立Runner实跑到完结，结论均CI FAILURE，绝不是 NOT_RUN 或无停机证据。两份原始 ZIP `13656024788`、`13657785615` 都有五个独立认证客户端加服务端六份真实 `V4_PUBLIC_SHARED_TUN_STOP`，源SHA/三份二进制哈希manifest一致、ZIP CRC完好。

**600s产品真实缺陷：** Original Alice真实发送25.0→50.0→75.0→50.0Mbps，正确配置0%物理损伤、四个其他独立客户端各2Mbps；真实应用600s、全程精确按10+90+180+90+230=600秒分段。Alice下行原始唯一UDP缺32包，精确只在75Mbps的90s overload阶段，其他四阶段及所有用户其他方向零缺；server真实 per-/32 pending queue 8cap overflow=45（`direct_delivered`不含独立周期flush，不能拿 offered-direct 当失包）。所有六个 original Stop 完成。原产品H1461 >=6/8预flush最多8包补丁在该压力下**没有**解决丢包，此负面结果为 `FAIL_SCOPED`，不能作为优化完成。

**1800s不同维度：** 全部五个真实应用计时1800s、原Go TLS/Rust远端M4真实换代和旧owner Stop、终端六Stop成功，原H1274报告 `rotation_verdict=PASS_ALL_FIVE_SCOPED`、per-lease overflow0、原配置告警0。可是0% netem的Alice真实下行仍缺351唯一UDP包（阶段 [0,22,142,118,69]），所以连续性 `PASS_SCOPED` 不等于零损可靠性PASS；严格0%唯一数据完好项单列 `FAIL_SCOPED`，暂不能称整个1800s零丢包完成。其余4个客户端含原生真实1/5/15/30%物理netem与活动应用均在证据中。

**报告器一项确定BUG**：本轮在 `tools/m0-plan028-h1274-30min-report.py` 将配置相列表命名为局部 `phases`，随后在每方向构建输出 `phases=[]` 覆盖配置，导致两份旧报告的每方向 `phases` 都是空数组。600s独立新验收将其错误地判成所有用户 NO_GENUINE_UDP；1800s新验收在 `stages[-1]` 崩溃 `IndexError`。该问题与真实 32/45、351 UDP缺包分开处理。现在固定源产物，明确区分 `phase_specs` 和收集阶段 `phases`，fail closed 当阶段不是完整5段，且1800s 0%配置方向出现任何缺包单列硬门。复算工具仅从上述两份原始Action产物下载、解析、比较并保存新复审SHA，**不执行新网络、不重编产品、不改写任何原始产物**。状态直到H1464离线Action成功仍标注 `OFFLINE_RECHECK_PENDING`。

真正的大原因目前未归属：600s per-lease downstream Full有120次 + overflow45，表明下游处理接收速度低于短时真实输入；1800s原server per-lease overflow0但Alice downlink仍损351，证明**至少有不同于server 8-slot队列的丢包路径**，不可再把所有问题归咎一个队列缓冲或盲目扩容。下一步源锁隔离 raw RX/kernel/socket、original M1 worker、host CPU per-core和生成器TUN，优先180s同宿主定向对照，才考虑进一步产品修改。

原SOURCE548 Normal75原28缺包/5 queue overflow `FAIL_SCOPED`历史保留；其Windows600 `PASS_SCOPED`、ARM64 eef2两场1800 `PASS_SCOPED`仍源限，正式Windows+Linux Wintun原1800 `NOT_QUALIFIED`，H998热MTU旧FAIL，Android/物理 `NOT_RUN`。PLAN028仍IN_PROGRESS，严格禁止PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Only correct offline Python report variable shadow and per-source original archive strict forensic rejudge, no production product, wire, kernel or new network traffic."}
```
