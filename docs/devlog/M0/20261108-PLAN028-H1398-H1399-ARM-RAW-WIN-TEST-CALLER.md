# PLAN028 H1398/H1399 — 只离线补证原 ARM64 黑洞及 Windows 单测调用方

2026-11-08。原 source`98c10665` 因本批 Windows Fixed/Auto 原 ISA-L helper 返回 `(length,BackendUsed)`，遗落了一处已有完整 original FEC 恢复单测 `symbol[..count]`；[自动 CI](https://github.com/lly8666/wbd-next/actions/runs/42483199643) Rust `E0277` 编译 FAIL，签名 Npcap/Wintun 真实业务未跑，判 `HARNESS_OR_CI_FAILURE / NOT_RUN`，不赦免真实编码。H1399 同时修此原调用方并增 native 链接时 `BackendUsed::NativeIsaL` 严格断言、无 native 仍 Scalar。原 M1/M2/record/Stop 合格门不变。

用户授权外因真实业务可 PASS_SCOPED。此前 H1395 严格只读 `h1353-physical-game4-blackhole.json`，原 [H1368 ARM64 Action42475183088](https://github.com/lly8666/wbd-next/actions/runs/42475183088) **产物漏传此 JSON**，H1395 报告器标 NOT_QUALIFIED；但对原始 37 文件 ZIP 的 `h1368-native-game4-correlated-traffic.log` 核验发现它**明确留有原进程打印的真实 `tc -s` 内核计数及 monotonic 开始/撤损戳**：t+70.017064至78.028773s，两个真实 egress drops uplink26109/downlink26197，原始保护流的 Dave 上下行业务同时 TX各1,050,112B / RX=0；窗口后真实 app 首次各约141ms。其他四原认证 session 黑洞窗口业务不断，五原 Windows无关 Linux clients Stop、server TUN Stop、租约队列无溢出。所有源有已归档原 Go TLS/Rust log、十条双方真实 veth PERMANENT readback，不依赖生成的事件文件。

故原业务实际功能按场景可判 `PASS_SCOPED_NATIVE_ARM64_GAME4_REAL_CORRELATED_BLACKHOLE_RECOVERY`，同时保留原 Action CI FAIL、事件单文件存档缺口和历史 H1395 JSON-only 判定。H1398 只让既有 ARM 审计在单文件缺失时解析原始**完全匹配、唯一** stdout 控制台事件；绝不制造 event JSON，核原时戳、两方向真实 kernel drops、原 application 10ms 完整、兄弟及 Stop，离线新独立 Action 严格校验。与正在执行的 Windows 原生 Action 不共VM，无网络重跑。

```feature-impact
{"kind":"none","ids":[],"reason":"Existing complete original recovery unit test adjusted for internal backend receipt and raw-console offline re-audit; no product wire/ABI/algorithm alteration."}
```

## H1398 独立离线 Actions 结果（原网络没有重跑）

[Action42483793828](https://github.com/lly8666/wbd-next/actions/runs/42483793828) 已结束 SUCCESS，其唯一独立 job 下载原 H1368 原始 37 文件 ZIP，直接审计真实 console 内核计数与 original 19001×10ms app bins、5 Stop；严格输出 `PASS_SCOPED_NATIVE_ARM64_GAME4_REAL_CORRELATED_BLACKHOLE_RECOVERY`，`event_provenance=ACTUAL_ORIGINAL_PROCESS_STDOUT_TC_KERNEL_WITNESS`，原 event JSON 仍缺失、不伪造。原输出 ZIP CRC PASS SHA256 `9362d2a71d3d9936fab86a285e5edf08c72d8724b335e57deb0069577be3ce54`；零故障、零容量异常、保留原 CI FAIL、正常 lane Rotation NOT_TRIGGERED。

同批独立治理质量：`g2_bootstrap_bundle.py` 历史源身份校验把 registry revision 固定为 PLAN020 的3，然而当前用户 2026-11-07 授权 PLAN028 功能冻结 registry 实际为 rev4，M4 撤销/历史 rev2 cursor 并未改变。引擎源码变化本来就触发 G2 bootstrap，因此旧硬编码每次都报 `ValueError: G2 registry revision changed`，只修为精确 rev4；其五 crate/source SHA/真正测试二进制校验、所有角色/worker检查不放宽，不重新派发网络。
