# M0 PLAN026 S2｜Windows Normal/off Rust NativeOwner 全链路代码切换（2026-10-28）

基线 main `92394a12bf357a68779bbf28aa00988dd8c410ca`（PLAN026 第一批已交Rust driver/Go原生handle lease）。**本文件是产品源码变更留痕，不是 Actions/性能 PASS。** 用户要求每轮多写代码、新链路替代后不保留 Normal/off 兼容回退；Fixed/Auto/Game 仍在本轮外，不提前删除它们共用的旧 Go packet 对象。

## 新实现

- `crates/wbd-engine/src/v4_windows_native_runtime.rs`：挂在现有 `v4_windows_owner.rs` 的私有原TLS/受控Device-owner Entry 之下；**唯一 Rust TX worker 从借用的Wintun ring直接读IPv4→原 M1 AEAD/PN→现有 ready-only Npcap sendqueue/TX专用句柄**，真实受理 prefix/uncertain/notAttempted逐个反馈同一个 Rust M2 original firstsend。Rust RX worker单独驱动精确BPF Npcap capture/pcap_getevent、复用M3 authenticated kind1 opener、原Replay/receipt、再写同一Wintun，绝无逐包Go FFI。原有M2 feedback、冻结密文repair和低频deadline在Rust内部执行；空闲Win32 Wait而不是5ms Go pulse。2 worker，不随lane扩张。
- `crates/wbd-platform/src/ipv4_tcp.rs`：添加 sealed raw bytes 的零额外Arc/Copy builder `build_bytes` 和纯40B TCP-looking `build_presentation_ack`；Rust RX 保留最高连续且真实已认证+成功写入Wintun的TCP外观ACK窗口，不误把乱序最高SEQ当 ACK，纯ACK合并在Rust TX发送；M2唯一receipt独立。
- `r0/go_overlay/internal/realityfront/bridge_v4_windows_native_io.go`：只从原已验证TLS Rust handle+当前M4设备scope调用NativeStart/Stats/early/Stop ABI。无新TLS、无自定义crypto、无单包Go seal/open。
- `r0/go_overlay/cmd/wbd-client/m0_native_v4_rust_peer_windows.go`：Native normal-only typed product traffic，把Go原握手 `pcap_t` 及有界early segment移交 Rust，第二句柄只发不收；借Go已有唯一Wintun会话/官方driver，Rust join后才能release pcap/Wintun，失败也先join。
- `r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go`：默认Normal/off选 Rust peer（**没有旧 Go Normal fallback**）；原 Go packet pump 在 Normal/off 不再启动，Go仍负责真实TLS/OS/WFP/route/DNS/owned WAL/GUI和低频读回；Fixed/Auto 未迁而临时保留旧peer，Game2/4原产品入口不变。
- `internal/faketcp/npcap_native_handoff_windows.go` 新方法 `DisableReceiveForNativeTX` 把同NIC专用TX pcap_t的捕获BPF设为恒false，避免重复kernel capture导致闲时CPU和ring drop。两份 assembly manifest 的blob精确更新。

## 已写测试 / 未测

新增 Rust platform raw/frozen builder等价、纯ACK checksum、Rust连续ACK/32bit wrap/乱序和真实M2 outcome分类、原 Wintun/NPF borrowed/sender queue单测；Go原生ABI函数表layout、Stop/loan和typed FFI布局单测。CI/真实Kernel/性能本批尚未运行，新SOURCE不可继承PLAN025此前Windows七模式PASS。

**功能门**：Windows x64 Rust cdylib + 原Go overlay/WinForms build→真 signed Wintun/Npcap/WSL2 Linux raw/TUN NORMAL双向UDP/TCP+Owned Stop→真实N0 10Mbps/300ms/240s和源锁旧Go A/B，空闲CPU、进程CPU-seconds/GB、每百万包、RSS、线程数/唤醒、p95/p99首到。先定位首个真正FAIL，原PLAN025 `produced=0 ready=4` 必须保留为独立回归。**不因代码移交宣称性能提升。**

仍未实现：Fixed/Auto/Game2/4全Rust native I/O、Rust Health/Keepalive真实双端wire、Rust动态lane驱动热替换（上一批仅实现了生成代次/prepare/promote状态机）。不会暗中启用这些能力或删仍被它们使用的Go代码。针对 Normal/off 已不提供Go fallback，编译/OS/driver失败直接保留真实错误。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"Windows Normal/off NativeOwner Rust NPF/Wintun 真实产品调用点、Go冷句柄交接和ABI已改变；两张卡保留旧SOURCE验收与新增NOT_RUN，本批还没有新真机/性能合格证据。"}
```
