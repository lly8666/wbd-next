# PLAN028 H1510｜Windows5 中断收口：shared/manual账户冷路径漏接

- 基点：cursor H1509 SOURCE `8e5f313fdb40c9ecf55c052db85c7abf3819306c`，main仅增一项文档提交；Action [42765555239](https://github.com/lly8666/wbd-next/actions/runs/42765555239) 已结束。Windows loss0 job129662640456、loss30 job129662640430 均 Action FAIL，产品实际业务 **NOT_RUN**。
- 首故障：真实 Linux 原生服务端完成 `V4_PUBLIC_MTU_PREPARE`、TUN txqlen/fq 安装后，**在** `V4_PUBLIC_MIXED_MULTI_SERVER_READY` **之前**退出：`realityfront: V3 policy unsupported by this build`。两场均未触发 TLS、M4、UDP/TCP、netem、轮换和 Stop 条件；不能将宿主前置 PASS 当五客户端业务 PASS。原始失败及 Windows/WSL2 驱动前置正证保留。
- 整条链：夹具原本即使用 `--users-file` + `--manual-client-leases-file`、每账户/32、非零手动 tunnel；现行 `runGame` mixed guard 限定 pool；`runGameServer` 不进入 manual-map shared；`runGameMultiServer` 检查及 TLS `ValidateRequest` 只认 pool/单例；`V4AuthenticateLinuxMixedServerLane` 不准 manual 且没有把原有 `V4ServerOptions.ManualLeases4` 传入，导致启动前和身份后的串联阻断。
- 最小修复：同一个 Go 冷共享端口复用已实现的 `originalV4ManualAccountTunnelAfterAuth` 和 `v4ServerSelectedManualLease4`；只允许受保护身份认领事先配置的唯一/32，启动时一项地址 authority（pool、单例或 per-account），在既有 `EstablishServerV4` 后绑定 Rust owned /32。现有 Game / Normal M4 路由、TUN 分发、MTU、后续 Stop 原封复用。未改密文/record/FEC/热路由。
- 添加真正调用 `runGame` 的无网络冷入口测试以及夹具接线静态回归；只覆盖入口与编译，必须原生 Linux 侧 build/test + Windows2025 实际故障触发后才可升级产品资格。
- 下个区分实验：先确认精确 SOURCE 的原生 Linux Go 测试与 build 通过，再使用**一场** loss0 Windows5 真实原生 Action 验证 server READY→五账户 TLS→双端 M4→MTU→业务→物理轮换→Stop；如 loss0 过硬门再独立 loss30。原失败不删除；原 ARM H1505 1800s 业务可复用 `PASS_SCOPED`，其 reporter enum 的 Action FAIL 保留。028 整体仍 **IN_PROGRESS**，Android/物理未跑另列。

```feature-impact
{"kind":"updated","reason":"PLAN028 shared TLS443 protected per-account manual /32 routing is a tracked multiclient capability; record the original pre-READY FAIL and the as-yet-unverified new Linux Go cold owner connection in the existing feature card, without promoting qualification.","ids":["tls-auth-multiclient"]}
```
