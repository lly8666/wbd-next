# M0 H2229 原始 Windows 风格 ACK 统一：Linux Normal/Game 双向、窗口65535、ACK 10ms、业务乱序交付保留

## 用户授权优先级

先修 ACK 不对称，再继续三 Runner（client→ARM 中继→server）的 200ms单程、loss 1/5/10/20% 原生 TCP 夹具；与 H2228 中继基础设施并列，**严禁修改任何表演式外层重传、FEC/AEAD/PN、Health90、逐包M2**。

## 对照现有源码后的事实

- 原 Windows Normal：`crates/wbd-engine/src/v4_windows_native_runtime.rs`，真实已认证累计头 `Counters.ack`，独立 ACK-only 在无业务数据或存在真实 SACK revision 时由 TX worker 发送；之前 SACK 快照每20ms；发送时窗口65535，DATA也65535。
- 原 Windows Game2/4：`v4_windows_game_native_runtime.rs` 每lane `AckLedger` 只在原 Game opener和 Wintun承认后前进，TX worker 用ACK-only和DATA piggyback，窗口65535。独立lane和业务乱序提交并未因为外层缺口阻塞。
- Linux Normal：`v4_embedded_go.rs` 先前 DATA+repair 的 `Presentation.advertised_window=4096`，且ACK-only **只在有旧SACK缺口或放弃缺口时**才可能发送；没有普通累计进度的ACK-only，真实单程200ms高负载可能一直依赖反向数据 piggyback。
- Linux Game2/4：`v4_game_public_kernel.rs` DATA/Health/outer replay 均使用 `ack32=1/window=4096`；没有类似 Windows per-lane authenticated cumulative ACK-only 出口。因此需同时处理方向性和乱序 ledger，单纯提高定时器不够。

## 修改契约（源锁定实验变更，不是性能改善已证实）

- 新 `v4_presentation_ack.rs` bounded per-lane 256非连续间隔、邻接合并、32位回绕、旧包/乱序不虚构累计进度。由原始Go已认证冷握手提供每lane `rx_boundary`；重认证仅在真实Game4 lane替换时重置，绝不能以第一个先到高seq包充当累计ACK基准。
- Linux Game2/4 OFF/FEC：RX仅在AEAD unique opener与TUN真实交付commit成功之后更新原子ACK；TX读取同lane最新值写到DATA/Health/现有copy的TCP presentation，及上限每lane100/s的ACK-only；ACK-only只封装原始 TCP 40字节，无ciphertext、PN、FEC或逐包M2。业务仍按已有原本会被接纳的乱序包立即尝试TUN交付，不在ACK ledger上wait/sleep。
- Linux Normal Off/Fixed/Auto 共享已认证 `OriginalPresentationAck`，新增普通累计进度的ACK-only，在实际M3认证活动且真实原始TX ledger存在时每10ms合并；保留真实SACK、旧缺口250ms放弃、原Go旧发送边界/严格身份和TUN原有独立投递。不能把纯 raw ACK 当作Health或业务正向确认。
- Windows Normal 自己原生RX SACK publish间隔20→10ms，不建新线程；Windows Game原来就是每TX turn ACK-only，因此保持原有即时发送并共享新经复核的受限 ledger，不能为统一而降速或让lane互相等待。
- Linux Normal/Game所有**稳态DATA、Game Health与现有outer copy** 的TCP展示窗口 `4096→65535`，纯ACK builder原本即65535。冷TLS/SYN等受Go原receive-window与WS/MSS协商约束，本轮不修改真实Go手握 / bootstrap窗口、认证/原始业务发送频率。

## 验证与尚未证明

本轮需先运行 Python源结构负例、Rust平台`presentation ACK` ledger单测、原Linux x86/ARM Rust M4原Go TLS编译/双NAT Game/Normal、Windows MSVC真实DLL编译与Windows原GoTLS。对应CI在独立分支；在所有平台未PASS前**严禁合并主线**，不能声称物理Windows 80Mbps或上行3秒崩溃修复。

外层表演式重传仍然独立；单纯将TCP appearance ACK提高不能绕开内层Linux TCP BBR或端到端拥塞控制，在200ms单程、20% loss下必须依据真实iperf原始样本结论。

```feature-impact
{"kind":"none","reason":"H2229 is M0 original native TCP-only cosmetic ACK timing and advertised-window consistency, not a new user-facing GUI/protocol feature. The existing performative outer retry, Health90, M2 quality and business out-of-order/FEC delivery contract are unchanged.","ids":[]}
```
