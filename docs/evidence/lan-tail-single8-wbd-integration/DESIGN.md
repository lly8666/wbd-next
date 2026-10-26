# WBD 单层 TLS-like 尾部 8B XOR：低开销接线设计

状态：已检查 main 相关收发源代码。本文件是设计方案，不是已经接线的产品。独立设计分支；main 未修改。源自已通过 TCP socket/PCAP 验证的 single-header 实验。

## 1. 正确的接线位置

沿用已经认证的 Go V4 会话 / exporter / 私有 Detach、Rust owner generation、M1 预分配缓冲区、原 M4 TCP-like IPv4/TCP driver、路由 MSS/PMTU、双向独立工作线程、sendmmsg/recvmmsg、Stop/lease。不要重复调用旧 WBD RecordCrypto::seal_in_place，否则又会多套原来的 5B header + 8B protected PN + AEAD/tag。替换为新的单独 Tail8RecordCodec。

禁用 FEC 和 GameMode 实际工作路径，先只接收 Normal data；若产品仍协商 V4，注意 V4 认证特性位默认值 3 中 Game 位是必需位，不能仅仅将协商 Features 改成 1。新 wire 格式必须用双方认证明确协商的协议版号或独立功能开关。

## 2. 不能忽略的输入语义

本次成功的 PCAP 实验给编码器喂的是 *完整、边界明确的 TLS 23 记录*。WBD 现有 TUN 输入却是完整 IPv4 datagram（常见首字节 0x45），其中包含 IP/TCP 头部；内层 TCP payload 可能只是 TLS 记录的一段、多个记录、含重传或乱序数据。

因此不能在原 TUN 入口检查 buffer[0]==23 并直接只转发 TLS record：这会丢失原始 IP/TCP 头部，而且无法从仅 2B 的 mode marker 恢复一份任意 IPv4 包。若保持 TUN VPN 语义，必须额外传输原 IP/TCP 头或经过可靠的流状态重建和 delta 压缩。不能声称 TUN 模式直通只多 2B。

**推荐先做 L4 TLS-Record Mode**：Go 已认证的 WBD transport 上，应用层源端提供完整 TLS23 记录，并由应用层 sink 收回原始 TLS 记录。这与实验 exact wire 相符；暂不启用 TUN worker。需要 IP VPN 时先将 TUN 全 IPv4 payload 作为 AES fallback 接入，随后再研究可信 TLS 流分类及 IP/TCP sidecar。

## 3. Rust 发送的低开销 slab 内存布局

主线 Rust 已把小包放到现有 M1 slab 的 [14..14+n]，且 memory/mod.rs UniqueBuffer::freeze(range) 允许 range.start 不为 0，FrozenRecord::bytes() 按原范围向 M4 借用实际记录字节，**无需为了生成记录再 memmove 一次完整正文**。

- L4 fast：输入 [14..14+n] 已包含其自己唯一的完整 5B TLS23 头；原位修改该头的长度 +2；在 [14+n..14+n+2] 写 2B 标记，最后 8B 一次 u64 rolling XOR；freeze(14..14+n+2)，不额外增加第二 TLS 头；输出 n+2。
- AES fallback：输入 [14..14+n]，使用空闲的 [9..14] 写新单层 5B 23 03 03 头；在 [14..14+n] 原地 AES-GCM，尾部 [14+n..14+n+16] 追加 16B tag，接着 2B marker；最后 8B u64 XOR；freeze(9..14+n+18)，输出 n+23。
- 已有 TUN small worker 会先从 jumbo scratch 拷贝一次到 slab；这里只保证 **不再额外拷贝大数据正文**，并非端到端完全零拷贝。
- RX 使用已有 raw recvmmsg 放入 M1 slab 的字节切片，原地逆 XOR 后解析 marker。fast 去掉 marker、还原原 TLS record header length 再交给真实 TLS endpoint；AES fallback 同片 Open 并校验 AAD；不能把未加 WBD 外层 MAC 的 fast bytes 当成已认证 IPv4 交给现有 write_authenticated_ipv4。

## 4. 无 WBD protected PN 的滚码与 nonce 同步

不需要复用 WBD 原 protected PN。建议第一版探索复用 *本来就存在的 FakeTCP 64-bit absolute byte stream start seq* 作为 per-record rolling key / AEAD nonce 的输入：TX owner 已有 next_tx_seq；RX driver已有 seq32 和 extend_seq32。这样在未接收到个别 FakeTCP datagram 时，不会因为按“收到几条 record”自增隐式计数导致后续包持续解码失步。

约束：每方向/epoch 必须使用独立 AEAD keys 和 domain separation；AES nonce 在同一密钥下对不同 plaintext 必须唯一，异常失败消耗该记录身份，重传必须重发相同 FrozenRecord 字节；seq32 rollover、RX anchor、伪造/replay、重排/恢复需要 fail closed 测试。这里改用 seq64 派生，相比过去按独立 packet counter 派生，会改变线缆 XOR 字节，必须协商新版 wire 和重新进行 PCAP/兼容性验证。公开 rolling XOR 不能提供 fast 数据的完整性认证。

