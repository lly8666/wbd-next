# Android KSU 系统 DNS + TLS 1.3：真实全绿收口（2026-11-16）

**范围：Android16/API36 x86_64 一次性 AVD，真实 KernelSU3.3.1 LKM、官方Manager单包授权、SELinux Enforcing。** 源码 `32008210b41a4764b77856a8dd81ec9a47c88f83`，[Action43843733837](https://github.com/lly8666/wbd-next/actions/runs/43843733837) **SUCCESS**；普通安装 APK `org.wbdnext.rootprobe` targetSdk37、UID10218 / untrusted_app，App实际su -c退出0、Root子进程UID0。主线M0/真机boot/system/SELinux未改，无adb-root冒充App授权。

## 数据面实测

| 项目 | 真实结果 |
|---|---|
| 系统Resolver | 普通App `Network.getAllByName("example.com")` 通过活动Network **100** 返回IPv4+IPv6共**4个地址**，其中IPv4 `104.20.23.154`、`172.66.147.243`；15ms，**不是**旧版App手工构造DNS |
| 经netd默认Network的 TLS | 普通App `Network.bindSocket` 经模拟器虚拟`wlan0`到宿主10.0.2.2:18318，真实JSSE **TLS1.3**、`TLS_AES_256_GCM_SHA384`、证书链及主机名 `wbd-ci-host.test` 校验PASS；双方收发同一个随机nonce |
| 一次性测试证书 | CI当场生成X509证书；仅公钥DER进入APK，私钥仅在runner且不提交、不上传；App在独立临时信任库校验。公钥SHA256 `a4ffd371e58b54f3bab7dace16523eded850e9691dd30c14f2314f536303d6d6` |
| UDP ↔ Root TUN | 普通App发40B，TUN收68B IPv4/UDP、注入70B，App收42B匹配nonce，PASS |
| App直发DNS53 | 32B `probe.wbd.test.` A查询、48B DNS答（IP/UDP76B），PASS，与Android系统Resolver是两个不同门槛 |
| TCP/HTTP TUN | Java真实Socket SYN/HTTP GET76B、Root回复HTTP200/97B（IP/TCP137B）、App ACK，PASS |
| 默认网络不误劫持 | Network100虚拟wlan0绑定普通TCP连宿主10.0.2.2:18317，宿主nonce回显；当精确UID/32规则仍存在时Root TUN读到App完成标记，PASS |
| 清理 | `pref8200 uidrange10218-10218 to198.18.254.2/32 lookup235`：TUN关闭，系统IPv4 rules/all routes前后字节一致；Root worker真正SIGKILL退出137，独立watchdog发现并删除孤立规则，PASS |
| CI资源退出 | 模拟器收尾有界，`ksu/cleanup.log`显示09:56:20进入、09:56:22退出，无780s死等，整体Action SUCCESS |

## SOURCE、SHA256 原始证据

GitHub [Action43843733837](https://github.com/lly8666/wbd-next/actions/runs/43843733837)，artifact **14214651040**，**116文件**，ZIP SHA256 `3be4e95760d8762df3407fb6d103ca2ec5773ef4d43327ef05d6547c7d03f92d`，已下载独立比对：
- `mainstream/app-mainstream.json` SHA256 `d76faae18674fba3fb3ca5cbad7b62ac81684768564bab28d854e91f5086e406`：`APP_DNS_TLS_MAINSTREAM_PASS`，真实App子进程 su exit0。
- `mainstream/summary.json` SHA256 `087090a84180291f5210b90ad467e654f5933d8bd01f088462ef3a8ff845ab57`：`MAINSTREAM_DNS_TLS_PASS`、errors=[]；证书sha与APK manifest相同。
- `mainstream/host-echo.log` SHA256 `35066ad717342fb8f1e9873ffcd01b1eb0d1857854ed2668afa5fcd12ee416ff`：宿主`HOST_TLS_ACCEPT`真实TLS1.3 cipher与App nonce。
- `ksu/summary.json` SHA256 `f6131d666bb0d06676bf412f698151fbb2a847019f72fb376680fda383f80a52`；`appflow/summary.json` SHA256 `877d49a18f63eafeee37b08cc024cfe6b05fd0860f2697f474c2b6ab5259755e`；`appflow-crash/summary.json` SHA256 `30da79d518b03133c1123183b33686b1632b09c6c1d62bab337c1e2da3e4fc68`。
- `apk/manifest.json` SHA256 `93fecf09d703ea67fec0d061d8fd4da8a3fa3d17a4d4d378407164a129072180`；`native/manifest.json` SHA256 `f1d9e91702cd35d40552d75435b0adfc2aedc640d7151aa59153c8e79eab4479`，都锁定本SOURCE。
- `ksu/cleanup.log` SHA256 `1bd37538b1db070a75c8674cba3ba68a16516122c822a7b89ccdfdb190c9fe58`。原始ZIP中三个工况的IP rule/routing before-after均逐字一致。

## 失败来源与未测项

- `e1d73f4046b5f8c36958159a9c339d1403eaf7e3` [Action43839583300](https://github.com/lly8666/wbd-next/actions/runs/43839583300) 原样 **CI FAIL**：App DNS/TLS等功能已通过，却在 emulator EXIT 无界wait中遭780秒总超时；artifact14212689127 ZIP SHA256 `49cc4e33ca7ed41ea351da43a2840097c17b71e5f7f7031d407bf5abfbd91555`。
- `83cadd9e24bfa0f9c7fa8db00acbb598896ac479` [Action43842381940](https://github.com/lly8666/wbd-next/actions/runs/43842381940) 原样 **CI FAIL**：模拟器虚拟host 10.0.2.2普通App Network.bindSocket偶发4.5秒TCP超时，故未执行后续系统DNS/TLS；artifact14214096151 ZIP SHA256 `0103f899ee29622f96faa1e95cc2d5f0e7a71cd8dab98009270e5e938feb8f14`。当前源码保留真实netd Network绑定，仅对ConnectException/SocketTimeoutException执行普通host≤3、TLS≤2次有界重试。本次实际均**第1次成功**，不代表重试/切网恢复已通过。

**边界：** 系统DNS通过的是默认Network，不是经过Root TUN的系统DNS转发；受控TLs用独立一次性信任锚，不是公众CA/透明TLS代理。模拟器wlan0非实体WiFi/蜂窝；真实IPv6/CLAT数据转发、实际双网切换、NAT/conntrack、热点USB下游、生产FGS及设备重启恢复、物理ARM64/OEM/16KiB **NOT_RUN**。仅限用户授权的实验分支，主线M0不动。

[机器可读证据矩阵](20261116-ksu-dns-tls-matrix.json)。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Source-locked full-success Android16 real KSU system netd resolver and authenticated TLS1.3 with all prior App TUN/cleanup gates, physical NAT/tether/roaming not run."}
```
