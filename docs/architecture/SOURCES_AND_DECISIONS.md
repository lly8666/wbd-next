# 依据与取舍（2026-10-14）

## 原始聊天来源

本轮读取当前聊天的原始逐条 JSONL，而非仅依据压缩摘要。只在本机读取/提取助手的相关原始回复，未发布原聊天、机器凭据或业务正文。对应 2026-10-13 UTC（北京时间+8）的决策段落：

| UTC时间 | 主题 | 本方案处理 |
|---|---|---|
| 04:55:02、05:03:56、05:11:24 | 长期路径Rust、共享Game FEC、Normal off短路 | 保留，补实际源码/ABI/迁移边界 |
| 05:18:31 | 内核辅助 | AF_XDP等只作为profile证明后的可选项；kTLS不能满足此无HOL模型 |
| 05:43:20 | 多仓库并行 | 定为单workspace明确所有权，不引入运行时多进程开销 |
| 05:32:41、05:37:36、13:17:00、13:21:22 | 伪WS、冗余封装价值 | 用户已认为无收益，本轮不添加WS或VMess |
| 13:28:47、14:12:46 | 低损恢复数学、两次重试/预算/高BDP | 重新计算口径、反馈和资源上界；不把旧初估常量当不可更改硬门 |
| 14:38:14 | 稀疏例外、聊天中断恢复、并行日志 | 保留治理并补同机对比规则 |
| 2026-10-14 最新用户指令 | 只重构长期运行模块、编译复用、同Action顺序A/B、容量不足停重测 | 最高优先级，覆盖旧禁止顺序A/B的规定 |

与原项目对照的固定源码为 `a7a82db31fe736ffedee330795a3234d358f1984`。关键读取：`runtimeowner/recovery.go`、`fec/{fastcodec,fused_encoder,size_class_encoder,block}.go`、`tlsrecord/record.go`、`pathmtu/budget.go`、`datapath/game_owner.go`、`gamelane/gamelane.go`、`linkdata/{fec_path,datagram_fragment}.go`、`platformflow`、go.mod、STATUS与真实夹具说明。路径相对旧仓库；精确取舍见 MIGRATION。

特别纠正：旧FEC已有硬件加速；当前重传仍有旧20%等参数，不能说本方案10%已实现；旧MTU已改功能不等于压力资格完成；N4/N5/N6未收尾不能被架构文档写成PASS。

## 官方设计来源

| 选择 | 来源与理由 |
|---|---|
| GF256后端 | [Intel ISA-L v2.32.0 README](https://github.com/intel/isa-l/blob/v2.32.0/README.md)、[erasure_code.h](https://github.com/intel/isa-l/blob/v2.32.0/include/erasure_code.h)：自定义矩阵、x86/ARM路径、批量编码；FFI必须验证指针/长度。实现时锁完整commit和依赖hash |
| 不直接换GF16 | [reed-solomon-simd](https://github.com/AndersTrier/reed-solomon-simd)：GF(2^16)/Leopard对较大数据集很有价值，但不是旧k20 GF256 wire的直接替换；理论复杂度不证明小k更快 |
| 不把另一Rust RS当跨平台必胜 | [reed-solomon-erasure](https://github.com/rust-rse/reed-solomon-erasure)：需核具体SIMD平台/构建模式；本轮选兼容旧矩阵的ISA-L，避免无限库对跑 |
| 独立AEAD | [aws-lc-rs平台支持](https://aws.github.io/aws-lc-rs/platform_support.html)、[Windows要求](https://aws.github.io/aws-lc-rs/requirements/windows.html)、[AEAD API](https://docs.rs/aws-lc-rs/latest/aws_lc_rs/aead/index.html)：非FIPS，三种现有cipher，跨平台优化；不改bootstrap密码栈 |
| RACK/TLP思想 | [RFC8985](https://www.rfc-editor.org/rfc/rfc8985.html)：时间/后到达推断与尾包探测；只借算法，不继承有序交付或无限可靠性 |
| 恢复计时参考 | [RFC9002](https://www.rfc-editor.org/rfc/rfc9002.html)：RTT/ACK delay/PTO；本项目修复重用原密文，不照搬QUIC重封装新PN |
| RS概率模型 | [RFC5510](https://www.rfc-editor.org/rfc/rfc5510.html)：systematic MDS背景；本方案具体概率为独立丢失条件下推导，不是RFC对互联网的保证 |
| 低级I/O | [packet_mmap](https://docs.kernel.org/networking/packet_mmap.html)、[AF_XDP](https://docs.kernel.org/networking/af_xdp.html)、[kTLS](https://docs.kernel.org/networking/tls.html)：按实际设备/驱动能力选；不把Linux特性当跨平台免费提速 |
| 构建与边界 | [Cargo workspace](https://doc.rust-lang.org/cargo/reference/workspaces.html)、[profiles](https://doc.rust-lang.org/cargo/reference/profiles.html)、[Rust FFI](https://doc.rust-lang.org/nomicon/ffi.html)：同进程、固定toolchain/profile、显式ABI所有权 |
| Actions能力 | [GitHub hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)：平台可用性仍须实际manifest验证，不固定假定所有runner四核同型号 |

本轮不承诺“99%不可识别”、500Mbps已达标、Rust固定倍数收益或普通TLS同等开销。实际协议仍有包级恢复、FEC、复制、TUN与用户态收发成本。优化收益以成本账本和同VM配对证据判断。
