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

## A2 Normal/off 真源码分层 + Feature Catalog 16KiB 治理恢复

- **SOURCE `69f262e13df239bb84fde42d4492d03c8257ac4f`** [ARM64 Action44024830339](https://github.com/lly8666/wbd-next/actions/runs/44024830339) **overall FAIL**。完整Rust ARM64 M1/M3/M4/Health/eventfd Stop `.so` release 和真实动态导出 ABI 严格校验通过、16KiB ELF通过；已进入**原 Go 产品最终链接**，失败的主体是尚未移植Android的原Fixed/FEC/Game/M2 native符号（也含normal_off_readback）。Go最终完整产品仍FAIL；真机仍NOT_RUN。
- [Feature Catalog Action44024830317](https://github.com/lly8666/wbd-next/actions/runs/44024830317) **FAIL**：`tools/feature_catalog.py` 原有16KiB单卡UTF-8限制被增长的历史 `limitations` 超过；本批压缩冗余历史描述、保留verifications/原devlog完整错误详情，**绝不放宽原16KiB治理标准**。
- 本批 ARM64 原 Go 改用**源码已有** `!wbd_v4_fec2_product` 发行分支，原Normal/off TLS/租约/同RustM4链路不变，原Go对Fixed/Auto/Game2/4采用其已有 `ErrAdmissionUnsupported` 实际fail-closed行为。既不冒充已做FEC/Game，也不为Normal/off首连引入未授权替代协议；Rust codec保留编译，模式/版本的正式成熟移植放后续。
- Android新增`normal_off_stage/readback`：同一原Go认证TLS非零epoch、feature3、同代际Active、strictly-increasing revision才发布真实OFF状态并读回；不复制Linux Fixed/FEC事务，也不伪造APPLIED、M2收据。Native CGo原stage/readback ABI不是空壳。

本 SOURCE 的 ARM64 Action/完整Go linker后续如实记录；Android16 ARM64 KSU真实原Go TLS/auth/lease、M4 TCP/UDP收发、Health/Stop与应用/Root Controller仍**NOT_RUN**。唯一下一步是消除真实Normal/off必需的Go链接/运行前置项，再获真机授权连接同源Linux WBD。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"同源ARM64 Bionic Rust M4真实链接已过，改用仓库已有原Go Normal/off源码版，Fixed/Game不再拉取未实现模式且明确fail-closed；Android原TLS epoch单调OFF revision真实 ABI与16KiB功能卡治理修复。"}
```

## Normal/off Go type闭包：仅Android source-locked原TLS真实类型

- `116164a89d329d05216cb768f8aed369fed61172` [Action44025435963](https://github.com/lly8666/wbd-next/actions/runs/44025435963) Rust ARM64原M4/Health/Stop与源锁严格导出BUILD_PASS，但原Go `!wbd_v4_fec2_product` 版在 **Go源代码类型检查** 阶段FAIL：`bridge_v4_linux_server_product.go:180:11: undefined: V4LinuxGameAuthenticatedLane`；原成熟Game代码只在`wbd_v4_fec2_product`标签存在。完整Go link此源码 **NOT_RUN**；A3真机同源TLS/UDP/TCP仍NOT_RUN。相同SOURCE功能卡16KiB治理 [Action44025435946](https://github.com/lly8666/wbd-next/actions/runs/44025435946) **PASS**。
- 本批仅Android `!wbd_v4_fec2_product` 原Go源码增量定义 `V4LinuxGameAuthenticatedLane` 的**真实受保护Normal模式**参数类型及 `ProtectedMode`：强检查已认证 ColdSnapshot/原Rust commit/原FakeTCP association、原已验证的policy.Transport==Normal、1 lane、NormalFEC与GameFEC均OFF。真实Game/Fixed仍错误拒绝；没有新增Game native入口、伪造M2或绕开原Go TLS。Linux/Windows源文件不更改。
- ARM64 Rust真实 `normal_off_stage/readback` 同认证epoch/单调revision导出符号加入精确动态ELF必需名单；治理卡删重复的旧日志说明（记录仍在不可变devlog/verifications），保证 UTF-8 长度低于仓库原16KiB硬限制。未宣称本SOURCE编译或真机已PASS。

**下一步**：用同SOURCE ARM64 Actions验真 Go Normal/off 源码类型闭包与完整原CGo链接；对剩余真实原M2/Health/Stop控制ABI做原能力移植，未完成不能认为可正式连接；真机授权后再进A3。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"仅Android无FEC版原Go源锁补真实TLS受保护Normal lane类型/模式验证，Game和Fixed仍显式不可用；原RustOFF真实ABI纳入符号门，16KiB功能卡重复历史压缩。"}
```

## A2 原Go无FEC Normal客户端的冷 ACK 与Game supervisor 正确分层

- 前 SOURCE `3349c63291a5d40e725d36fb34fb71d75c80f9e4` [ARM64 Action44025826215](https://github.com/lly8666/wbd-next/actions/runs/44025826215) 原Rust ARM64 M4 / Normal/off stage/readback 编译和动态ELF符号导出 **BUILD_PASS**，原Go已有真实认证Normal lane类型的编译问题修复。Go包 `internal/realityfront` 源码检查通过，但 `internal/v4productcli` 再报告三个精确缺口：原 `repeatOriginalDetachedTLSFinalACK` 定义被Game build-tag包住、无Game变体 `runGameClientGeneration` 仅6参数而原路径supervisor用7参数、缺原cold candidate错误分类常量。因此本SOURCE Go **类型编译FAIL**，还没到最终Go链接。 [Governance44025826225](https://github.com/lly8666/wbd-next/actions/runs/44025826225) **PASS**。
- 本批只给 Android `!wbd_v4_fec2_product` 自己的新 `game_disabled_android.go` 保留**完全相同**原 `game_linux.go` 的有界Cold FinalTLS ACK duplicate（<=4480ms、仅verified FakeTCP Detached、原association+原tuple）、七实参 supervisor 函数签名和受控 cold candidate 分类；Game2/4运行严格拒绝，绝不允许Go独自起另一个虚假Game lane。原 `game_disabled_linux.go` 只加 `!android` build-tag，Linux构建逻辑不改变。无需复制Game FEC/Engine M4。

同SOURCE Actions后评估本批完整Go CGo链接；Android16 ARM64 KSU真机、标准TLS认证lease、TCP/UDP数据、Health/Stop性能均NOT_RUN。不跳过任何原Rust真实native符号闸；缺口只能用现有真实原Go行为/原Rust逻辑补全。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"ARM64无FEC Go原产品保留真实Normal冷FinalACK原逻辑及原Game路径supervisor 7参签名，Game严格不可用；Linux build tags不改运行，治理/真实M4仍保留。"}
```

## ARM64原Go Normal/off真实CGo链接之后：修复认证/32与实际物理预算

- SOURCE `33c4b2883064ea295a98bf1433f5ea3d940d2fd6` [ARM64 Action44026223115](https://github.com/lly8666/wbd-next/actions/runs/44026223115) **overall FAIL**：单ARM64 Rust M1/M3/M4/Health/eventfd/Normal off release BUILD_PASS、完整动态导出符号严格校验PASS、ELF16KiB PASS；原Go `realityfront`/`v4productcli`类型编译PASS，实际已经走到原Go最终 `ld.lld`。**真Go最终链接FAIL**仍缺原 `fixed_stage_pending`/`fixed_pending_readback`、`arm_public_original_m2_feedback`、`client_shared_tun_promote_after_rx`、firstsend-M2与其coverage、route-event/route-refresh/CPU/outer FEC counters 等，以及两个原产品关键认证与MTU接口。不能把该 Go ELF 标产品BUILD_PASS。[Governance44026223142](https://github.com/lly8666/wbd-next/actions/runs/44026223142) PASS。
- 本批源码还原了已有原`bind_authenticated_client_ipv4`的 Android可见性：之前两个 cfg 相与意外要求 Android目标是Linux GNU/musl，导致原已实现的 Go TLS认证lease /32从Bionic动态库消失；现在使用Linux原架构或Android arm64的实际 OR target guard，**内部仍限原Go认证/已OS安装地址、原同一generation、RAW/TUN开工之前**。不是任意用户输入/IP自证。
- 新Android ARM64真实`observed_tx_ipv4_mtu`：原Entry活跃、原Go/32客户端授权、精确物理ifindex和RAW/TUN存在；**在原绑定RAW TX socket 上**重新验真物理MTU，不调用默认网络，然后由原Rust `android_normal_off_frame_budget` 的peer MSS、record/LINK/AEAD扣减返回单一inner IP limit。错误必须fail-closed；不复用 Linux 特定 netlink驱动。两真实C ABI已加入原ELF严格符号校验。

当前新提交前未跑Action，完整原Go M2/SharedTun/route/FEC等仍真实缺口，**Android真机运行/标准TLS/auth/lease、双向TCP/UDP、Health/Stop**全部 NOT_RUN；不为绿灯添加假函数。唯一下一步：对原Go产品链接余符号按原实现进行平台真正移植/按明确未启用模式收敛依赖，再获授权在ARM64 KSU同源真server实测。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"ARM64原Go Normal/off首次走到真实ld.lld链接并精确列出剩余原M2/FEC/route符号；修复原认证租约/32被误加Linux条件遮蔽，新增真实绑定物理RAW+原Rust预算的Android MTU读回。"}
```

## 本轮最终SOURCE/Action证据冻结：ARM64原Rust M4 ABI已完成构建，Go产品仍未链接

- **SOURCE** `1b044ed3f76a4674e75ee409fe9746ba22343e84`，唯一 Android目标 `arm64-v8a`；[ARM64 Action44026702035](https://github.com/lly8666/wbd-next/actions/runs/44026702035) **overall FAIL**。但其中真实 Bionic `android_abi.c`、共享 Rust 原AEAD+PN/M1/M3+M4双线程/eventfd/Health/Stop、原Go认证后的租约 `/32`、真实绑定 RAW TX 读回 MTU/FrameBudget、Normal/off revision C ABI 和 16KiB ELF **BUILD_PASS**。原-Go无FEC版的 `realityfront`、`v4productcli` 和 cmd/wbd-v4-client 所有 Go 代码已编译到最终CGo `ld.lld`，**最终链接 FAIL** 于原FEC/M2/SharedTun/route/diagnostic余符号，完整原Go二进制仍不存在。
- 与上一SOURCE相比，两项实际产品FFI `wbd_m0_embedded_go_bind_authenticated_client_ipv4` 和 `wbd_m0_embedded_go_observed_tx_ipv4_mtu` **不再在undefined symbols名单中**；其真实Rust函数已由ELF符号表/同source严格nm验证为 GLOBAL FUNC。这不是用stub应付原Go链接；Native旧Fixed/成熟M2、共享TUN代际promotion、route/quality等仍需原实现，错误列表受lld默认20条截断，不能据此断言其余ABI已解决。
- [Artifact14303282058](https://github.com/lly8666/wbd-next/actions/runs/44026702035/artifacts/14303282058) 已独立下载并核验：ZIP SHA256 `861529ae769e5463f8fe1cf1de15a0a8cc3ae2bb526136135fd9f1e3953f4d70`；唯一 `libwbd_engine-arm64.so` SHA256 `49c0b53fdcdfbd13419e641d35df29de09254beb042e701b4acdafcc23ce2331` 与真实内置manifest一致，ELF machine=183，PT_LOAD最小16384；同包有 `SOURCE`、`abi-arm64.o`、完整 `.dynsym.txt` 和`rust-cold-stage-manifest.json`，无Android x86 ABI。stage manifest诚实标 `SOURCE_COMPILED_NOT_EXECUTED`，Go full linker由后续真实日志判FAIL。
- [Governance44026702031](https://github.com/lly8666/wbd-next/actions/runs/44026702031) **PASS**。本批不触碰main/M0 registry/cursor、不改变Linux/Windows x86行为、PR#36仍Draft；未获取真机额外部署授权。
- **NOT_RUN**：原Go Android16 ARM64 KSU 与真同源Linux WBD服务端标准 TLS ClientHello/auth/lease、任何实机M4 TCP/UDP 双向业务、真实内核RAW/TUN权限、M4 owned线程join/Health/MTU切网、系统DNS/应用路由/热点USB/p99/CPU/RSS。不得依据ELF源码编译称产品连接通过。

**唯一下一步**：优先把原Go `!wbd_v4_fec2_product` **未启用**的Fixed/FEC/Game源码引用按明确不支持的原能力边界拆分，真正需要的原M2/SharedTun/route/Stop状态则按原Rust实义移植，不加fake C ABI/跳链接门；使ARM64原Go Normal/off二进制全链接，再进入受授权设备 A3 真机验证。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"SOURCE1b044 Action44026702035真实ARM64 Rust M1M3M4/Health/Stop/认证lease和物理MTU、ELF/导出PASS，原Go CGo最终链接仍FAIL；ZIP/.so SHA验证和Gov PASS封存，真机NOT_RUN。"}
```
