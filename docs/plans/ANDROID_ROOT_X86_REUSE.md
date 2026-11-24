# Android x86 KVM/KSU 与 ARM64 NativeBridge 测试复用（B83）

**2026-11-24 B83 用户范围冻结（当前最高优先级）**：除手机端显式手动联网更新官方 CN 域名列表（唯一功能待办；已有内置8472、文件导入/恢复）外，所有 Android 主体功能标记为基本完成开发、转入验证；未实现的高级功能冻结不开发，不把它们说成已接线。只修实际测试发现的业务/性能问题，不扩极端工况。高级 CN FakeIP 仍 OUT_OF_SCOPE。优先复用一次 Android16 x86 KVM/KSU guest 跑 ART 冷控制、x86 原生原Go/Rust、ARM64 NativeBridge 真 Rust MTU 和原Go c-shared help；原 ARM64 独立 Go ELF139 与 hosted SLIRP/TAP RAW 路径阻塞保持历史，不为冷测试重开这些诊断；ARM64 真机集中验证真实业务、内核设备差异和性能。

## 历史证据（真实 SOURCE，不重新认定为 B83）

- [43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528)：真实 Android16 x86 KVM/KSU3.3.1，旧 x86 探针普通 UID、Root、TUN/RAW/UID/私有 DNS 能力。不是原 WBD 完整业务。
- [44126602143](https://github.com/lly8666/wbd-next/actions/runs/44126602143)：ARM64 NDK 执行、原 Rust dlopen/dlsym 通过；纯 Go CGO0 和正式 Go ELF 均 SIGSEGV139。不是产品协议 FAIL。
- [44138382581](https://github.com/lly8666/wbd-next/actions/runs/44138382581)：隔离复制 Go1.23.12 MIDR 探测 + 测试专用 noasm 后，NDK 调用原 Go c-shared 的真实 Run(client,--help) exit0；正式 APK Activity启动 PASS；原 ARM64 独立 ELF仍139。不能用替代测试库作正式 ARM64性能/运行资格。
- [44236693889](https://github.com/lly8666/wbd-next/actions/runs/44236693889)：原 x86 Go/Rust 同源签名 CI APK，普通 App→KSU→su root、正式 NativePayload 与 PhysicalNetwork exact readback PASS。
- [44251978166](https://github.com/lly8666/wbd-next/actions/runs/44251978166)：原 x86 RootClientService 真 Go Root 进程、TUN、AF_PACKET及原 Linux server启动 PASS；TLS/lease/M4/Stop 未证。
- [44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998)：SLIRP/TAP/Wi-Fi TAP 未拿到原业务 RAW SYN/SYNACK；TAP guest物理网络读回成功但无实际 TAP L2 RX，属于 ENV_BLOCKED_NETWORK_PATH，不是原协议FAIL。ARM64 hosted KVM也曾不可用。

## 新的可复用单轮冷套件

使用现有 CI 原 x86 Go/Rust 产物、官方 CN 数据和原 ARM64 NativeBridge 诊断资产，沿已成功的 KSU AVD 初始化（首次准备与重启必要，不额外为每项另开 guest）。同一最终 guest 内：
1. 原生产 Java Activity/NativePayload、真实普通 UID、KSU su、PhysicalNetwork readback 与原 x86 Go CLI。
2. 在实际 Android ART ordinary App UID 上执行既有六类真实生产 helper 断言：7模式设置、四配置 SAF codec、Go argv、冷轮换/恢复决策与 Network callback gate。不是系统回调/实际转发证明。
3. 复用 ARM64 NDK launcher + 原 ARM64 Rust .so，实际调用生产 wbd_m0_v4_mtu_budget_v1，核四种 MTU 类别的 1460→1389/1375/1373/1358（覆盖七种模式预算类别），不是单纯加载。另调用历史已证明的原Go c-shared CLI help。记录独立结果及资产hash，不重跑原ARM64独立ELF139，不修改产品Go/Rust或采用测试库作正式包。
4. x86 guest原始 D2/SLIRP、TAP 和旧整套NativeBridge诊断各独立手动选项；cold suite默认不启动它们。

执行方式：新 [Android cold suite reuse](../../.github/workflows/android-root-cold-reuse.yml) workflow 在实验分支手动选相同SOURCE的已完成产品run ID，从该 run 下载同源 native/CN assets，不重复构建Go/Rust/Linux oracle。即使产品总run因旧字符串门失败，也可复用实际已通过且校验完整的native/CN artifacts。仍由本次 guest 真实输出独立判据。也可在原 dual64 workflow手动只开 run_x86_guest（会重新构建，不优先）。没有兼容环境时据实NOT_PROVEN，不无界重试或修改产品适配层。

## 哪些能减少实体工作量

| 测试域 | 优先放到 x86/转译 | 实体保留 |
|---|---|---|
| UI、七模式冷参数、配置/文件codec、选网决策 | ART与普通App框架；真实UI交互/SAF另按可用夹具 | 一次安装/界面/实际手机配置冒烟 |
| KSU权限、原生资产、原Go CLI、MTU冷预算 | 原 x86 + 真实ARM64转译Rust ABI | 正式ARM64 Go ELF原生执行、设备内核能力 |
| TUN/RAW socket、UID路由与清理 | 历史原x86 preauth、旧诊断真实内核能力；未来只复用已可达的同源路径 | 当前SOURCE实际认证后路由、真实停止清理 |
| DNS、CN、FEC、Game、外层修复等算法 | 现有 Rust/Go Host 真回归；可逐步增加转译纯函数测试但不为此扩大工程 | 真实双端业务、实际mode/路径/readback |
| IPv6/464XLAT、系统DNS、热点、Wi-Fi/蜂窝切网 | 冷逻辑/相关Host，不宣称真实设备功能 | 真实内核模块、netd、下游与物理Network |
| 端到端与性能 | 原 Linux 同源 Oracle，模拟器普通网络不代表FakeTCP | ARM64真机七模式短业务、实际ISA-L、CPU、吞吐、唤醒、RTT |

结论：先消化重复配置/权限/冷参数/MTU/构建检查，让手机不承担这些逐项重复测试；真实 FakeTCP/M4、Android 物理系统行为和性能依然需要真机。不要承诺“转译等于真机”。本次新套件尚未执行，任何新增结果一律 NOT_RUN，非历史 PASS 迁移。
