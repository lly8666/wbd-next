# M0 PLAN026｜Windows 原生 I/O 第一个实代码批次（2026-10-28）

本批直接按用户授权方案 B 开发，不再停留在设计层。基线 main `5cde8a730d5acce3de627ab02907754adac4fa65`。这次实现的是**可复用的 Rust Native I/O + 真实 Go 原生设备租约基础，不是已激活的全 Rust Windows 产品流量路径**。正常 Linux Rust/raw/TUN 未修改。

## 已实现的代码

1. `crates/wbd-platform/src/windows_native_io.rs` 与 `lib.rs`：Rust Win32独立事件唤醒、单独 Npcap RX/TX pcap_t 借用和真实 pcap_next_ex/sendpacket；可用时复用一个8包/16KiB NPF sendqueue、Wintun同session收包-release/发包、Ethernet/VLAN去壳和拼装、Ethernet padding兼容、driver三态Outcome。每包调用直接在Rust，源代码不依赖Go每包callback。新增Windows mock ABI/packet/partial-send单测，不能冒充真实 signed NPF/Wintun通过。
2. `r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go` + test：保留原 Go握手/精确BPF/pcap_t，读者 gate.stop+wait 后移交句柄、wpcap.dll函数表及read事件；旧 Go endpoint 不再可读写/Close此句柄；`CloseAfterRustJoin`才可真正pcap_close/Release模块。过渡early帧还须在正式客户端接线时结清。
3. `r0/go_overlay/internal/windowsclient/native_rust_wintun_loan_windows.go` + test，及 `native_udp_kernel_driver_windows.go`：原 authenticated M4设备读回后借同一session/Win32导出函数给Rust；Go ring读写/Stop在Rust借用期被明确拒绝，`TUN.active`确保 Go.Close不会提前EndSession；Rust Join完成再归还。WinForms/路由/WFP/WAL仍在Go。
4. `crates/wbd-engine/src/windows_lane_lifecycle.rs` + `lib.rs`：无锁、无加密替代的Rust动态lane状态机；按真实同TunnelEpoch的1 Active/1 Retiring/1 Candidate、RX+TX就绪后原子promote、候选失败abort、驱动quiesce后retire，单隧道一次转场；三组正确性单测覆盖旧lane健康保持、stale callback、Game其他lane未动。
5. Go overlay 两份 `r0/go_overlay/assembly/manifest*.json` 已添加精确新文件blob，PLAN020清单也更新现有 Windows kernel lease文件blob；无需直接改老 `wobuzhidao` 仓库。

## 两侧复查与未完成边界

- Rust平台代码 **未安装到** 当前 `v4_windows_owner.rs` 的实习 RX/TX worker（尚未开始真实 Rust-native TX/RX）；Go `m0_native_v4_windows.go` 仍运行旧 `pulse()`/Go NPF reader，故当前 Normal/off的真实产品行为没有改变，不能宣称 Windows Go 已休眠、CPU已降低、Keepalive已迁或动态lane已接线。
- 低层借用的真正安全顺序是：Go TLS/受控绑定→停止旧 NPF reader +保留early→Go导出Npcap/Wintun原生租约→Rust Session.NativeOwner启动→Rust Stop join/释放ring→Go归还借用/关闭pcap和Wintun→WAL/WFP/DNS/route回滚。任何提前Go.Close或绕过authenticated epoch 都不能称为成功。
- Npcap `pcap_breakloop` 对正在执行的 `pcap_next_ex` 的唤醒可靠性及 target runner `pcap_getevent`仍需真实CI验证；当前 Go原始 read timeout50ms为既有设置，不以模拟保证没有handoff空窗。下一功能片需实际观察/关闭这一边界。
- 原 M0 H315–H318 的Windows N0 `produced=0 ready=4`、M2/M3历史首错，以及实际在途Actions结果均未被覆盖。新Rust native ingress正式接线后必须独立复现/回归。
- 本批**未执行 Rust/Go/Windows Actions 编译、网络功能或性能测试**，全部 NOT_RUN；后续先补Windows真实 NativeOwner 接线与Go调用链、packet proof/owned Stop、装配与完整测试夹具，再冻结 SOURCE 集中测试。性能按同机旧Go A/B、新Rust B比CPU秒/GB、1pps首到、空闲唤醒、RSS和NPF drop，不能从代码量推断性能提升。

## 下个具体代码任务（无需新授权）

在已有 `v4_windows_owner.rs` 中为已提交且真实认证的 `Entry` 安装 `WindowsNativeOwner` 及两个固定 Rust worker、直接使用本批 `NpcapRx/NpcapTx/WintunRx/WintunTx`；Go V4产品入口通过受控FFI传完整原生租约，移除Normal/off的 Go读者/pulse/packet-proof热依赖，Stop必须先join线程再归还两侧leases。把实际source中每方向PN/SEQ、真实driver M2结算、auth-only RX→Wintun与Go packet reader early queue的边界一次接通，写齐真实Windows/WSL2功能和Go基线性能夹具之后才集中Actions验证。

```feature-impact
{"kind":"none","ids":[],"reason":"新增Windows NativeOwner低层Rust/Go句柄租约、lane状态机与测试/装配；产品CLI/GUI和业务热路径尚未接线，未改变可见功能或默认配置，也没有新产品测试资格。"}
```
