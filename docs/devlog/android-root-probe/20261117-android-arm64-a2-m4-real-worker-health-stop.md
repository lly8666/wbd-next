# Android ARM64 A2｜同一原 Rust M1/M3 的真实 M4 双线程、Health 与 Stop 大批次

**基线**：实验分支 `e24beb636e3cc5bbbb43665cb74f9ac41639839b`；main `2fca1a93b4f9f7d3e7c5985adc356ade13332e86`。仅 Android arm64-v8a，不触及 main/M0 registry/cursor/PR Draft，不操作未授权Android16 KSU 真机。用户要求更大批次/可并行工序并行：本批合并Bionic原生唤醒、原Rust原生M4双线程、Health加密控制、MTU、owned Stop、源锁导出门及文档。

- 在原 `wbd-platform::android_root_io` 增加独立 owned `eventfd`×2和 kernel `poll` 组合 TUN/RAW+Stop FD，无10ms空闲轮询、无Go/Java逐包唤醒；所有 RAW/TUN syscall 借用维持既有 `r1::BorrowFence`，原物理 Network FD 每1s/工作时 readback ifindex和MTU，变化后停止，不放行默认出口。
- 新 `v4_android_original_m4.rs` 在**同一**原Go密码所有者 `Entry` 内起真正ARM64的RX/TX readiness worker；有界一次8个原生读写/turn、预留唯一原M1 arena输入、原`parse_data_packet`严格 tuple+checksum，独立原M3 AEAD/唯一PN后的Normal/off LINK重组+Auto lease /32后才写TUN；原FrozenRecord/seq/PN的原IPv4/TCP字节构造与带BorrowFence的RAW sendto，拒绝伪发收据和默默重封PN。
- Go冷配置健康间隔、Dead与dormant被当前原Go TLS epoch检查后交给同一个 `HealthPolicy`。TX原 `HealthClock` 通过`seal_original_authenticated_receipt`产生标准已有WBC4 Health kind0，**只有原PN对应的真实kernel完整拷贝**才更新Health send结果；RX原windows共享typed Health解析继续沿单个原M3重放bitmap验证canonical peer Health/idle/retire，进而唯一可标注peer dead、预重认证和实际peer-health，并不把外层TCP ACK或局部TLS Ready视为真实健康。
- `wbd_m0_embedded_go_stop` 在持有注册表锁之外唤醒+同步 join ARM64两个原线程，join失败不得Stop/Release原M1；join成功后原Rust owner.stop、RAW/TUN BorrowFence drain、唯一Arc持有检查和FD释放。新增真实 `loop_start/stats/authenticated_dead/predead/peer_health` ABI，加入ARM64原共享Rust C ABI导出强检查。不增加fake FEC/Game/原M2符号，不绕开原Go最终链接。

**真实阶段闸**：本 SOURCE 当前待Action构建，编译结果**NOT_YET_RUN**。就算真实Rust ELF+符号通过，仅代表**SOURCE_COMPILED_NOT_EXECUTED**；原Go正常 FEC2/Fixed/Game/M2 全链接仍缺真实模式/健康/数据收据 ABI，必独立验证。Bionic设备权限/RAW socket/TUN/健康计时/原worker Stop/连接、完整M3 jumbo、真实ARM64 KSU ↔ 同源Linux server 的标准TLS/auth/lease及双向TCP UDP性能，均 **NOT_RUN**。若构建失败以真实错误为准，不预先声称PASS。

