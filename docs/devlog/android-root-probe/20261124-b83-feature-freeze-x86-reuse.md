# B83｜主体功能冻结，复用 Android x86 KSU + ARM64 NativeBridge

基线 B82 `8d96accbb59db525670dd1287ae2a6aa203d6378`。用户决定唯一剩余新增功能为手动联网更新官方中国域名列表，其余基本不用开发、进入测试；高级功能冻结/OUT_OF_SCOPE 按原决定。B82 [产品CI](https://github.com/lly8666/wbd-next/actions/runs/45364555540) 9 SUCCESS/1 FAIL/5 SKIPPED；正式ARM64 APK构建、签名及原Go/Rust wiring实际PASS，普通测试APK Host TCP/UDP字节回显PASS（[APK Job](https://github.com/lly8666/wbd-next/actions/runs/45364555540/job/138344431177)），末尾旧B17源码断言FAIL；[维护](https://github.com/lly8666/wbd-next/actions/runs/45364555688) 与[功能目录](https://github.com/lly8666/wbd-next/actions/runs/45364555515) SUCCESS。

- 审阅历史NativeBridge、x86原生KSU和SLIRP/TAP证据，分开 Go ELF139、Rust翻译、Java ART和网络阻塞，保留旧真实证据。
- 新复用冷套件：一轮原 x86 KSU Android16 guest 的普通App UID 上执行既有6类生产Java helper 测试、原x86 Go help、真实 Root/Network；同guest 复用原NDK launcher 调原ARM64 Rust MTU ABI四类黄金值与历史原Go c-shared help。无生产协议/数据面变化。旧D2 SLIRP 另选，TAP/原ARM64 ELF139不重跑。
- 新仅下载同SOURCE已构建产物的手动workflow，避免重复双ABI和Linux oracle。旧B17断言按实际所有单lane共享padding入口修正，不改产品代码。新套件未运行、真机未运行；实际资格按新SOURCE输出。仅实验分支，main/M0未动。

详见 [x86 复用计划](../../plans/ANDROID_ROOT_X86_REUSE.md)。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"User-directed feature freeze except manual official CN domain update; reuse historical x86 KSU and ARM64 NativeBridge for bounded real ART/MTU/Go cold tests and artifact-only workflow."}
```
