# B34：原Android Root全App排除 + 物理DNS上游配置，合并大类施工

上一原生SOURCE `dd2292c8` [Android dual64 #44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) 签名APK、Go/Rust Bionic双ABI、原Linux Server Oracle **11 SUCCESS/4 SKIPPED**。本批直接对照当前Root App与原Go/Rust产品实现，不造新流量面；新SOURCE是否HOST/BUILD PASS以后续Action为准。

**全App绕过**：Root Activity新增可筛选/勾选的真实安装包额外绕过（最多6包），单/组代理选择不受影响；本地noBackup/SAF预设记住非秘密包名+UID。START和Service及SU前在PackageManager核对真实身份，Root Manager及绕过包一起监听安装变更并撤销原Owner。归并到`AllAppUIDPolicy.excluded(owner,managerUIDs,bypassUIDs)` 仍最多8个AppID，原Go `--android-route-exclude-appids`、原20 profile UID `rootjournal.AllAppPlan.ranges()`、table19842、同一锁/journal/Stop全复用；共享UID/同AppID跨profile均排除。系统/root UID仍未包含，Android后续netd物理选择NOT_RUN。

**真实物理DNS上游**：新增Root App IPv4表单、Service冷参数、设置/SAF；原Go验证 `--android-physical-dns-upstream-ipv4`（仅物理/CN DNS模式），默认223.5.5.5，用户可填所选Network可达本地路由器DNS如192.168.1.1。原Go `V4LinuxClientProductConfig` 在TLS/租约/真实RAW/TUN之后调用Rust M4新**冷设置＋逐字节读回**，原Rust `Entry` 当前generation储存4B，现成 `AndroidBoundPhysicalDnsUdp::open` 经Bionic `android_setsocknetwork`/SO_BINDTODEVICE及本机IPv4读回，连接用户所选IPv4:53。无新增DNS/TUN包泵；Go自己的服务器域名原223.5.5.5 bootstrap完全不变。

**验收分层**：既有Host JVM测试校验真实AllAppUIDPolicy/Settings/原Go argv/IPv4拒绝，Go dnsnative原验收及ARM64 Rust导出符号使用原workflow；无新重型CI、无个人手机或服务器操作。Android真实App TCP/UDP交付、实际netd后续路由、系统Resolver/DoH、IPv6/CLAT、Game2/4、物理TCP53、吞吐与CPU继续NOT_RUN/MISSING，不得虚报。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B34原Root全App真实安装包额外绕过继续复用原20-profile UID FIB/Stop，物理DNS IPv4上游从App/预设/Go冷配置接原Rust已认证M4绑定Socket，含生产源Host回归"}
```