**唯一下一步**：先用本 SOURCE ARM64 Action 判定上述真Rust worker是否可编译并独立导出；修复真实编译缺陷后，在不替换原协议的前提下完成原Go必要M2/Fixed/FEC/Game接线或将Normal/off有证据地源码隔离成可链接真产品，再完成 Root controller/路由真机授权验收。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"ARM64批次复用原Go授权/原RustM1M3实现Bionic RAW/TUN双就绪线程、加密HealthClock、物理MTU检查及双eventfd Stop同步join；同SOURCE真M4符号门，Go完整产品与真机未验。"}
```

## 第一轮 ARM64 编译与精确修复

- **SOURCE `f490df0670804814d6fb60ff2a9dd9699ffc147f`** [ARM64 Action44024127542](https://github.com/lly8666/wbd-next/actions/runs/44024127542) **FAIL**，原因仅报告两处 Rust `E0599`: Android 编译看不到已有 `ProtectedScopedOwner::normal_firstsend_identity`。该方法已有真实原Go TLS epoch+owner token 检查，但先前 cfg 只包含 Linux/Windows。不能宣称本 SOURCE M4 Rust 构建通过。Bionic C ABI 开始执行，但由于 Rust 出错，`.so` 导出和完整 Go 链接在本 SOURCE **NOT_RUN**。
- 同源 [governance44024127523](https://github.com/lly8666/wbd-next/actions/runs/44024127523) **PASS**、[governance-maintenance44024127561](https://github.com/lly8666/wbd-next/actions/runs/44024127561) **PASS**。没有 Android x86 目标，没有设备部署。主分支未修改。
- **本修复**：只将这个原 `normal_firstsend_identity` 的 cfg 扩到 Android arm64，保持原 active、detached、epoch 非零检查不变，不新建身份或替代接口；同时从新原生M4文件删除一个未引用、永不调用的辅助函数。当前修复 **Actions待执行**；不提前宣称通过。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"M4 SOURCE f490 ARM64 编译首次FAIL精准定位两处原TLS身份方法Android cfg缺口；原方法目标编译修正且去除未用助手；治理PASS，真机M4仍NOT_RUN。"}
```

## ARM64 M4 Rust ELF真实导出 vs 源锁 grep -q/pipefail 误报

- **SOURCE `2b8e662547e8d994f6ae201f3ad414019bd63774`** [ARM64 Action44024436340](https://github.com/lly8666/wbd-next/actions/runs/44024436340) **overall FAIL**，但已明确不是新增原Rust M4 compile/link出错：`cargo +1.85.1 build --release --target aarch64-linux-android -p wbd-engine` 实际 `Finished release`，生成唯一 ARM64 `.so`；出错点是 `set -euo pipefail` 下 `llvm-nm -D "$lib" | grep -Eq " [TW] symbol$"` 的 grep `-q` 提前退出，导致 `llvm-nm` 的 SIGPIPE 非零码被 Bash `pipefail` 判成假 `MISSING wbd_m0_embedded_go_prepare_client`。
- 已独立读取 [artifact14301758387](https://github.com/lly8666/wbd-next/actions/runs/44024436340/artifacts/14301758387)，下载 ZIP SHA256 `47279d89e5ddfe67d5be7a4be7c2351be708e7ee084c53da3a0e368696667c86`；其中 `libwbd_engine-arm64.so` SHA256 `df8ad737e631e66b99e836422d8c33d844036d5e4d972b47ba1ea9842417764e`，ELF64 AArch64 machine183、PT_LOAD min alignment 16384，`readelf -sW` 和 `nm -D` **实际看到 `wbd_m0_embedded_go_prepare_client`、`loop_start`、`loop_stats`、authenticated_dead/predead/peer_health、native_health_config/effective、android_raw/tun attach、Stop/Release** 为 GLOBAL/动态导出；因此可写 **M4 ARM64 源码/真实 Rust ELF 编译 PASS**，但绝不是 Android 上真实 M4 运行 PASS。
- **本修复**不是跳过ABI：将 `llvm-nm -D` 输出预先完整重定向一次到同源 ARM64 ELF `.dynsym.txt`，再逐个对文件执行相同的严格 `[TW] symbol$` 检查，避免管道SIGPIPE 假失败。真实缺失符号仍 FAIL，允许下一步进入**原 Go 完整产品链接**核实，不会用伪造 C ABI 兜底。
- 该 SOURCE 没有跑到原 Go product CGo link；Go FULL LINK **NOT_RUN**；Android16 KSU真实原 Go TLS/认证/lease，M4双向 TCP/UDP、Health/MTU/Stop真设备均 **NOT_RUN**，FEC/Game仍未完整Android移植。Feature/Governance `[Action44024436425](https://github.com/lly8666/wbd-next/actions/runs/44024436425)` **PASS**。

**唯一下一步**：在同一ARM64 ABI导出严格门通过后跑原Go完整链接，定位未移植原M2/Fixed/FEC/Game真实符号，逐项真实移植/有证据的Normal-off原Go产品源分层，不添加任何无行为假占位。随后获设备授权再真机验收。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"SOURCE2b8e ARM64原Rust M4真实ELF/Health/eventfd等符号已动态导出、16KiB验证；CI grep-q+pipefail误报已改全符号表文件逐项严格校验；完整Go链接与真机依旧NOT_RUN。"}
```
