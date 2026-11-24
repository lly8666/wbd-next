# B85｜集中并行 Android 模拟与双架构原协议验证

基线 `d54fe06b3305fb433c96f8e6588382adf44dc400`。用户授权大规模并行模拟。仅 CI / 测试脚本和记录变更，正式APK产品代码与 Go/Rust 协议不变，main/M0不动，Draft PR36。

## B85 并行批量模拟（本轮显式触发）

B84 实际 [Action 45373452414](https://github.com/lly8666/wbd-next/actions/runs/45373452414)：ARM64/x86 native、签名 ARM64 APK（[artifact 14910378010](https://github.com/lly8666/wbd-next/actions/runs/45373452414/artifacts/14910378010)）、APK wiring、官方更新器逐条8472条、Host DNS/Rust、原 Linux oracle、维护/功能目录均实际PASS；root-app 最后历史UI源码字符串断言FAIL；KSU job在下载产物目录校验FAIL（未启动模拟器）。B85修正两处，不把前次失败改成PASS。

同SOURCE 构建产物共享：ARM64正式APK+普通UID fixture（构建一次）；Android x86/ARM64 native assets（构建一次）；原 Linux x86/ARM64 CLI+Rust（各构建一次）。提交标记 [android-parallel-test] 自动开启独立场景，fail-fast false：
- 2个 stock x86 KVM guest Android API35/API36：安装真正签名ARM64 APK（Java UI，不执行ARM64独立Go），真实四页导航和四种接管/分流组合截图；实际独立普通UID TCP/UDP回显夹具，经10.0.2.2仅验证模拟器普通网络/夹具，不冒称WBD。
- 1个 Android16 KSU 冷套件：x86原Go/Rust、普通App Root、ART七类cold helper、NativeBridge ARM64实际Rust MTU与原Go c-shared CLI。UI、ART、转译独立收据。若UI/ART失败继续尝试翻译，不修改正式ELF。
- 1个 Android16 KSU D2-S1：复用已证明原 RootService 到原 Go TUN/AF_PACKET，自动批次仅到真实 preauth 立即停止；不反复试已知SLIRP/TAP握手阻塞，不将成功归为M4或认证Stop通过。
- 14个独立原生 Linux 场景（x86/ARM64 × 7模式）：复用原 W167 LinuxExperiment 真实两端 Go TLS/Rust M4/内核 TUN 和 UDP 业务/owned namespace cleanup。20s、10Mbps每方向、1% IID、75ms 标准轻弱网，最大7并行，不做极端容量测试；保存每场景原始指标/独立结论。它们属于共享Linux协议验证，不是Android E2E或手机性能。
- 原有 Host / 源码门 / M3 / DNS / CN / Linux normal wire / 治理保留；旧NativeBridge ELF139、Cuttlefish、TAP不自动重试。

总计18个增强场景（4 Android guests + 14 Linux模式参考），其中原KSU冷job与D2 job为既有job复用。全部新SOURCE未运行前NOT_RUN；不要跨SOURCE或跨平台迁移PASS。用户明确授权Actions模拟，不部署真实手机或外部服务。


```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Fix real B84 artifact path and obsolete UI assertion, reuse signed APK and native bundles across four Android guest scenarios and fourteen same-source Linux native mode references with independent receipts."}
```
