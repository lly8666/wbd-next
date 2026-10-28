# PLAN026 H317｜Windows NativeOwner 编译首错与运行门（2026-10-28）

本次按已发布产品 SOURCE `b2d01c7a496eddaf1a10482791a6eebd805a79f8` 的实际 Actions 首错迭代。Windows/Rust 原有流程的当前生产服务端没变。

- GitHub Actions `40646315405` 两交叉目标和 `40646315374` Windows Rust owner test、`40646315323` Windows/Linux Rust unit 的首错均为同一个 Rust E0502：`wbd-platform/src/ipv4_tcp.rs` 新纯 ACK checksum 同一表达式存在可变/不可变借用冲突；源码已单点拆出预计算checksum修复。
- `40646315485` feature catalog 首错为 `feature-impact.kind=update` 非合法值，已修为 `updated`；修复提交 `b8db2a4a` 自身被 feature catalog 的「本次声明应和本次卡片差异一致」门检查为红。本次同时重新更新两张实际受影响功能卡，并以新的 devlog 给出合法 `updated` 说明，解决每单提交审计关系，不篡改旧SOURCE资格。
- Workflow `m0-wl-public-normal-full.yml` 原仅监控主 `v4_windows_owner.rs` 与旧Go hot文件，未把新版独立 Rust native worker、Go NativeIO桥、Wintun/Npcap借用和IPv4/TCP模块列为触发源。现在将其加入 push paths，以后每批NativeOwner代码变更自动跑已有便宜 Windows Go/Rust 编译门，不需为了发现编译失败跑10Mbps/240s业务 Actions。
- 新增 V1 192字节 Go/C NativeOwner attach ABI offset 单测（Windows x64）：4×原生handle与6×Npcap函数指针、4×Wintun导出地址布局明确固定，避免 Go字段改动使Rust在未验证时读取错位指针。

本次不改变Normal/off执行策略、不恢复Go per-packet fallback、不删除仍服务Fixed/Auto/Game的Go模块。前述真实Windows N0 produced=0 ready=4 和新NativeOwner真实签名driver/性能没有由本次便宜修复自动PASS，继续等对应原始精确源码的Windows编译与真实端到端证据。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"修正Windows Rust NativeOwner原生字节入口编译借用E0502与ABI布局、自动触发Windows编译回归；两张受影响功能卡同步本次source qualifier，尚未证明正常运行/性能。"}
```
