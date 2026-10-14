# R0 实际固定旧Go tlsrecord 外帧与Rust受保护片段解析—原子计划

2026-10-14：交接前远端main HEAD `d173aa02ad8eae82b8fab723eb01ab044dd3eac4`，M0 cursor seq14 checkpoint `e8b8125022333cb9818e734973da8ec179400f95`→HEAD仅一个cursor-only H；最终Governance38522202227成功，近期Actions无未完成、无open PR，M0 active/main/epoch1/rev1，CLEAN。

**why_now**：05要求沿用固定旧Go tlsrecord，00要求Rust wire显式offset/golden；现有Rust codec只有WBC4/WBG4，尚无TLS-like record外帧。真实AEAD/HP未引入，严禁用明文PN的样板代替真实record或把解析成功当认证/交付。

**锁定真实来源**：原Go `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` 的`internal/tlsrecord/record.go`与`decoder.go`；其`vector_test.go`原有5个独立wireHex（PN0/1/跨32位/MAX-1/MAX）和9B padded黄金记录在`r0/fixtures/legacy-record-wire-v1.txt`。不是Rust本地数学模型造出的密文：新Go test fixture复制进固定旧checkout，调用原真实`sealRecord(...)`和`OpenRecord`，逐字节核对fixture完整加密wire并验已开密PN/kind/payload；Go另一测试使用真实`Decoder.OpenPayload`确认坏长度停止不扫描后续。原旧仓库不写。

**Rust最小范围**：在`wbd-codec::record_frame`新增纯wire`split_one`和`outer_header_for_body`，5B outer=`17 03 03 lenBE16`，8B protected PN(不可读取为PN)，offset13起opaque ciphertext+16B tag，最短body26/record31、最大body16640；HP sample为opaque ciphertext前16B，最短记录时可跨入tag。单次split返回opaque borrowed view+其后slice；长度不可信立即err且不向后扫描magic；不把单条struct dump成wire、不试图解出encrypted kind(仅authenticated plaintext offset0，kind0/1)。测试6组：固定Go oracle的全部布局；组合多record边界/坏长度终止；min31与全截断；type/version/len/MTU预算；HP短样本与tag重叠；PN不可未掩码、kind仅在认证后可见。

**流程**：Github Actions Ubuntu24.04 Linux x64 依锁Rust1.85.1、Go1.23.12、固定旧Go SHA。build只编译现有Rust codec单测二进制与原Go tlsrecord真实单测二进制；manifest记录源码/run/attempt/toolchain、原Go SHA、fixture与所有输入SHA256及两份二进制长度/hash。独立consumer严格对账下载的原二进制并分别运行Rust6组/Go2顶层组，不编译重跑。已有WBC4/WBG4的13组在另workflow用`--skip record_frame::`保持原本的独立计数。Cargo workspace不变，source-lock不变，依旧会运行受影响Rust codec、cross-target及qualification audit回归。

**done_when**：真实Go Seal/Open与Rust opaque结构6+2组、所有本次触发的Actions绿色；精确SOURCE/run/artifact/hash/剩余NOT_RUN证据，独立H。错误则只修最早可解释断言；不得把未实现Rust3cipher/HP视为PASS。R0总体仍partial、Go生产V4 fail-closed、M1–M4 reserved。

**唯一下一动作**：在R0下推进尚缺的LINK/FEC wire/MTU外头原Go golden和显式offset基础反例（L01）；不提前以伪FEC/伪AEAD变成业务资格或自动激活worker。