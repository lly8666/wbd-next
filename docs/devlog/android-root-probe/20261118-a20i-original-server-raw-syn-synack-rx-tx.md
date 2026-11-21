# A20i：原 Linux Go 服务端 RAW SYN/SYNACK 取证（2026-11-18）

**真证据**：[SOURCE `edb61a32` Actions #44260197955](https://github.com/lly8666/wbd-next/actions/runs/44260197955) 整体 SUCCESS。官方 Artifact #14408156804：Android16 x86 KSU 普通 App→Root、原 Go/Rust NativePayload、正式 RootService 真 TUN、AF_PACKET、原 Go Sendto SYN PASS；同源 Linux 原 server 真 TUN PASS。Linux host `lo` 观察到 TCP dport443 SYN，没有 SYNACK/RST；Android 模拟器 `-tcpdump` Ethernet LAN PCAP **0 frames**（该捕获不代表 Wi-Fi 全流量）。此前收据错误地把空样本显示为 NOT_OBSERVED；现修正为 **NOT_PROVEN**。真实 SYNACK、TLS/认证/32租约、Rust M4 双向应用 TCP+UDP/owned Stop 依旧 NOT_PROVEN/NOT_RUN。

**需要继续区分的两个真实阶段**：宿主 `lo` 出现 TCP SYN 还不足以证明原 Linux Go AF_PACKET 实收原 FakeTCP SYN，QEMU 用户态 NAT 可能将其换成 TCP socket 连接。本提交在原 `runSharedMultiServer` 不改变协议或数据收发的前提下增加两枚**一次性、无敏感数据的固定日志**：
- `V4_PUBLIC_ORIGINAL_SERVER_RAW_INITIAL_SYN_RX`：只有原 `raw.ReadSegment` 收到，且 `IsInitialSYN`、MSS 536–1460 真校验通过的未认证 SYN 才出现；
- `V4_PUBLIC_ORIGINAL_SERVER_RAW_SYNACK_TX_OK`：只有原 `assoc.SYNACKSegment`、原 RAW `emit` 真成功才出现。

D2-S1 从私有 Linux server 日志抽取两枚固定 marker 组成 source-locked receipt，绝不把未认证 SYN/Sendto 当 TLS PASS。若 host SYN 但原 Go 没有 RAW RX，应排查用户态 NAT/host AF_PACKET 过滤；若 RAW SYNACK 发出而 Android 原 ClientAssociation 未收到，应评估 TAP/桥接环境。此修改没有第二 packet pump、无原始 PCAP 上传，不修改 Go/Rust 协议、ARM64 正式发行、物理 Network、UID、Stop、系统 DNS 安全冷许可；实验分支 PR #36 Draft，不动 main/M0。新 SOURCE CI 尚未运行。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20i host lo SYN 实证，但 guest Ethernet PCAP 0帧改为 NOT_PROVEN；新增原 Linux Go AF_PACKET 接受未认证 SYN 与发 SYNACK 的固定只读 marker，防止误判普通 NAT TCP 为 FakeTCP 认证。"}
```
