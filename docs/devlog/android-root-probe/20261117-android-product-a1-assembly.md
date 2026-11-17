# A1 实施切片｜Android/Bionic 真产品装配构建及薄FD边界

本切片修改 **Android product** 的编译/链接闸门，不新增探针测试或合成业务，不修改现有Linux入口或M0算法。原Go donor固定 `a7a82db31fe736ffedee330795a3234d358f1984`，复用共享源锁安装器，Rust `wbd-engine` 采用 `m0_v4_probe,m0_v4_embedded_go` 首次Normal/off编译（本包不启ISA-L）。NDK同时验证 Android arm64、x86_64 的真实Bionic ifreq/TUN/socket ABI与16KiB ELF PT_LOAD alignment，Go以 `GOOS=android CGO_ENABLED=1` 编译原Go产品 `cmd/wbd-v4-client`，不复制Linux代码形成新分叉。

Rust `wbd-platform::android_root_io` 是 Android-only owned TUN FD / exact Android Network 物理socket绑定 API，冷阶段验证TUN模式和接口，禁止未经绑定回退、全局mark和整个root UID直连；不承担认证/数据循环。旧 `linux_raw_carrier` 不被错误启为Bionic。这些API**尚未接到**共享 Rust M4 handler，更未发生TLS、lease、正常业务交付。首次Action在提交后才会提供准确 `SOURCE` 与 BUILD_PASS/FAIL，之前维持 `IMPLEMENTED_NOT_TESTED`。

下一步：读取 A1 Action 首个真实失败/成功，按真实构建错误最小修复；通过后 A2 实际与原Go冷控制接线，再在KSU Action真正连接Linux标准WBD服务器。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A1新增Android Bionic 64bit布局/底层root TUN和物理Network绑定源码，接入原Go/Rust source-locked交叉构建；产品链路严格未测。"}
```

## A1 source-locked CI 失败与定点修复（不变造成功）

- `b33039f67585191ffa83c27892e55839be73d86d` [Action44012875741](https://github.com/lly8666/wbd-next/actions/runs/44012875741)：**FAIL/WORKFLOW_INVALID**，新workflow run-name的 `\\$\{\{ github.sha \}\}` 在YAML双引号中为未知反斜杠转义，零作业。修正见 `d50e9e8200ac4f15ef5b978da30e99dcc6bc5ddf`，不属于产品编译失败。
- `d50e9e8200ac4f15ef5b978da30e99dcc6bc5ddf` [Action44013027549](https://github.com/lly8666/wbd-next/actions/runs/44013027549)：**FAIL/NDK_HEADER**，Android C `<linux/if_tun.h>` 的 `TUNGETIFF/TUNSETIFF` 展开需先显式导入 `<sys/ioctl.h>/<linux/ioctl.h>` 才能得到 `_IOR/_IOW`。尚未进入Rust/Go链接，不能写 `BUILD_PASS`。
- 当前修正仅补必要头文件，接下来的A1 Action才可证实更深层编译。若再失败，分辨 Rust Android C ABI、Go Android编译或测试环境，不进行Linux整套代码复制。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Bionic产品A1编译夹具修正头文件依赖，记录初始Action失败及精确SOURCE；产品能力仍未认证或实际接通。"}
```

## Bionic signedness：A1第3次构建反馈

