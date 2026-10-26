# 关键讨论、设计更正、性能结论与尚未归档事项

日期：2026-10-26。归档原则：这是由**现有可核对实验报告与本次讨论内容**形成的设计决策摘要，不是 ChatGPT 逐字聊天存档，不声称能恢复所有未留在源码/报告的思考、临时方案或生成物。总索引见 [INDEX.md](INDEX.md)。

## A. 需求如何变化（阶段性决定）

1. 最初研究成本更低的 XOR 模拟 TLS-like 记录；要求即使原始内容相同，外部同样的包也不总是字节完全相同。先测按外层 PN 派生公开重复 64 位掩码、64 位批量 XOR。
2. 为保留协议边界，讨论“已确认 TLS1.3 应用稳态走快速模式，其余包括握手、未确认流量和重传走 AES-GCM”，并做理想分类器（trusted offline oracle）A/B。未实现真实网络分类器；不能仅从外层 0x17 推断 TLS Finished，11–21秒延迟也不构成握手完成证据。
3. 曾把 mode 放进受 AES 保护的 8B PN 高位，使外部不再暴露独立的 clear mode 字节，并测试了 x86/ARM 额外成本。后来**明确取消复用 WBD protected PN 的要求**；这些是历史对照而非现在最终线缆。
4. 研究 V2Fly VMess security=none 和 zero：NONE 默认在 TCP chunk 模式通过 SHAKE128 掩码处理每个2B分块长度，但**业务字节本身明文传输**；zero 关闭分块/长度掩码。额外讨论 VMess+WebSocket 客户端到服务端4B随机WS mask的公开 XOR、反向无需 WS mask，以及 WS/WSS 的区别。未做完整 VMess WS/TLS 系统 benchmark。
5. 发现少触碰业务数据可显著节省 CPU，于是改用**原始已确认 23 TLS 记录直通，非23和被分类为重传的23记录先 AES-128-GCM，再使 wire 记录 type=0x17**，以及尾部2B marker。这个结构为单向端到端 TLS 应用数据保留原本加密性质，但不代表自定义传输成为标准 TLS1.3。
6. 起初对“最后8位”按1字节做了测试，后来用户明确纠正：**最后8字节**，建议以单次64位 XOR 实现。
7. 初版测试错误地给原始23记录**再增加了一层5字节TLS-like头**。用户明确纠正并要求：**原本就是完整TLS23的输入必须保留自己的唯一头，不增加外层头**；只有AES回退才生成新的5B TLS-like头。修正后有原生测试和TCP PCAP佐证，没有双层头。
8. 新格式必须把尾部2B marker计入当前TLS-like record的长度；Fast RX 必须先逆 XOR、剥 marker、将TLS头长度减2，再把原始已认证TLSCiphertext交给内层TLS。尾部8B XOR修改了原有TLS AEAD tag的后6字节，普通TLS终端不能直接读原始网络数据。AES回退是自定义AEAD帧，不等于真实TLS1.3会话。
9. 做真实 Linux socket→tcpdump→TCP字节重组，抓100条custom记录+真正Go TLS1.3对照。记录级格式/长度100%有效，无多余TLSlike头；原始80/20 fast/AES形成长度1347/1368B的双峰。在同一个捕获的自动TShark识别中custom全部显示TLSv1.2（仅记录层识别），真正Go TLS1.3握手流后33段显示TLSv1.3；**不能将“会被识别为 TLS record”误称为“与普通TLS1.3完全一致”。**
10. 最后用户希望以最低系统开销把这套新 wire 接入 WBD：**初期不接 FEC、GameMode；尽量复用原 Go 已认证会话及密钥、M1 内存池/冻结范围、M4 TCP-like RAW 批量发收、route/MSS/MTU和双向 worker**。不允许原有 WBD AEAD record 再套一层；新 Rust Tail8Codec 尚未编写。
11. 检视主线后明确两个不同产品入口：**完整L4 TLS记录模式**可按现行fast +2B、fallback +23B零额外整包复制；**WBD原TUN IPv4包模式**包含原IP/TCP元数据，一个TUN packet不能等同于一个完整TLS record。如保留IP VPN，必须设计无损 IP/TCP sidecar/流重建，或先把完整TUN包全部AES回退。仅靠2B marker无法还原任意IP包。

## B. 实际原生 A/B 的数值（全是最小程序，不是WBD整机性能）

所有相应基准均对每个原始1345B数据包执行**发送编码+接收解码**，一轮100包；以下为已经存入各自 FINAL_REPORT 的五轮均值，除特别说明外均为 Go 1.25原生机器上的不同测试程序，**不得跨不同程序直接当成相同严格实验对照**。

