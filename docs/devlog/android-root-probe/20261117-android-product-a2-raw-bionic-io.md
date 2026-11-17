# A2 第一批｜Android/Bionic 真 RAW 收发 FD 与物理网络强绑定

SOURCE：本次提交 SHA 以 GitHub commit 为准；提交前未声称测试通过。起点远端 Android `0e1fe307125b17f7edbc66ac4d16b6249c743b39`，main `fb24fe784d960e3e8bf4ca63cc2a22332247e1dd`。本批仅限实验分支；无 worktree，未检查远端不存在的本地未提交文件。

- 在已有 `android_root_io` 中新增 Bionic 内核 RAW **实际** TX/RX FD 原语（非模拟包、非协议替身），不改标准 Go TLS/认证/租约及 Rust PN/FEC/retransmission。RX 按已经认证的对端原四元组安装与 Linux M4 同语义的13条 classic BPF，失败即关闭 FD，不降级为无过滤监听；返回的原始字节仍为 **未认证**，必须由同一原 Rust M3 解析/AEAD/重放门处理。
- RAW TX 仅在原Go冷控制传入明确 physical Android `Network`、接口、ifindex、MTU、generation 和外层源/目标 IPv4 后打开，`android_setsocknetwork` + `SO_BINDTODEVICE` 双绑定、`SIOCGIFMTU` readback；使用内核 `IP_HDRINCL` `sendto`，原Rust拥有完整不可变外层 IPv4/TCP DATA 与共享MTU快照。绝不把 Go/Java/JNI 放在逐包路径，不建新的重传器或 TLS。
- FD RAII 保证初始化任意失败关闭；Stop 标记阻止新调用。**尚未接入原M4线程 join / BorrowFence**，因此不可声称完整 owned Stop、p99、真实TCP/UDP。
- NDK C gate 同时验证 Bionic `SIOCGIFMTU`、classic BPF 布局及 option。保留 A1 独立双 ABI 和故意不能绕过的原Go真实 M4 全链接门，不新增 synthetic PASS/探针按钮。

**测试：** 原代码和ABI本轮提交后由 SOURCE 对应的唯一 Android product 构建 Action 决定，提交前一律 `NOT_RUN`。Android16 KSU↔同源真实Linux WBD、TLS/认证/租约/TCP/UDP/16KiB真机装载/网络变更/ISA均 **NOT_RUN**。旧 A1 `c385502a` Action44015392698 的冷ABI BUILD_PASS、完整Go M4链接 FAIL 继续保留，不能覆盖。

**唯一下一步：** 对照 `v4_embedded_go.rs` 原 `ScopedRawIpv4Tx/Rx`、`ScopedTunSink`、`ScopedRouteBudget` 和全部 Go CGo M4 调用，把这些 Bionic FD/网络预算操作纳入**同一**成熟 M4 worker与同步 Stop，并在原Go完整产品全链接门实证；之后 A3 才开始同源真实 Linux server 连接。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A2首个原生I/O施工切片，Android内核RAW TX/RX四元组过滤、特定Network/MTU/代际强绑定与NDK ABI门；尚未M4接线及真实业务测试。"}
```

## A2 源锁构建与治理收口（2026-11-17）

- **SOURCE**：`097d3b0e95872c2aaad317e3647f59101ba315fc`，原 Go donor `a7a82db31fe736ffedee330795a3234d358f1984`。构建 [Action44017866225](https://github.com/lly8666/wbd-next/actions/runs/44017866225) **overall FAIL**，但子步骤 NDK arm64-v8a/x86_64 的 Bionic C ABI 静态检查、同一 Rust `prepare/stage/commit/stop` 冷 FFI 导出、双 16KiB ELF 构建 **BUILD_PASS**。这只证明源码可编译；**A2 Android RAW 内核行为未运行**。arm64 原 Go `cmd/wbd-v4-client` CGo 最终链接 **FAIL**（原 M4 `attach_raw_rx`、`attach_tun`、`loop_start`、Health/MTU/FEC 等符号仍未在 Android Rust 导出）；x86_64 完整 Go 链接 **NOT_RUN**。
- **同源产物**：[artifact14299801880](https://github.com/lly8666/wbd-next/actions/runs/44017866225/artifacts/14299801880) ZIP SHA256 `47c6e5c29387a2efd0fda411a8cb556d2e0a9bf5ad0802a6b190f5043f9a8914`，独立下载解包核验 `rust-cold-stage-manifest.json` 与 .so SHA256 一致；ARM64 ELF e_machine=183, PT_LOAD最小对齐16384, SHA256 `bf2261b2ebd33656cb0df9efc1bc7b16aa462cb9fee2c389192d23b86e458be8`；x86_64 machine=62, 对齐16384, SHA256 `53a9445f1d5083b09c8d2d74cf57363648956b6292aba18664bb6e34f669c7ec`。清单明确 `SHARED_RUST_COLD_ABI_ONLY`，不代表完整客户端链接成功。与旧 A1 相同的 Rust .so SHA 不代表新 Android RAW 系统调用被真机执行。
- **Governance**：初始 [Action44017866230](https://github.com/lly8666/wbd-next/actions/runs/44017866230) **FAIL**：devlog `feature-impact` Markdown 围栏意外带反斜杠，非产品编译问题；文档独立修复 SOURCE `403d0d531206ab51157ddb29fba2274e8934df6f` 后 [Action44017973893](https://github.com/lly8666/wbd-next/actions/runs/44017973893) **PASS**。失败保留，不改写旧 Action。
- **NOT_RUN**：Android16 KSU↔同源真实 Linux 服务端标准 TLS ClientHello/身份认证/租约、RAW/Rust M4 收发、TUN/双向 TCP+UDP、真实 Stop/异常恢复、物理 arm64 装载/16KiB、网络切换/能耗/ISA、业务 p99；没有部署设备授权，也没有把编译当真实业务证据。

**唯一下一步仍为 A2**：在 `v4_embedded_go.rs` 同一原 Go 认证代际内复用 M4 handler 并接入 Android RAW/TUN/MTU/Health/owned worker Stop 的真实实现，消除真实完整 Go 链接缺口；之后 A3 才做 Android16 KSU↔真实 Linux server Normal/off 的同源业务验收。不得添加假 ABI stub 或另建逐包控制循环。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"以SOURCE097d3b0e和Action44017866225封存双ABI Bionic冷FFI构建PASS与ARM64完整Go/M4链接FAIL，独立ZIP/hash核验；治理失败及修复PASS照实留存，实际WBD仍NOT_RUN。"}
```
