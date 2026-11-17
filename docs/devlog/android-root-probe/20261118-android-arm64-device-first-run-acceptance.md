# Android16 ARM64 KernelSU 首次集中联调：正式APK固定事件收据 + 只读ADB采集（2026-11-18）

**范围**：只向 `experiment/android-temp-root-probe` / Draft PR #36 施工；不碰main/M0/registry/cursor、不安装任何真实用户设备。开工主分支 HEAD `9d2111debc6cb1e8c27373644624d7f0aef3bf6c`，原Android产品验证 [Action44138382581](https://github.com/lly8666/wbd-next/actions/runs/44138382581) 是**10/11 PASS，总体 FAIL**：x86_64 KVM Android16 KSU NativeBridge NDK→隔离MIDR/noasm的完整原Go c-shared `Run(client,--help)` 真 exit0；正式签名APK里原Go ARM64 ELF直接启动 **SIGSEGV 139**。不得将诊断入口替代最终产品，真实ARM64 KSU实体手机仍未执行。

## A9 最小正式产品安全诊断与集中验收

- **正式Root Service未替换**：仍用原 `ProcessBuilder("su","-c",...)`、实际原Go ELF+同源共享Rust、真TLS/认证/租约、内核RAW/TUN/唯一Rust M4和所有原来的精确 generation/PID/starttime Stop；没有替代二进制、JNI逐包、fake TLS、VPN、FakeIP、root全局杀进程或自动改路由。
- 新建纯Java `RootDiagnosticReceipt` 仅接受编译期固定`enum Event`，写入 app 私有 `files/wbd-root-diagnostic.txt`，超过16KiB按旧代边界轮转，文件owner-only权限，额外 `android.util.Log.i("WBD_ROOT_DIAG", event.name())` 提供设备端ADB读取。只输出毫秒时间戳和事件码；**不输出**username、password、route key、peer、UID/package、Network handle、owner generation/token、TLS或原native日志。IO失败不会阻挡Go/Rust Stop。Service在真实状态点加Network验证/UID校验/真ARM64 SHA确认/su进程创建/原Go M4就绪+路由readback/退出码类别/Stop信号与收尾阶段；不把TERM发送当作Go/Rust join，也不把根权限进程创建当真实授权成功。
- 新建PC侧纯标准库 `android/root-app/ci/device_first_run.py`：会先核对ADB授权设备、真实**kernel `uname -m=aarch64`**（绝不从 x86 NativeBridge `abilist=arm64-v8a`推断）、Android16 API36、安装的原APK、本地APK内真正AArch64 16KiB ELF/manifest SOURCE SHA。只读`ip -4 rule show`采集 WBD 专用priority9600..9607/table19842的优先级和哈希，不暴露UID范围/IP。默认从`logcat WBD_ROOT_DIAG`提取已知枚举值，不保存raw logcat。**用户在APK界面自行选择真实Network/安装App并按Start、Stop**；脚本每阶段等待用户按Enter，最后读回专用规则并生成私有`acceptance-bundle.zip`（只含结构化JSON），无shell su、无kill、无路由修改、无自动恢复已存在foreign规则。
- 唯一主动可修改手机的操作是操作者**显式选择** `--install --apk FILE` 的`adb install -r`；默认不执行安装、卸载或任何Root命令。对已有WBD私有规则或非原生ARM64环境，提前拒绝启动 Activity；用户自行按APK Stop。支持`--collect-only`只读收集。
- A9来源锁Host验收：编译并执行真实Java enum私有收据轮转/拒绝自由字符串测试；执行ADB脚本离线unittest（真实Arm64 ELF负例、UID规则脱敏、源SHA/16K APK资产校验、被动Stop不能伪称join或Android E2E、输出ZIP无凭据）；签名APK常规API35 javac/d8/aapt2/apksigner和SOURCE验证依旧运行。**Host测试是软件审计，不是设备PASS**。正式DNS `android_dns_hijack_ready=false` / `android_dns_physical_ready=false`保持冷状态，CN8503/tunnel/physical TCP53/Resolver未入场。

## 分级收据解释与设备验收边界

`NATIVE_SOURCE_VERIFIED`仅表明 APK 内原生hash资产已在App中验证；`ROOT_PROCESS_LAUNCHED`只表示su进程创建，不能单独证明Root获权；`NATIVE_M4_AND_UID_READY`必须同时观察真实原Go两个 native receipt，仍不等于用户TCP/UDP应用数据已经通；`STOP_SIGNAL_ACCEPTED`只表明精确代号/PID信号发送成功，**不是原Rust线程join**；`ROOT_PROCESS_EXIT_ZERO`和`OWNER_CLEANUP_FINISHED`只证明Service退出并执行Java清理；专用规则readback为空只表示检查时没有该前缀，完整路由与跨层Stop仍需后续确认。同源Linux真服务端、用户App真实数据与系统DNS没有自动检查的一律`NOT_RUN`。

真正ARM64 KSU手机首次集中测试需要用户独立设备授权、网络测试条件和本人在APK内Start/Stop；本批仅构建可运行的正式APK诊断链与测试脚本，不触碰用户设备，不把 x86_64 KVM 成功误称为ARM64内核成功。产品A9全部SOURCE CI最终结果以提交后的GitHub Actions判定，禁止提前写PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"首次ARM64 KSU集中验收所需正式Root Service固定脱敏阶段收据/原Stop保留/PC端只读ADB诊断与有界私有规则回读，host Java/Python严谨验证；设备未运行。"}
```


## A9b 强化正式原Go成功Stop/回滚证据（不加新协议）

对真实原 Go `linux.go` 行为的源码核对：`V4_PUBLIC_LEASE_APPLIED role=client`仅在真实受保护TLS/32租约通过本地OS配置readback后打印；`V4_PUBLIC_GO_RX_HANDOFF role=client`在原Rust M4启动并交出原RAW/TUN归属后打印；`V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client`仅在调用原Go rootjournal Stop撤回UID路由成功后打印；`V4_PUBLIC_NATIVE_STOP_DRAINED role=client`只在撤回路由且`native.Close()`真成功（原Rust线程/loan join）后打印。这些固定字符串在正式 Service 根进程stdout处理内仅映射为固定事件码，不输出含凭据/网络状态的原native日志。非零进程退出中`132`/`139`单独输出固定FAIL分类；不把Shell signal当native Stop。

ADB首测脚本除UID rule pref9600..9607/readback，还检查真正的**私有表19842 IPv4路由**与本地非持久`wbdv40` TUN是否消失。三种资源都只输出状态/哈希，读权限不足标`NOT_RUN`，存在残留标`FAIL`且不执行自动清理。真正原Go Rust Stop需要原 M4/UID就绪、用户 Stop、原`V4_PUBLIC_NATIVE_STOP_DRAINED`对应固定事件、原生进程exit0才可标PASS；Android↔Linux应用数据回环与系统DNS仍保持`NOT_RUN`，不以单机日志冒充真实包验收。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"新增真实原Go TLS租约/Rust接管/UID route撤回/native.Close joined Stop固定码与SIGILL/SIGSEGV固定FAIL，ADB原路由表/TUN资源回读、只读无Root改动。"}
```
