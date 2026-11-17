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
