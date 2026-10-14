# R0-CONTRACT-001：控制入口V4 fail-closed接线（本轮原子范围）

**为什么现在做**：M0 seq7 唯一 next_action 指向旧Go真实控制调用点。之前非测试V4 TLS入口在固定旧Go源码下通过5组双方测试，但旧runtimeentry/data plane仍是V3语义；将测试的`DataPlaneReady=true`直接转给旧生产CLI将错误广告未实现receipt/Game，是fail-open。

**基准**：`lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`，Go1.23.12 Linux x64；不写旧库。Action `r0-go-control.yml`检查三个真实旧Go文件的blob SHA及一处一处精确锚点，在runner临时checkout里插入，并加入`r0/go_overlay/internal/runtimeentry/r0_admission_mode.go`及上轮已存在的`admission_v4.go`。

**真实接线**：
- Linux CLI客户端、服务端均新增`--admission-version`，默认3，配置JSON沿用原`configfile.ApplyFile`参数空间，帮助明确V4能力未就绪。4永远在身份/网络操作前拒绝（没有隐含降级）；其余不支持值拒绝。
- `runtimeentry.DialTunnelClient`（实际DialTunnelClient调用）和`runtimeentry.NewLifecycleServer`（实际NewLifecycleServer调用）增加`RequestedRecordVersion`防护；直接Go library调用同样无法绕过。显式3验证真实V3 policy/RequireV3；zero保留旧测试与兼容调用者行为。接入V4入口前需要独立Rust引擎ABI readiness证据，绝不相信配置开关。
- 旧服务端`--check-config`输出`effective-admission-version=3`、`v4-capabilities=not-implemented`且保持原密码和route-key脱敏。客户端无对应`--check-config`，仅通过flag和入口防护；该CLI全平台迁移后续验证。
- **epoch store和自动lane ReleaseLane不应虚接**：旧Go V3的session不带V4 epoch，无法正确释放。真正V4生产路径被禁止，因此没有V4 epoch store实例；需在Rust数据面接入且显式提供生命周期事件之后才完成，不能借用测试夹具冒充接线。

**本轮done_when**：固定旧SOURCE精确patch后编译runtimeentry和realityfront两个Go测试二进制及Linux两CLI共四产物；consumer先验二进制与源码hash，跑runtimeentry fail-closed单测、旧V3真实TLS兼容反例、两CLI拒绝及server真实`--check-config`；记录精确Actions结果与剩余边界，独立cursor-only H。

**资格限定**：通过仅证明Linux控制入口的V4闭锁和V3兼容，非V4产品接通。Windows CLI、Rust ABI/平台ABI、epoch ReleaseLane实际事件、真实V4应用接线、产品与性能物理都NOT_RUN。

**唯一下一动作**：完成原生Go↔C↔Rust版本/size/opaque token ABI最小探针（Actions实际编译/调用，跨版本和错误路径），以ABI作为未来V4 readiness的必要前提；保留当前生产V4关闭直到Rust receipt/Game与生命周期均就绪。
