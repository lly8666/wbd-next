# 2026-11-17 A3：Android ARM64 原 Go Normal/off 产品 CGo 能力分层与 M4 热路径优化

**SOURCE基线**：`6c347e1b7a912e28d3224efed51b745b4e574439`，仅 `experiment/android-temp-root-probe`；main/既有Linux/Windows产品实现及M0 registry/cursor未修改。此批唯一Android ABI arm64-v8a / AArch64 Bionic，Android16 KSU 真机不在本次未经设备授权的实验范围。

## 具体产品改动

- 原 Go 原产品 `bridge_v4_embedded_linux.go` 仅加 `!android` **构建选择条件**（Linux原行为与逻辑一个字不动）；新 `bridge_v4_embedded_android.go` 用相同的原 TLS credential-checked Prepare/Commit/lease/FD/M4/Stop/Health/TCP-MTU Go控制调用，但静态只引用已经真正编译的原共享Rust ELF导出。剩余**20项** Fixed/Auto、真实M2 mature firstsend/coverage、Linux共享TUN/路由回调、outer/quality、debug/jumbo等未经Android实现的产品API直接返回已存在的`ErrAdmissionUnsupported`；返回错误而非伪造空的 native C 函数，亦不把未知CPU或Repair当0个丢包；未启用模式不会误导产品或强求未移植ELF。
- `bridge_v4_fixed_pending_linux.go` 原源只加 `!android`；Android normal/off 版本中 Fixed/Auto 请求和只读Pending均显式拒绝，绝不创建一个假的Fixed APPLIED或M2 ACK。原 `bridge_v4_normal_off_policy_linux.go` 不改，继续直连已实现的真实同epoch单调revision Rust Native ABI。
- 原Go `V4LinuxClientProduct.ConnectAuthenticatedPeer` 在开始TLS前按Android分支验证仅Normal/off、无outer repair、无Linux SharedTun、真实auto lease；原TLS认证、Install /32、外层RAW interface handle、Rust加密M4 Start和canonical Health逻辑均复用不改。原Go普通Linux仍调用自己真实OuterRepair和FirstSend M2；Android **仅在这些能力尚未实现时跳过相应不可用的可选功能**，不是伪造能力或把所有模式都称为可用。
- Android首连原Go CLI将outer repair默认`off`并显式拒绝固定、自动、Game2/4、重叠轮转和非自动/32（用户仍可明确选`on`，会在建立TLS前报不支持）。不再在 Android autoIP 为首连打开原Linux共享TUN或者驱动Linux A/B共享reader，而使用已有Bionic原Owner持有的真实根TUN FD；Linux原模式和旋转管理路径保留。
- Bionic Rust真实M4 worker RX 一次分配并持续循环复用`Vec<RxPacket>`，去掉原来**每个RAW包一次**`Vec::with_capacity(1)`；依旧经原M1 slab→单个M3 AEAD/replay→原/32授权TUN，消息与原PN均不变。Native CPU采样在实际RX/TX worker中用Bionic `CLOCK_THREAD_CPUTIME_ID`（每个外层就绪turn最多一次，而非逐包），锁外/低频原子快照，供原Go健康探针读取真实线程CPU值，不从wall time猜CPU。`wbd_m0_embedded_go_loop_thread_cpu`在原native owner active和worker存在后真实返回两线程纳秒数。
- 源锁CI强制真正Rust CPU/Health/Stop/Normal/off/认证lease/物理RAW-MTU符号均来自**同一个ARM64原Engine `.so`**；完整Go `cmd/wbd-v4-client`不能关闭真实lld链接门；最终Go可执行文件也必须为ELF64/AArch64并具有>=16KiB PT_LOAD对齐。没有任何 Android x86目标或V3/VpnService/FakeIP替代实现。

## 验收状态与边界

- 上一正式源码`1b044ed3f76a4674e75ee409fe9746ba22343e84`的 ARM64 Action44026702035：真实原共享Rust M1/M3/M4 Health/Stop + lease+MTU BUILD_PASS、原Go类型PASS、最终CGo ld.lld FAIL（Fixed/M2/SharedTun/route/诊断等），Governance Action44026702031 PASS；详见同目录A2 devlog。
- **本A3 SOURCE CI尚未跑**：不得提前声称Go完整链接/装载成功。即使 Go `ld.lld` PASS，唯一证明的是正式原 Go ARM64程序产出和硬ABI对齐；实际安卓16 KSU root、Bionic真RAW/TUN、标准TLS/Auth/原租约/真实双向TCP/UDP、Life/Stop/CPU/Health/FEC/jumbo、Android UI/路由与DNS全部**NOT_RUN**。原Linux正式产品行为保持原样。
- 进一步目标：建立Android ARM64 正式 app Root 控制器，从ConnectivityManager真实Network handle/ifindex与TUN、owner journal进行生命周期绑定；完成原M3 jumbo及真机授权后，再讨论成熟M2/Fixed/Game的真实分模式移植。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Android ARM64原Go Normal/off真实控制CGo同Rust必需ABI单独source-lock；20项非本模式功能显式Go拒绝，不造原生占位符；修复首连Linux共享TUN依赖；原M4 RX预分配复用和Bionic实际线程CPU低频读回，真实Go最终链接与真机独立验收。"}
```
