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
