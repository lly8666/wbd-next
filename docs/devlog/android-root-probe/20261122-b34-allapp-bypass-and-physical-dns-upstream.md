# B34：原Android Root全App排除 + 物理DNS上游配置，合并大类施工

上一原生SOURCE `dd2292c8` [Android dual64 #44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) 签名APK、Go/Rust Bionic双ABI、原Linux Server Oracle **11 SUCCESS/4 SKIPPED**。本批直接对照当前Root App与原Go/Rust产品实现，不造新流量面；新SOURCE是否HOST/BUILD PASS以后续Action为准。

**全App绕过**：Root Activity新增可筛选/勾选的真实安装包额外绕过（最多6包），单/组代理选择不受影响；本地noBackup/SAF预设记住非秘密包名+UID。START和Service及SU前在PackageManager核对真实身份，Root Manager及绕过包一起监听安装变更并撤销原Owner。归并到`AllAppUIDPolicy.excluded(owner,managerUIDs,bypassUIDs)` 仍最多8个AppID，原Go `--android-route-exclude-appids`、原20 profile UID `rootjournal.AllAppPlan.ranges()`、table19842、同一锁/journal/Stop全复用；共享UID/同AppID跨profile均排除。系统/root UID仍未包含，Android后续netd物理选择NOT_RUN。

**真实物理DNS上游**：新增Root App IPv4表单、Service冷参数、设置/SAF；原Go验证 `--android-physical-dns-upstream-ipv4`（仅物理/CN DNS模式），默认223.5.5.5，用户可填所选Network可达本地路由器DNS如192.168.1.1。原Go `V4LinuxClientProductConfig` 在TLS/租约/真实RAW/TUN之后调用Rust M4新**冷设置＋逐字节读回**，原Rust `Entry` 当前generation储存4B，现成 `AndroidBoundPhysicalDnsUdp::open` 经Bionic `android_setsocknetwork`/SO_BINDTODEVICE及本机IPv4读回，连接用户所选IPv4:53。无新增DNS/TUN包泵；Go自己的服务器域名原223.5.5.5 bootstrap完全不变。

**验收分层**：既有Host JVM测试校验真实AllAppUIDPolicy/Settings/原Go argv/IPv4拒绝，Go dnsnative原验收及ARM64 Rust导出符号使用原workflow；无新重型CI、无个人手机或服务器操作。Android真实App TCP/UDP交付、实际netd后续路由、系统Resolver/DoH、IPv6/CLAT、Game2/4、物理TCP53、吞吐与CPU继续NOT_RUN/MISSING，不得虚报。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B34原Root全App真实安装包额外绕过继续复用原20-profile UID FIB/Stop，物理DNS IPv4上游从App/预设/Go冷配置接原Rust已认证M4绑定Socket，含生产源Host回归"}
```


## B34a｜修正旧B29冷授权计数，保留同源Native通过证据

B34原始SOURCE `d4a74893` 的六项DNS/M3 Host、Go/Rust Android ARM64/x86_64原生编译已经SUCCESS，新B34两类纵向源检查也PASS。正式APK源码门遇到旧B29静态计数：B29此前三处 `!android_dns_original_m4_ready(&e)`，B34为真实物理DNS上游冷设置在**同一已认证M4代际**增加第四处，这是必需的新门，而不是重复虚假授权。将旧计数3更新为4，保留B34新冷ABI符号/读回检查及所有旧业务门。真实用户手机、netd及TCP53仍NOT_RUN。新SOURCE另看Action，不能把首次失败改写为成功。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B34a原Rust物理UDP53上游冷设置增加第四处同代M4 readiness门，修正旧B29仅计三处的源码门假设；原业务Go/Rust代码保持原样"}
```


## B34b｜同SOURCE双ABI、签名APK、原Linux Oracle全部SUCCESS

B34a原生产代码SOURCE `d70132608bf5772f61098199f1910dc13e542ecd` 的 [Android dual64 #44978243692](https://github.com/lly8666/wbd-next/actions/runs/44978243692) **11 SUCCESS / 4 SKIPPED**，包括Android Go/Rust双ABI、签名ARM64 Root APK、Java生产App/预设/原Go argv测试、原Linux server Oracle、真实Rust M4 DNS源及Host套件；[治理 #44978243728](https://github.com/lly8666/wbd-next/actions/runs/44978243728) **SUCCESS**。B34原始 `d4a74893` 早期静态门错误仍保留为**FAILED** 历史，而不是删改。

这两类现归类 `WIRED + HOST_PASS + BUILD_PASS`，不需要再次造全App控制面、独立DNS套接字或新的Packet worker。所有 Android 真实物理出站、系统netd DNS、App字节级业务E2E、局域网UDP DNS实机返回、Game2/4、IPv6/464XLAT、物理TCP53及CPU/首包延迟仍按 `NOT_RUN/MISSING` 记录，没有设备授权，不可声明成功。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B34b将已同源验证的全App额外绕过和原Rust物理DNS IPv4上游从CANDIDATE升级为HOST/BUILD_PASS，官方Action #44978243692 11 SUCCESS/4 SKIPPED，保留实体NOT_RUN"}
```
