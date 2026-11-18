# A14｜A12 真机临时 TUN 提前消失：修正 FD 握手 + 正式原 Go 冷路径证据

日期：2026-11-18。唯一施工分支 `experiment/android-temp-root-probe`，Draft PR #36；不写 main/M0/registry/cursor。
用户要求继续开发到手机真实跑通。本轮未获用户设备交互通道、同源 WBD 服务端或凭据，**不宣称真机已连接或部署**。

## A12 实机失败与新审查结论

用户 Android16 ARM64 KernelSU A12 `NATIVE_ARM64_KERNEL/ROOT/GO_ELF_HELP/TUN/RAW/UNDERLAY/ROUTE_UID/ROUTE_ROLLBACK=PASS`，但 `A12_TUN_INTERFACE_DISAPPEARED`、`A11_UID_TUN_ROUTE_FAIL`、`A11_UID_TUN_ROLLBACK_PASS`，`REAL_APP_UID_TO_TEMP_TUN_PACKET=NOT_PROVEN`。
之前 DEBUG helper 写 `.uidready` 后立即进入一次 9.5s `poll`；Shell 尚在配置地址、接口 up、route/rule、UID readback 时，非持久测试 TUN 的唯一 FD 可能提前关闭。此生命周期竞争确实存在于源码，但尚未确认是**唯一**真机根因，不推广到原 Go/Rust 正式 TUN。

## 本次代码和安全边界

- **修正既有隔离测试而非新增 probe**：NDK ARM64 helper 必须在 Root-owned 0700 目录内等待 0600、root UID、单硬链接、`O_NOFOLLOW | O_NONBLOCK` arming marker（预备限时20s），才启动独立 9.5s TUN 收包计时；等待期保留原唯一 FD。测试 Shell 仅在确切 `ip -4 route get 192.0.2.1 uid <原APK UID>` 回读命中 `wbdst11` 后建立 `.uidarmed`，启动前/`trap EXIT` 双清理。保持 `table19843/pref9699`、单固定测试 UDP、无 TUN persist、无全局路由/DNS、fail-closed rollback。Host Java/SOURCE audit 验证 handshake、cleanup、timeout 顺序；没有设备证据不宣称 TEST PASS。
- **正式 APK 冷路径改进**：新 `OriginalGoMilestones` 只接受原 Go 行首或默认 `yyyy/mm/dd hh:mm:ss` 日志前缀后的完整固定标志，不再在任意 stderr 中用 `contains` 误认 TLS/UID/Stop。实际原 Go kernel TUN 配置、RAW socket、收到 SYNACK 分别记录非认证的固定枚举；非零退出显示最后已观察的 `PRE_TUN/TUN_PRE_RAW/RAW_PRE_SYNACK/SYNACK_PRE_AUTH/LEASE_OS_READBACK/NATIVE_UID_READY` 阶段。保持真实原 Go TLS/auth/lease、Rust M4、Go rootjournal owned Stop、不伪造业务 PASS。
- **生产 TUN ownership 审查**：正式 `linux.go` 的 `ownedTun.f` 持有 FD，`AndroidOwnedTun` 接受 FD 并通过 Rust Arc/BorrowFence 保持生命期，不采用 helper 未经路由准备直接 `poll(9500)` 的模式；因此没有凭此单条 A12 失败盲改原生产 Rust M4。

## A14b 脱敏收据下游同步

审查发现正式 Service 的新增原 Go 冷阶段虽然会写入 App 固定事件日志，
但 `android/root-app/ci/device_first_run.py` 使用独立固定 `EVENTS` 白名单，
若不更新，脱敏真实设备报告会无声遗漏三条新枚举。已同 SOURCE 增补白名单和
Host Python 正/负例：`ORIGINAL_GO_TUN_KERNEL_CONFIGURED`、
`ORIGINAL_GO_RAW_SOCKET_READY`、`ORIGINAL_GO_TCP_SYNACK_SEEN` 可导出；
未知动态字串拒绝，以上阶段不能替代 TLS 租约、Android TCP/UDP 或原生 Stop。
A14 首次源码 `e8b0d472` 只有部分施工，**最终可上机 APK 请以包含本修正的
新 SOURCE 和其 Actions artifact 为准**，不能混用两个 APK 的收据。

## 证据门

本 SOURCE 自动跑 `.github/workflows/android-root-product-a1.yml`：原 Go/Rust ARM64 Bionic ELF、source-locked signed APK、原 Linux Normal/off server oracle、Java/Python 审计、独立 x86 KSU NativeBridge 任务；**写入时新 SOURCE CI 结果待核验**。此前 SOURCE `466b6415` 的 10/11 不是本 SOURCE PASS。原真实 Android TLS/auth/lease、App 双向 TCP/UDP、原 Go/Rust joined Stop、系统 DNS 安全开关均保持 `NOT_RUN`；A12 UID 实包仍 `NOT_PROVEN`。

后续实体操作需要用户在自己设备上明确安装/启动及真实同源 Linux 服务端、有效凭据后回传不含敏感内容的固定事件码；Root 域任何内核所有权更改不得绕过 readback 或默认接管系统 DNS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修正 A12 既有 Android ARM64 测试 TUN FD 与 UID 内核路由准备间的竞态；正式 Go Root APK 原生日志阶段只认完整固定行首、记录 TUN/RAW/SYNACK 非认证里程碑；Host/NDK/签名 APK 源锁回归；真机 TLS/M4/Stop/DNS 仍 NOT_RUN。"}
```