## 5. 主线精准模块和改动

| 主线位置 | 复用/调整 |
|---|---|
| crates/wbd-engine/src/v4_embedded_go.rs:background_tun_once,background_raw_once | 单独实验 worker 保留现有 32-slot batch、Route cache、M4 driver；不要每包 Go FFI 或重复 mutex |
| crates/wbd-engine/src/v4_owner_crypto.rs:seal_scoped_authenticated_one,consume_original | 新 Tail8Codec adapter 承接 owner 的 seq64、M1 slab、Frozen metadata；不再经过旧 AEAD sealer/opener |
| crates/wbd-codec/src/record_crypto.rs,record_frame.rs | 不全局替换旧 31B FIXED_WIRE_OVERHEAD 常量；为双尺寸新 wire 增加独立 codec/framer |
| crates/wbd-codec/src/path_budget.rs | FEC/Game overhead=0，但仍应按最坏 fallback +23B 预留 record headroom，并受 peer MSS、route MTU、outer IP/TCP 头限制 |
| crates/wbd-engine/src/memory/mod.rs | 直接使用有效 nonzero freeze range，冻结原 unique slab |
| crates/wbd-platform/src/linux_raw_carrier.rs,rx_ipv4_tcp.rs | 不改变 raw TCP-like 头和 checksum；保留绑定的 peer tuple 和实际 syscalls，利用外层已知 seq32 |
| r0/go_overlay/internal/realityfront/admission_v4.go | 已认证密钥和 scope 继续保留；新格式必须显式双方授权，不能靠 marker 猜测协商 |

M3 LINK 分片并不等于 FEC。即使不需要 FEC，超过 peer MSS/PMTU 的 TLS record 仍然需要可靠的分片承载或保守拒绝；不能把一个完整 16KB TLS record 当作单个 1500B raw TCP packet。旧 M2 包发出/不确定状态统计可对新实验按需关闭高频工作，但不能删除真实 kernel definite-copy/uncertain 归属、Stop fence 和失败后的 slab 回收。

## 6. 最小实施顺序

P0：Rust 新独立 codec + Go 已认证 wire switch + 真实 L4 TLS-record 入口和 sink + 现有 TCP-like raw TX/RX，两个方向 in-place、strict framing、nonce/seq / 8B XOR / 外层校验、loopback PCAP。无需 TUN、FEC、GameMode。熟悉代码者预估约 4～8 人日，尚未实际实现。

P1：如需要保留原 WBD TUN，先在真实原始 TUN IPv4 包上只走 AES fallback，把 TUN 和内核 raw 的全部 Linux end-to-end 接通（约另 3～6 人日）。保留完整 IP 内容，不声称它属于直通 TLS23。

P2：要让 TUN 内层 TCP/TLS 真正走 fast，必须做 IP/TCP parse + 流状态 / record framing + 无损 IP/TCP header sidecar 或受控 delta + 接收端重新生成 IP checksum；大体数周工程。只有满足认证的 TLS application data 记录才能触发 fast；TCP payload 起始 0x17 不能证明 TLS Finished；一个 TUN 包不等于一个 TLS record。

## 7. 实测数字和发布判据

本次 Go 最小测试基于 1345B 已完整 TLS 记录，99% 直通时在 x86 原生 TX+RX 约 7.7124us/100，ARM64 约 9.9078us/100；80% 直通分别 23.1354us/100 和 25.7458us/100，所有模式零 Go heap allocs。是内存模拟成本，**不是 Rust WBD owner 的真实 CPU / LAN 吞吐**。

既有 loopback PCAP 证明真实 TCP packet stream 的 100/100 record 完整解析，单层头无嵌套；Wireshark 未指定解析器也把 custom 数据识别为 TLS record，但标记 TLSv1.2，真正完成 TLS1.3 握手的对照才显示 TLSv1.3。PCAP 本身不证明标准 TLS 1.3 AEAD 互操作和流量不可区分。

真实双机需量测每一方向的 p50/p99 延迟、owner CPU、真实 1Gbps/2.5Gbps 吞吐、每包 heap/syscall、1000/1500/9000 MTU、实际 peer MSS、掉包与乱序、FakeTCP seq wrap、重连密钥更新、fast record 认证缺失风险。fast 数据没有 WBD 自身 MAC；只有当恢复后直接交给真实 TLS 端点、且接受其安全边界时才能考虑此路径。

**最终推荐：先单独接 L4 TLS-record → 新 Tail8Codec → 原 FakeTCP M4。不要把已验证的“只加 2B”实验格式直接宣称能零代价放进完整 IP TUN。**
