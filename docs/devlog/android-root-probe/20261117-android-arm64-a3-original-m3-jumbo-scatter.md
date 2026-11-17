# Android ARM64 A3：同一原M3 LINK20的零拷贝正常包与完整大包分片

**工作基线** `02c2772d8d44da76db3210a69ffdebd277f4e4b3`，仅分支 `experiment/android-temp-root-probe`；不触碰main/M0 registry/cursor，不扩展Android x86/32位目标。

## 源锁产品实证起点

- [ARM64 Action 44029417500](https://github.com/lly8666/wbd-next/actions/runs/44029417500) **overall PASS**，真实原Go `cmd/wbd-v4-client` CGo最终链接和原Rust单一M1/M3/M4/Health/Stop Bionic `.so` 生产源码编译成功。真实构建ZIP [artifact 14304571415](https://github.com/lly8666/wbd-next/actions/runs/44029417500/artifacts/14304571415) 已独立解包核对，ZIP SHA256 `0c962e0daa3ad3a92bc5246d20876985c5f6afacbab5c8ad16fa42d2330694ae`；原Go `wbd-v4-client-arm64` SHA256 `62db8d080f884a869935aa65040ddf8e7bed67e71bca6c2f75be60d120e2d3b7`；共享Rust `libwbd_engine-arm64.so` SHA256 `8383d2e43577a9380fedaaa00deeaf322695e0f51b716ae87dc71552ead7842a`。两ELF均AArch64 machine183、min PT_LOAD alignment16384；manifest仍标真实TLS/设备 `NOT_RUN`。同源 [Governance 44029417519](https://github.com/lly8666/wbd-next/actions/runs/44029417519) PASS。

## 本批高效正确性修复

- 旧Android M4只在原M1 slab读取`single_business_payload_mtu+1`字节，真内核TUN的破坏性读取会让较大IPv4包被截断消耗后丢弃。新增 `AndroidOwnedTun::read_ip_scatter`，通过 **单次Bionic `readv`** 两个原生iovec接收整个IPv4：第一个直接是原M1 slab `[14..]`（常见小包无需复制或分配），第二个是每个TX worker只分配一次的65KiB大包尾部scratch；必须有总计>=65535字节容量，沿原 BorrowFence、Stop所有权，绝不将截断包当有效IPv4封包。
- 单个原`ProtectedScopedOwner`的Android seal现在接收**已经在原M1 slab中的完整IPv4**，按原Go经过认证的客户端lease /32验证真实内层源地址，验证IPv4头长与total_len一致后，继续调用原 `seal_normal_off_one` 同一AEAD/PN/Seq/FrozenRecord；不再二次读TUN或分叉密码对象。
- Jumbo或LINK magic逃逸沿原 `wbd_codec::link_fec_wire::LinkPacketPlan`，新增 `issue_next_into`直接序列化字节到原M1预借slab，逐字段与原Go历史 `issue_next`兼容；新增 `resume_issued` 仅在原同一packetID/source+MTU且确认已发行索引后O(1)恢复游标。不可复用/递增的同generation packetID，8帧/turn有界发出；所有密文仍由原M3 `seal_normal_off_fragment_one`签发且必须原 M4 RAW definite kernel copy 后才推进索引。异常、partial、MTU改变、Stop则终止余片、不重封已发PN，不出现混合stride重组。jumbo scratch单一TX worker重复复用，避免正常小包额外堆操作。
- `HealthClock`在原正常小包和每个真实内核复制的分片后记录本地业务活动；每8个原M3帧回到同一Health/Stop/物理scope检查，不创造第二定时器或Go/Java packet callback。
- 同一ARM64 CI增加**独立并行的纯原M3 Wire Oracle**（不是Android x86开发/测试），跑LINK20内存direct slab bytes与原 `issue_next`逐字节相等，覆盖63/65/65535B、magic逃逸、MTU/容量不足时不可续发及游标越界；Native ARM64原Go/Rust真实二进制和16KiB build gate与其并行，两项都必须PASS。

## 实际验收边界

本源新增 readv/M3代码**尚未获得当前SOURCE Actions/Android真机执行通过**；不能把前一SOURCE的Go BUILD_PASS当成本次SOURCE的构建成功。真实Android16 ARM64 KSU /dev/tun、SO_BINDTODEVICE、TLS认证、服务端租约、双向TCP/UDP、MTU near-boundary/65KiB IPv4、Health与线程Join Stop、内核路由/DNS/Root controller/热点评测仍 **NOT_RUN**。

**唯一下一步**：先跑本源码ARM64双CI，修复真实编译/线协议Oracle问题；通过后补 Android Root控制器与journal，获设备授权在真实ARM64 KSU手机↔同源Linux服务器完成标准TLS/双向业务/Stop/MTU测试。成熟FEC/Game仅在完整原协议实证接入时解锁。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"原Go Android ARM64完整CGo与Rust同源ELF首次PASS并核验hash；Bionic单readv常包直入原M1、完整65KiB jumbo原M3 LINK20零分配分片与固定PN/MTU/packetID、8帧turn和Health公平性；独立并行wire oracle，真机仍NOT_RUN。"}
```
