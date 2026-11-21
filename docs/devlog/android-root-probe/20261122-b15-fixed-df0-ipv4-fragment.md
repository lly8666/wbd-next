# B15｜Android Fixed 原生 IPv4 DF0 普通头分片接线

SOURCE 基线 `1c5181284aa513f4364875e1d76146dadada2f43`。针对真实代码缺口：`v4_android_original_m4.rs` Fixed 单源预算之外的大包此前直接 `tx_dropped`，而 Normal 走 LINK20（Fixed 接收端不认识，不能复用）。

这轮只接 `IHL=20`、未分片、`DF=0` 的大 IPv4 包：同一原 TX worker 保留已经从 TUN `readv` 得到的完整包；原 IPv4 ID、IP 负载/UDP/TCP checksum 保持；按现有 Fixed 原预算扣 source header 的容量切为 8 字节对齐的 IPv4 分片，逐片修 IP total length、MF/offset/IP header checksum，分别走已有 `send_android_fixed_source` → 原 FixedStream → 原 M3 AEAD/unique PN → 同一 AF_PACKET RAW 拷贝。最多每轮 8 片，容量不足稍后续写，Stop/generation/物理MTU切换即退休剩余片，不新开线程/FD/另一个 crypto。普通小包原零复制快路不变。

严格留下独立后续片：IPv4 options/copy-bit、已分片大包和 DF=1 正确 ICMP PMTU；不对它们谎称已支持，也不偷偷封装 Normal LINK。Go Android Fixed/Auto 产品入场仍按原门关闭，不能据此宣称真机 Fixed 可用。静态新增 Android-target Rust 单元测试覆盖 4020B 全量复原、offset/MF/IP checksum、DF/options/旧分片拒绝；实际是否运行需看 CI（Android target 测试不一定由 Host 执行），真机与真实对端应用字节级 E2E NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B15 Android Fixed DF0 IHL20 jumbo now fragments at IPv4 layer and feeds original FEC2 owner; DF1/options/phone testing remain pending"}
```

## 首轮 CI 证据及源码门修订

首轮 SOURCE `64731e47bb41ddb3a77e64f72444485041444338` 的 [dual64 #44930277640](https://github.com/lly8666/wbd-next/actions/runs/44930277640)：原 B2C2b DNS Host Rust 测试运行通过，随后旧 Python 静态断言仅允许两处 `android_dns_flows.rewrite_query`，B15 新 Fixed jumbo 分支新增第三处调用，因此源码门 FAIL；其余源级/ABI 真正结论查各 job。首次 [governance #44930277680](https://github.com/lly8666/wbd-next/actions/runs/44930277680) 由于功能卡超过 16KiB FAIL；第二次 [#44930359351](https://github.com/lly8666/wbd-next/actions/runs/44930359351) 因仅修改功能卡、同提交没有 feature-impact 日志 FAIL。当前冻结修正 B15 源码门按三个确实存在的原 M4 调用验收，功能卡缩短而**保留原历史 verification**，本日志与功能卡在同提交申报；等待新 SOURCE 所有 Jobs，绝不追认前三次为成功。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B15 Fixed native IPv4 DF0 slow path remains, document real CI size and DNS source gate failures and correct same-commit feature declaration"}
```

## B15c｜关闭未启用FEC2的构建边界

复查发现 B15 新增 `pending_fixed` 处理块引用 `send_android_fixed_source`；后者仅在 `fec2_product_record` feature 下存在。把 TX worker 状态和 Fixed 分片处理块同步置于同一个 `#[cfg(feature="fec2_product_record")]` 条件下，防止没有 FEC2 的 Android 编译失败。Normal/off 运行代码不变；仍需最新 SOURCE 原生构建收据。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B15c bound new Fixed slow-path state and TX block to the existing FEC2 compilation feature; no change to Normal/off runtime"}
```