源码 `a50db413a337044e55a93d7c0f7d8c17476c1597` [Action44013224466](https://github.com/lly8666/wbd-next/actions/runs/44013224466) **FAIL/PRODUCT_RUST_TARGET**：NDK ifreq/TUN `android_abi.c` 已通过，编译随后在 Rust `if_nametoindex` 入口报 `expected *const i8, found *const u8`（Android Bionic `c_char` signedness 与 GNU 假定不同）。修正声明为 `std::ffi::c_char`，不修改全平台GNU声明，不忽略错误，不宣称 Go/Rust owner已连通。下一SOURCE继续检查Rust编译与真正Go链接。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"根据Android/Bionic c_char实编译失败最小修复if_nametoindex ABI；继续源锁构建验证，真实连接仍未测。"}
```

## A1 第四次构建：原共享加密C库的真实NDK工具链失败

源码 `64edbb3d32cf70463f81cbb397ff1bb65c931f7c` [Action44013459586](https://github.com/lly8666/wbd-next/actions/runs/44013459586) **FAIL/AWS_LC_CROSS_CC**：Bionic C ABI与新平台Rust代码编译已越过，`aws-lc-sys@0.45.0` 经 `cc-rs` 默认查找不存在的 `aarch64-linux-android-clang`。Cargo linker变量仅作用Rust链接，不等于依赖C编译器设置。已按实际NDK wrapper路径设置 `CC_aarch64_linux_android/CC_x86_64_linux_android` 和 `AR_...`，下次Action确认是否通过。原Go entry/build tags依旧Linux-only，编译符号闭环未验，不能宣称真实客户端成功。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A1因aws-lc-sys没有NDK交叉C编译器而失败；给cc-rs配置精确NDK两个目标CC/AR并保留失败证据，产品连接NOT_RUN。"}
```

## A1 第五次构建：原Go生产源码的条件编译闭包

SOURCE `067e3fe91b106abdd50f12a9e8e31ea241e1a01f` [Action44013768079](https://github.com/lly8666/wbd-next/actions/runs/44013768079) **FAIL/ORIGINAL_GO_BUILD_TAG_CLOSURE**。NDK/Bionic静态ABI、共享Rust `wbd-engine` Android64 release 构建成功；原Go `realityfront/bridge_v4_linux_server_product.go:180:11` 缺 `V4LinuxGameAuthenticatedLane`，因为Go生产源在对应Linux原产品发布构建中本就需要 `wbd_v4_fec2_product` tag，单 `wbd_v4_embedded_go` 不构成封闭编译集。参照仓库既有 `tools/arm64_public_go_rust_bundle.sh` 将Go tags修正为 `wbd_v4_embedded_go,wbd_v4_fec2_product`，共享Rust加 `fec2_product_record` 以保持链接符号一致（不启 `native_fec_acceleration`；A1只运行Normal/off的设计目标不变）。**这次失败不是Android真实接线失败或通过；产品C桥与Rust M4的Android条件编译仍待连通。**

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A1源锁Go生产模块缺Game类型，修正为既有Linux公共产品构建使用的Go/Rust feature闭包；仅build检查，实际AndroidWBD未接通。"}
```

## A1 第六次构建：Go↔Rust原认证所有权实际链接断口

固定 `19115a34bef1ec3c8213c16e953062254e9ae93c` [Action44014077113](https://github.com/lly8666/wbd-next/actions/runs/44014077113) **FAIL/GO_RUST_PRODUCT_LINK**：NDK两个ABI C校验、共享Rust release、原Go源锁源码编译（`wbd_v4_embedded_go,wbd_v4_fec2_product` tags）已到最终原生链接阶段；`ld.lld` 报 `wbd_m0_embedded_go_abort/prepare/commit/attach_raw_rx/attach_tun/loop_start/... undefined symbol`。确认 `crates/wbd-engine/src/lib.rs` 原 `v4_embedded_go` 模块仅在Linux启用，Android曾误编译了无该认证owner的普通cdylib。这**明确不属于Go客户端成功**。

本切片仅将 **原同一个** `v4_embedded_go` Rust 模块在Android64条件下进入编译，验证已有标准Go认证TLS冷所有权 `prepare_client/stage/commit/stop` C ABI是否真实导出；不创建Android专用认证者、不复制Rust加密核心。原模块内GNU/musl raw/TUN worker和M4生命周期仍受原条件编译屏障保护，因此本步 **不会** 宣称真实M4收发。下一Action如有编译/链接错误按实际逐项移植，绝不添加假stub绕过缺失的产品符号。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A1在真实Go CGo链接发现Rust V4 Go owner仅Linux装配，最小拓宽原私有认证冷模块的Android64编译并检查真实FFI导出；M4数据面仍NOT_RUN。"}
```

## A1 第七次：真正进入原Go Rust所有权模块后的平台边界

SOURCE `b2fe8422682e7e2dd34ce39211cb2f1f3dfcdd2a` [Action44014373562](https://github.com/lly8666/wbd-next/actions/runs/44014373562) **FAIL/RUST_BIONIC_CFG**，16项编译错误集中在原Linux-only kernel M4字段/辅助函数不应于Android无驱动阶段被引用：`OriginalOuterRepair` Linux-only类型的字段无OS门，`attach_tun`仍直接调用Linux `ScopedTunSink`，`PollFd/LoopCounts/ClockTimespec/ppoll` Linux-only类型的辅助函数少了同条件门，以及 `protected_features` 认证冷字段在Android被Game冷验证读取却没有对应字段。现在只对这些既有符号施加匹配内核驱动的Linux门，保留Android共享冷认证字段；既不引入Glibc类型到Bionic，也不在Android提供假的M4替身。Linux GNU/musl和Windows默认功能条件保持不变。

这些更正仅为跨平台编译核准，真实WBD链接/传输/MTU/Stop仍是NOT_RUN，最新Action将独立决定符号是否导出与Go CGo是否能链接。再次FAIL按原链路补真实Android底层适配，而非禁用失败测试。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"实编译原私有Go-Rust冷认证模块发现16处Linux-only M4字段/辅助函数cfg遗漏，最小限定内核驱动以保持Bionic只复用同一冷owner，不增加假M4。"}
```

## A1 第八次：真实冷所有权导出通过，真实M4产品链接阻塞（不是TLS成功）

`7a721ae82c18e68db58af1b43b7fb3ce16057b0d` [Action44014838092](https://github.com/lly8666/wbd-next/actions/runs/44014838092) **整体FAIL/FULL_GO_LINK_M4_NOT_PORTED**。该Action内实际通过 Android ARM64 NDK静态ABI + 完整 `cargo release -p wbd-engine --target aarch64-linux-android` 与原共享Go-Rust冷控制 `prepare_client/stage/commit/stop` **真实 .so 导出检查**；原 Go CGo 产品源码也已编译到链接器。`ld.lld`仍报 `wbd_m0_embedded_go_attach_raw_rx/attach_tun/loop_start/route_refresh/Health/MTU` 等M4调用缺失，原因不是未连接server，而是原Linux raw/TUN worker尚未移植Android Bionic。不得生成空壳符号或用探针代码取代该认证所有权。**ARM64内核业务数据、TLS实际建链、真实认证/租约与Stop均NOT_RUN**。

之前每次遇到原Go arm64链接阻塞都不能证明x86_64的完整Rust包。现在只在构建脚本内先对 **两种 Android ABI** 完成 C 静态布局、共享Rust冷所有权导出和16KiB ELF/PT_LOAD检查，并写入具 SOURCE 的 `rust-cold-stage-manifest.json`；随后真实原Go客户端全链接仍保持失败闸门，不会因为第一阶段成功就冒称可安装运行。后续 A2 专注真实Android套接字、Raw/TUN M4 worker与原Go冷阶段接线，A3才做KSU↔Linux同源服务器业务实测。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"区分已通过的arm64共享Rust认证冷ABI与尚缺失的Android M4 Go全链接；重排A1为双ABI冷编译证明与真实Go链接独立闸门，留精确SOURCE证据且不发布假APK。"}
```
