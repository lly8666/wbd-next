# PLAN026 H318｜Windows NativeOwner 单锁批量 + 满载停止回执（2026-10-28）

沿用已提交的Windows Go冷层+Rust Normal/off双native worker产品入口，不加Go回退，Fixed/Auto/Game原Go业务模块等对应Rust模式替代完后再删除。

- 测试源 `aef4ef8a597244fbb120b8db682cd12552d89124` Windows2025 Rust 库编译：原 `v4_windows_native_runtime.rs` 里RX事件 `Arc` 被 move 到线程后又保存到owner, `E0382`；已于 `055026fda1cf6ef31e1a8d81b7e04badeb617c34` 修正。`aef4` 源 Linux Rust 全库检查和Windows Go产品/test编译通过，其 Rust Windows单测因 E0382 未通过；真实双向业务和CPU未由这些编译证据证明。
- 本批把 Rust TX 的8个 Wintun ready源包**先从Wintun读入固定栈slab，一次获取authenticated Entry锁封装全部 M1/PN密文**，再一次Npcap sendqueue真实提交、一次 Entry锁批量记录M2 Accepted/Uncertain/NotAttempted。原实现需8次seal单独锁加1次结算，现每批为2次锁、没有逐包Vec/Go FFI、不增加线程。
- 停止时设置 `AtomicBool stopping`，满载TX worker每批检查，避免一直有包时永远不进入Win32 WaitForMultipleObjects导致Rust Join无法结束；RX有自身Stop事件。同一个OS/Wintun原生loan仍先Rust join后才由Go归还/释放。
- Rust/Go原生 Attach V1 静态布局测试：192字节、RX capture offset80、Npcap函数表offset112、Wintun函数表offset160、Stats48字节。原有具体Go ABI单测已覆盖相同边界。
- 源代码未再次修改Linux raw/TUN执行路径，仅Windows worker局部定点性能/生命周期修正。持续N0 240s、真实业务首次交付、空闲 CPU 和同机A/B必须由后续 Actions 证据证明，不能据单锁策略宣称提速百分比。

```feature-impact
{"kind":"none","ids":[],"reason":"Windows Normal/off Rust native steady热点内部单批锁次数优化、停止同步和Go/Rust ABI静态保护；无用户可选配置、协议wire、平台能力或默认值变化，正式资格不变。"}
```
