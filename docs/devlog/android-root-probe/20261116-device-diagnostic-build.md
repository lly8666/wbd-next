# 2026-11-16 WBD Android 实体设备 Root 资格诊断 APK 开工

## 已有 SOURCE 与不足

仅在 `experiment/android-temp-root-probe`。原真实 KSU3.3.1 Android16/API36 x86_64 试验 SOURCE `a5cca542f93e7c256145e07d7432b4dfa388e7c7` 的 [Actions43872821388](https://github.com/lly8666/wbd-next/actions/runs/43872821388) PASS：普通App→su UID0、TUN UDP/DNS53/TCP、TLS1.3、SIGKILL owned 清理、隔离命名空间的 2 Wi-Fi+1 USB 合成来源 SNAT/conntrack、真实按钮恢复自有规则。实体热点、USB、IPv6-only蜂窝/CLAT、真实原产品VPN仍 NOT_RUN。此前APK依赖 ADB 预推原生程序到 `/data/local/tmp`，不能直接上手机测试。

## 本次实现

- `DeviceDiagnosticActivity` 提供两步明确用户触发：只读Root环境/能力观测；短时 Root 内核 TUN/raw、IPv6 TUN、SO_MARK策略路由及合成共享NAT实测；按用例产生 PASS、PERMISSION_DENIED、ENV_BLOCKED、FAIL、NOT_RUN/原因、errno、原生证据并持久保存可复制/分享JSON。
- App 先检查实际 Android `nativeLibraryDir/libwbdprobe.so`，然后由应用UID调用用户已有 `su -c`；原生 `devicecheck` 输出 SELinux context/enforce、真实UID0、CapEff/CapBnd、内核/SDK/ABI/page size、只读网络接口及 Tethering/BPF观测。不自行root、不关闭SELinux、不可打开未知系统选项。
- 新 `ipv6gate` 仅在新建并验证的空 `CLONE_NEWNET` 里创建非持久 TUN，真实双向 IPv6 UDP 包及校验和；无需修改手机主网络空间IPv6/DNS/iptables。现有 `routegate` 与 `tethergate` 在各自私有命名空间检查，主网络空间前后快照必须相等。
- 自包含双ABI ELF：APK 内 `lib/arm64-v8a/libwbdprobe.so` 和 `lib/x86_64/libwbdprobe.so`，`extractNativeLibs=true`，所有 PT_LOAD 对齐16KiB；Android 10+禁止从可写app私有文件夹直接执行，所以采用系统解压至只读 nativeLibraryDir 的ELF。单APK、最低SDK28，targetSdk37。应用内不实现 VpnService、不连接真实 WBD服务器。用户自行通过Root管理器授权。
- Root+TUN+raw实际操作全通过才是 CORE_IPV4_ROOT_PROBE_PASS；即便如此，真实Wi-Fi热点和USB共享出口、offload、蜂窝切换、原WBD认证TLS及后台FGS均标 NOT_RUN，绝不偷换为产品PASS。
- 本独立诊断不持久修改Android主 netns，没有生产网络Rule journal；已有原AVD恢复规则独立作用于明确8200/235/UID/32，**本手机APK不会假装能清理其他Root程序的系统网络变更**。所有实验对象均通过短时fd/私有netns结束回收。

## 验收门

使用同SOURCE、同一次CI临时签名证书构建旧测试APK与新设备诊断APK，双ABI Rust交叉编译，对APK签名/ABI/elf对齐/SHA256与SOURCE锁校验。真实 KSU Android16 x86_64 AVD保留旧全部正例；最后 `adb install -r` 新APK，**仅通过真实App UI按钮与自身su调用内置原生程序**，禁止本新case ADB push原生可执行文件。核验真实 UID0/SELinux/Cap/TUN/raw/隔离NAT、IPv6正例或精确阻塞理由、文件导出的JSON和主namespace路由规则不变。Actions SUCCESS != 真机共享VPN PASS。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Add standalone dual-ABI embedded-native on-phone Root eligibility diagnostic, IPv6 TUN and exact per-check failure classification; retain actual physical tether NOT_RUN."}
```
