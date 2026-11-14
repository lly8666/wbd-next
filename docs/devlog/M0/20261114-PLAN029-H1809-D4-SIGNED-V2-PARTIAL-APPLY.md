# PLAN029 H1809｜D4 一个真实 no-WFP 四阶段 OS 部分 Apply 失败/恢复

- 在 H1808 signed D3 多A独立 Action 仍编译时，采用不同 Windows2025 VM 的独立小场景，**不重复 H1697 正常四阶段完整 Apply**：真实签名 Wintun 与本机/代际 WAL 事务按 original Go pinned assembly，真实 stage 0=lease、1=MTU 落 OS 且独立 Inspect=Owned；第三 DNS stage 采用仅测试封装，**在 Win32 写之前有意返回可辨错误**，持久 WAL 应精确为 owned lease / owned mtu / intent dns，routes 未开始。沿现有 `Recover`/finally 完成反序CAS恢复，验证原 OS baseline、parent/route sidecar 不残留；不删除不属于本项目资源，不关闭防火墙。
- 这个有限案例只覆盖一种有界部分Apply假设，不模拟真实机器掉电/任意第三方修改，不给 v2 Ready/GUI 或真实双出口背书。故障前如果第一阶段/OS定位失败，按真实首错 FAIL 留证，绝不让故障注入掩盖先前错误。
- 同一 H1809 交付只涉及真实测试 fixture + 既有专用 H1697 Action 脚本与 cursor，正式 OS writer 无改动；H1808 D3 和 ARM64 旧 ACTION 不重发，H1809 最终资格待原 job/artifact SOURCE。剩余 IPv6/D5/P1/P2/Game4 Direct Mode 继续 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Add one generation-owned signed OS partial-Apply fault-injection verification to existing v2 Win32 test fixture; no product stage writer or default changed."}
```
