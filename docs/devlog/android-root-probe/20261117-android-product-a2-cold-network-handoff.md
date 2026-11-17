# A2 第二批｜原 Go 认证代际接入 Bionic Network / RAW / TUN FD

基线：实验分支 `1ccc56e4ff9437d694234fd64ff860e1cc997a04`；main `fb24fe784d960e3e8bf4ca63cc2a22332247e1dd`。本提交仅作用 `experiment/android-temp-root-probe`，不更改 main、M0 registry/cursor；无远端工作树，本次仅审阅远端已提交内容。

- 保留原 `r0/go_overlay/assembly` + pinned Go donor `a7a82db31fe736ffedee330795a3234d358f1984`；沿原 `V4LinuxClientProduct.ConnectAuthenticatedPeer` 标准 TLS → 验证/Detach → 原 Rust `prepare/stage/commit`，在 RAW attach 之前插入 Android-only 冷 `Network`/ifindex/MTU 绑定，接口 MTU由 `net.InterfaceByName` 读回比对，缺失值拒绝。Linux 侧独立文件保留原内核接口，不读取 Android Network 值。
- 同一个 `v4_embedded_go.rs` 的认证 Entry 增加 Android-only 的物理 scope、真实 Bionic tuple-filtered RAW RX、绑定 RAW TX、独立复制持有的验证 TUN FD。导出原 Go 调用的 `attach_raw_rx_on_interface`/`attach_tun`，以及 Android 专属冷 scope setter；实际 RAW FD 在原 TLS 后绑定，未建立替代认证/协议/PN。两个 RAW 打开任何一个失败就全部撤销，禁止不带 Android Network 的发送。
- Android 原 `stop` 通过同一共享 Rust `ProtectedScopedOwner` 将尚未发布给 M4 worker 的这些 owned FD 停用、去引用并关闭；没有 join 真实工作线程，不能标为完整 owned worker Stop。继续保持缺失 `loop_start` 等 M4 原符号的真实 Go 链接 FAIL，不能添加空壳 ABI。
- 原 A1 Action 的一个构建来源、双ABI Rust+Go 源锁不变；扩展真实 Rust 符号导出门与 manifest，使 `Rust COLD + ANDROID OWNED FD ATTACH` 和 `REAL WBD M4 WORKER` 分明，不将 stage 编译/链接等同真机权限、系统 socket 可用或业务 PASS。

此提交执行前测试状态 **NOT_RUN**；之后须以同一 SOURCE Actions 完成实际记录。Android16 KSU ↔ 同源 Linux server 标准 TLS/认证/租约、正常业务双向TCP+UDP、完整 M4/Stop、ARM64 装载/16KiB真机及加速仍 **NOT_RUN**，无设备部署授权。