| 实验 | x86_64 ns/100包 | ARM64 ns/100包 | 来源 |
|---|---:|---:|---|
| VMess NONE SHAKE128 2B mask | 5246.4 | 10533.0 | lan-vmess-none-compare |
| WBD 隐藏 PN 模式的完整旧型 PN-XOR | 26481.0 | 37659.2 | 与上行同一运行 |
| Go 批量 XORBytes 优化的 full PN-XOR | 25478.4 | 29821.2 | lan-pnxor-optimized；相对该轮其 baseline 42845.4/34906.8 |
| 最初尾部marker 99%直通、尾部**1字节** XOR | 5384.4 | 9430.2 | lan-tail-marker-rolling8-cost（旧双层头） |
| **最后单层原始 TLS23 头，99%直通，最后8字节word XOR** | **7712.4** | **9907.8** | lan-tail-one-header-8byte |
| 同单层头，95%直通 | 10980.6 | 13236.0 | 同上一实验 |
| 同单层头，80%直通 | 23135.4 | 25745.8 | 同上一实验 |
| 同格式100% AES fallback | 87967.0 | 91861.6 | 同上一实验 |
| 单层头同跑 full PN-XOR 对照 | 20327.6 | 24372.4 | 同上一实验 |

结论：在人工保证 99% 输入为**完整已确认 TLS23 record**的前提下，单层头+尾部8B word XOR相对本轮 full PN-XOR 对照为**约2.64倍 x86、2.46倍ARM**；不过真实WBD TUN路径的分类成本、收发syscall和分片可能改变整体收益。所有这些阶段**没有完成真正的双主机 1/2.5/10Gbps LAN 测试**。

## C. 当前拟定的 wire 摘要

- Fast（只限完整有效且可信分类的原 TLS23 record）：原完整5B TLS头+原 encrypted body，长度字段加2；尾部2B marker；尾部最后8B一个rolling u64 XOR；无第二层TLSlike头。1345B实验输入输出1347B。
- AES fallback（其他/真实重传）：新5B TLSlike header + 1345B in-place AES-GCM +16B tag +2B marker；尾8B word XOR。1345B实验输入输出1368B。
- 两分支marker数值域在其公开tail XOR逆变换后可被观察：不提供加密或完整性。AES路径自身拥有 GCM tag，fast依赖恢复后真实TLS的端到端认证，WBD本身并未验证fast来源真实性。
- 不复用 WBD 保护PN。关于以本来已有的FakeTCP byte-stream seq64替代独立隐式滚码计数的做法只是**架构建议**，尚未实现/未重新抓包验证；改变滚码输入会改变wire bytes，且要解决重排、回绕、恶意伪造、nonce唯一性与重连。

## D. 证据/生成物的实际归档层级

**已在 Git：**所有索引中逐项指向的源代码、CI workflow、分析脚本、报告/部分status.json、这个关键决策总结、WBD接线设计。

**Git 外且受时限约束：**GitHub Actions 的原始benchmark TXT、tcpdump实际PCAP、tshark TSV、外部 artifact ZIP和一部分Go运行输出。实际PCAP归档标识：run 40268297939 / artifact 12627636543。Tshark auto vs forced 审计：run 40268945000 / artifact 12626843821；对应工作流写有30天 retention。该事实不能描述成“已永久保存在Git分支”。

**并未记录成可恢复逐字内容：**我们的所有聊天问答、所有临时建议、未曾提交的候选草稿、临时下载物/截图。此文仅总结最关键的设计决定，不可冒称具有逐字转录/审计法律证明效力。

## E. 仍未实现的重要事项

- 完成 Rust new Tail8RecordCodec / 主线产品级 Go-Rust owner TX/RX 接线 / 真实 TCP-like M4 双端发收。
- 可信 TLS1.3 record/Finished 边界及重传判别；TUN 的 IPv4/TCP sidecar 或完整 fallback；多TLS记录/单TCP分段对齐；超长TLS记录与真实peer MSS。
- 新记录协议的双方认证协商（现有V4 Go 功能集受限）、nonce绝不复用、out-of-order / loss / reconnect / replay、fast模式安全边界、主动篡改/降级防御。
- 两台实体LAN设备实际 p50/p99 CPU、吞吐和数据平面验证；外部原始PCAP永久保存策略。

**维护约束**：今后若本用户再讨论/实现新版本，务必同步追加这个文件和 INDEX，记录运行commit、Go/Rust源码版本、原始证据所在地、成功/失败结论，避免把用户纠正过的历史错误设计当成最终设计。
