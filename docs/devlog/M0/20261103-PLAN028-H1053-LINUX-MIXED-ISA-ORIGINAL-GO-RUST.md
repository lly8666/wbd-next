# PLAN028 H1053 — Linux ARM64↔x86_64 交叉端点资格入口

用户新增要求：Linux 客户端与服务端今后可异构 ARM64/x86_64 交叉实测，不能假设两端 ISA 相同。H1053 不碰 wire/record/AEAD/PN/FEC/反馈、业务 owner 或 1460 外层默认，仅补原有原 Go TLS/Rust 产品 SOURCE 的跨 ISA 构建与真实 kernel netns 夹具。

新增一次双 ISA 构建：固定 donor Go `a7a82db` + 本仓库确切 `github.sha` overlays 与 Rust `wbd-engine`，Linux amd64 原生，Linux arm64 GNU cross toolchain。对每个二进制和 Rust SO 做 ELF e_machine+SHA256 manifest；两套源代码/编译/二进制绝不取旧 Action 的异源结果。两个并行 job 分别测 ARM64 **客户端**↔ x86_64 服务端、x86_64 客户端↔ ARM64 **服务端**。使用真正两个 netns、AF_PACKET/TUN、原 X25519 pre-ClientHello + TLS 证书校验 + 用户口令、单443和 protected auto /32、10 个实际 UDP echo、双方 owned Stop 与 MTU OS readback。不造 mock Rust owner、不逐包 Go 泵。

**资格界线**：当前 Linux runner 是 x86_64，ARM64 二进制由 `qemu-aarch64-static` 用户态执行；netns/TUN/AF_PACKET 为 Linux 真内核。这只能是 **QEMU_USER_EMULATED_ARM64_REAL_KERNEL_FUNCTIONAL**，不是 ARM64 物理真机、不同物理机往返、真实延迟、CPU/p99 或 FEC 性能 PASS。真实 ARM64 runner/硬件现有工作流保留，之后相同源锁二进制可在 native ARM64 执行。H998 在线缩窄 FAIL、ARM64 Game4FEC 旧 Action FAIL、远端 ICMP 未测及 CPU 因果未证保持不变。

新工作流仅在本文件相关测试源码变更或明确 workflow_dispatch 时启动，避免每次与 PLAN028 无关提交重跑长矩阵。本次候选要以两角色的独立 Action 结果/工件核 SOURCE 后再升级 PASS。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1053 source-locked dual-ISA original-Go+Rust Linux ARM64/x86 real-kernel netns reciprocal endpoint fixture, strict QEMU-vs-real-ARM performance distinction; Actions pending."}
```

## H1053 原生失败窄定位

H1053 构建 job PASS；两个互换角色 job 都在首次原 Go TLS 前失败，原始 ARM64 动态装载器缺 `libgcc_s.so.1`。H1054 冻结下载旧工件，不为测试夹具重建 Rust/Go。
