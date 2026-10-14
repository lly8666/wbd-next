# R0-CONTRACT-001：原生 Go↔C↔Rust ABI 原子探针（M0）

**why_now**：cursor seq8 在生产 V4 明确关闭的前提下要求证明跨语言 ABI，不再用 Python 计算或 Go-only TLS fixture 代替。这一步固定接口所有权，避免后续各 worker 各自定义大小/opaque token。

**SOURCE 与边界**：新源码以执行 Actions 的 push SHA 为准；Go 旧模块必须 `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`；Rust 1.85.1、Go 1.23.12、Ubuntu Linux amd64 native；Cargo.lock 完全锁定当前无外部 crates 的 workspace。仅本仓库 `crates/wbd-engine` 可导出 cdylib ABI，`wbd-types` 保持 Rust-only，`r0/abi/include/wbd_abi.h` 为对应 C 头。该 engine 当前是 R0 空能力 sentinel，**不包含真实业务收发**，features 强制0；名称带 `r0` 防止误用为最终产品接口。

**布局**：ABI v1；`WbdAbiInfoV1` 24B、`WbdAbiConfigV1` 16B、engine/lane token 各8B；导出函数显式校验 query/out size 和 open/config size（在读取 config 前校验 ABI 旧 size），再验 version、flags、reserved，全部定宽 C types。Rust opaque token 不压指针，generation 32位且即将回绕永久退休槽，engine/lane token 通过不同 tag 隔离；engine close 强制让所属 lane 失效；复用时旧 token 必须 STALE。资源上限仅探针4 engines/16 lanes，不是最终容量或业务架构性能承诺。

**错误 contract**：0=OK,1=NULL_ARG,2=BAD_SIZE,3=BAD_VERSION,4=UNSUPPORTED,5=STALE,6=NO_CAPACITY,7=INTERNAL；不发出 Rust BufferKey/裸对象地址，失败不得输出新可用 token。R0 只有 init/lifecycle, 业务错误层次留后续正式 engine。

**真实 Actions**：一次构建 Rust release cdylib、预编译 Rust tests、原生 C executable；将 bridge.go 与测试注入固定旧 Go SOURCE `internal/r0bridge` 编译 cgo 测试二进制。build job 不执行测试，consumer 下载并验证四个 binary 的 SHA-256/bytes 与每份输入 SHA-256、双SOURCE/run/attempt/架构，设置运行时库查找路径后只运行预编译 Rust/C/Go。通过测试名称和日志确认原生调用而非 Python 等价替代。旧 Go 代码不写回远端。

**本原子 done_when**：上述原生 Rust/C/Go 实测绿色，包含 ABI 旧size、新旧version、NULL、unsupported、stale/duplicate/parent close、generation 极限与容量；记录精确 SOURCE/run/artifact/未覆盖；独立 cursor-only H。失败必须真实记录并精准修复后重测，不循环换 seed。

**未覆盖**：真实Rust steady engine/data plane、Go旧控制实际链接 cdylib、Windows与ARM目标、真实驱动、async callback/send uncertain/fake clock、生产V4能力、Windows UI/GUI、产品/性能/物理一律 NOT_RUN，不激活 M1–M4。

**唯一下一动作**：以经过 native ABI 证明的 token 与版本为基准，补 R0 fake-clock 与 platform fake-driver 的发送 prefix/uncertain/关闭借用探针及 Linux→Windows/ARM 多目标 build/ABI 检查；未完不声称 R0 全部完成。
