# B12d｜原 Android Fixed 先 PENDING 认证接收、后真实 M2 APPLIED

基线 B12b/c 已通过 [同源构建及 Oracle #44924052500](https://github.com/lly8666/wbd-next/actions/runs/44924052500)，**11 SUCCESS / 4 SKIPPED**；SOURCE `0d93d2f3ab2d7b13720df779b6e2641b36ad5918`，实体 Android↔Linux 业务未证明。本片不是放开用户模式，而是移除下一步 M2 的因果循环阻塞。

## 循环依赖与本次真实接线

- 原 B12a 的 Android RAW RX：只有 `android_fec2_rx.applied!=0` 才解 FEC2；但是当地 APPLIED 本来要依赖真实原 M4 数据复制后来自服务端的已认证 M2 / Quality。先等 APPLIED 才让 RX 解密，会永远看不到低频反馈。
- 现在只有原已认证 TLS feature7 并经同一 Original-Go Fixed stage FFI 写入的 `android_fec2_pending=(profile,rev)`（合法档0..6，修订>0）才允许进入 **同一个** `ProtectedScopedOwner::drain_windows_authenticated_fec2`，其唯一 M3 AEAD/PN replay 解密与 `Fec2LiveRx::accept_authenticated` 后照旧仅完整 IPv4 经 /32/DNS原TUN 写入。此前的 pending 不能直接变 Applied。
- 在这条**已经过原 M3 AEAD、唯一PN和 Kind 检验的 callback** 内，分别数真正 unique FEC source/repair 和 `AuthenticatedControl.low_rate_quality`、`low_rate_signal`；并不把 raw SYN/ACK、Health idle、legacy per-PN ACK或 Go requested 当成熟 Quality / Fixed APPLIED。
- 原 `wbd_m0_embedded_go_fixed_m4_counters` Native 低频7 u64读回：序号0/1实际 source/repair RAW复制，2/3原TUN实写 source/recovered，4唯一认证 FEC2 symbol，5低率质量已认证报告，6低率质量已认证 signal；原 Go Android Bridge 的强类型数组同步变为7。无新网络队列、加密器或额外线程。
- `fixed_pending_readback` 的真正 APPLIED 修订仍0，没有功能UI入口，`ConnectAuthenticatedPeer` 仍拒绝 Fixed/Auto，Android loop_start仍feature3；软件验收只认 ARM64/x86真Go/Rust ELF、签名APK和 Linux Oracle。旧结果不可借来证明手机真实逆向质量或业务。

## 下一关键路径

同一原 native owner 的 TX 已知 source/raw copied PN 需要与真正认证 PLAN027 quality窗口匹配，形成有出处的成熟 M2 / APPLIED，而不是靠累计一个kind1就置位；然后 Android 原TUN接线与实际 Fixed MTU/大包闭环，最后开放 Fixed/Auto 和实体E2E。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B12d解开原Android Fixed pending-before-Applied接收循环，真实M3唯一AEAD/PN接FEC2与PLAN027认证低频Quality/Signal，7数Native/Go读回；APPLIED及Go模式仍关闭。"}
```
