# PLAN026 M0｜Windows Fixed/Auto Rust NativeOwner 直接接线（代码候选，尚未测试）

2026-10-29；同 main 任务 `R0-M0-PLAN026-WIN-RUST-NATIVE-IO`，不新开 epoch/分支。本批代码是在用户要求“先整批写好，再跑测试”的**部分施工进展**，不能视为完整 Fixed/Auto/Game/Keepalive 实现或任何同源产品 PASS。

## 修改与动机
- `v4_windows_native_runtime.rs` 将已有 Normal/off 两worker 扩成 NativeAttachV2 Fixed/Auto 模式，复用相同 M1/M2/M3/TunnelOwner。新源 IPv4 立即封成 kind2、真实 NPF 接收回执进入原成熟 M2；partial parity≤4 行按 Rust FixedStream 真 deadline 分批出队、真实 NPF accepted prefix+uncertain/not-sent 结算；真实 kind2/3 接收使用现有 Fec2LiveRx，多源恢复交给相同 Wintun，借用资源由已有 native stop/join 归还。V1 192B ABI 未改；不创建第二个 Go packet callback/线程。
- 原 Go bridge 增加 16B typed NativeAttachV2 wrapper，附 Go ABI 回归；`m0_native_v4_windows.go` 默认 Fixed/Auto 不再进入原 Go packet pump，旧Go保留明确同机A/B Normal对照，原TLS/OS/WAL与 StartNativeIO/Stop 接口不被替换。Auto暂继续**已有**2s Go单策略 actor/原 Rust M2 mature readback：Rust政策actor、Health和动态lane仍待后续编码，不借“Go纯冷层”词语冒充完成。
- 默认产品关闭1Hz Go heap/GC JSON telemetry，只有Actions或`WBD_NATIVE_TELEMETRY=1`按1s采样；普通运行30s cold OS/MTU状态检查。Linux Auto监控器周期从200ms改为2s，真正的策略决策本就是2s一次，避免额外Go wake。
- 更新有影响功能卡及源装配manifest固定 `bridge_v4_windows_native_io*.go` 结果blob，保持旧原Go来源和权限/签名OS方案不变。

## 施工/资格界限
**暂不发起 Actions。** 仍须写齐 Game2/4 多 capture Rust RX、共享TX/独立PN、Linux双端合并认证 Keepalive/Health/Quality、服务器失联/FIN休眠/唤醒、V2模式化夹具与真实监测点/帮助、更多单元保护；随后固定SOURCE批测 Fixed→Game→Auto最后（Keepalive与超时同测）、同机A/B。旧FEC W168 56case/250M与W103 Game只是原SOURCE的矩阵oracle；不能平移PASS。不能宣称生产修复CPU、低延迟或物理完成。

```feature-impact
{"kind":"updated","ids":["fec-fixed","fec-auto","windows-native-transport","linux-raw-tun"],"reason":"Windows Fixed/Auto candidate native steady I/O, Go diagnostics cadence, Linux Auto observe cadence and verified source assembly fields changed. These are UNVERIFIED code changes, not new qualified feature PASS."}
```