**唯一下一步**：把这组同一 Entry 的 Bionic RAW/TUN 真实 FD 经原 Rust M1/M3 PN/AEAD/MTU/fair worker 收发循环消费并可同步 join，解决原 Go 全链接（而非新建 Android 逐包引擎），再进入 A3 真实同源服务器测试。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"原Go TLS/Detach冷控制加入仅Android物理Network scope，原共享Rust认证Entry实际收养四元组 RAW RX/TX及TUN FD，NDK双ABI源锁符号校验；M4真实worker仍NOT_RUN。"}
```

## A2 原 Rust 借用栅栏与源锁构建记录

在同一 `wbd-platform::r1::BorrowFence` 上补齐 Android RAW RX/TX、TUN 读写的同步借用，原 `v4_embedded_go::stop` 在结束原 Rust owner 后核对每个借用归零；不凭借 AtomicBool 猜测已无 syscall，未排空返回 `STOP_INCOMPLETE` 并保留 FD。未创建第二 loop 或调度器，原 Linux 代码路径保持不变。

**上一 SOURCE 真实结果**：`ce9be27b318cb44abe86c7c740028173488444b5`，[Action44019082492](https://github.com/lly8666/wbd-next/actions/runs/44019082492) **overall FAIL**；两种 Bionic C ABI、共享 Rust 原认证 cold FFI 及新增 Android Network+RAW/TUN FFI、16KiB PT_LOAD **BUILD_PASS**。原 Go ARM64 完整 M4 链接仍 **FAIL**（`normal_off_*`、原产品 FEC/Game、loop/Health/MTU 等）；x86 Go 全链接 **NOT_RUN**。已独立读取 [artifact14299639612](https://github.com/lly8666/wbd-next/actions/runs/44019082492/artifacts/14299639612)：ZIP SHA256 `09096d7cd178240088bc4c01fe0be3c95d97bef73c67cc4d28c21b0eb1fb8903`，两 .so 与 stage manifest SHA相符，ARM64 `a0e491f2f914d5c2907d869c47e1ca128ef9ba32adc9a58f1e4e8913a63e6179`，x86_64 `35532b2bd8ec3eb0754c8b4be9945ef231a9b1f6a2f006253226492efb7eba77`；stage标记 `RUST_COLD_ABI_PLUS_ANDROID_OWNED_FD_ATTACH_ONLY`，非真socket运行证据。

**本次 BorrowFence SOURCE** 提交后 Actions 再判；Bionic实际收发、同源真实Linux WBD server TLS/认证/租约双向TCP/UDP、完整M4工作线程join、物理 ARM64/耗电均 **NOT_RUN**。单一下一步仍为把现有 FD 消费接入共享原Rust M4成熟 worker 与真实 Go 全链接。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A2真实同源Bionic冷Owner附接 Action证据封存；复用 wbd-platform::r1 借用栅栏阻止未排空FD提前Stop；不伪造已接通M4。"}
```

## A2 冷握手真物理 Network 接线

原 pinned Go donor 的 `RawIPv4Endpoint` 使用 AF_PACKET RX（内核按接口/端口过滤）及 AF_INET IPPROTO_RAW TX。此前只给 **TLS 后 Rust DATA** 绑定 Android Network，无法保证标准 TLS 前的原 FakeTCP SYN 和 ClientHello 物理出网。

现在在同一原Go SYN/TLS流程 **任何 SYN 之前**，使用 Android-only 的 `android_setsocknetwork` + `SO_BINDTODEVICE` 绑定原 sendFD，失败完整关闭原两 FD；没有另造 TLS、TCP 或 Go 数据面。原 CLI 在 Android client 上强制非零 `--android-network-handle`，由系统 ConnectivityManager 的真实 Network 对象提供；接口 MTU 在冷入口读回，并传往认证后共享 Rust Entry。Linux原 Go 路径保留默认行为；原 donor SHA仍按 source-lock 验证，增量文件经 overlay 装配而不复制旧 donor 源。新 CGo Android 文件不影响 Linux GNU/musl。

**上一 SOURCE** `7f5fbda33c3fd26d615923bd93793998de8ad7e8` [Action44019457210](https://github.com/lly8666/wbd-next/actions/runs/44019457210)：双 Android ABI Rust冷/实际FD FFI构建通过，原 ARM64 Go M4 全链接 **FAIL**于未移植的原Normal/off/FEC/Game/loop符号；[Governance44019457225](https://github.com/lly8666/wbd-next/actions/runs/44019457225) **PASS**。本提交新的 source-locked Action 才可裁决源代码的 Android Go CGo 编译/链接。Android16 KSU 与 Linux真server标准 TLS、租约、双向TCP/UDP、root设备实际装载仍 **NOT_RUN**。原 Android CLI 的 TUN/路由并未完成生产 owned 增量适配，不能视为正式可安装App。

**唯一下一步：** 实现同一Rust M4成熟Normal/off线程对 Android RAW/TUN/MTU/Health 的消费与同步 Stop，消除原产品 Go 链接缺口，随后A3真实设备同源连接。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"原Go冷 SYN/TLS 发送 socket 按唯一Android Network/ifindex/MTU在 ClientHello 前绑定，精确 source-locked overlay 文件，完整 WBD M4业务仍NOT_RUN。"}
```
