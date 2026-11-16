# Android KernelSU 普通 App 主流网络路径 — 实测收口（2026-11-16）

**仅 Android16/API36 x86_64 真 KernelSU3.3.1 一次性 AVD：FUNCTIONAL_PASS。** SOURCE `47f501dacb2284a06582d6d8449203d6e06871f3`，实际 [Action43833012235](https://github.com/lly8666/wbd-next/actions/runs/43833012235) **SUCCESS**；普通 APK targetSdk37、UID10218、SELinux untrusted_app，经真实 KSU Manager 单包授权，App调用su退出0、原生子进程UID0。不是adb-root/假su；全程SELinux Enforcing。

| 普通 App 业务路径 | 真实结果 |
|---|---|
| UDP双向 | 普通App UDP40B nonce→Root TUN实收完整IPv4/UDP **68B**→Root TUN回注**70B**→App自身Socket收到42B：PASS |
| DNS UDP53 | App直发32B A查询 `probe.wbd.test.`，Root TUN返回DNS48B（完整IPv4/UDP76B），App验证事务ID、来源和A=198.18.254.2：PASS |
| TCP/HTTP | App Java Socket三次握手、发送76B HTTP GET；Root TUN实际见SYN/GET，回97B HTTP200（IP/TCP137B），确认App内核ACK、App读取nonce body：PASS |
| Android netd 默认Network | 普通App通过 `ConnectivityManager.getActiveNetwork`／`Network.bindSocket` 使用Network **100**、虚拟`wlan0`、5条路由，与模拟器宿主 `10.0.2.2:18317` 完成真实TCP nonce回显：PASS |
| 防误劫持 | 宿主回显完成后App向仍存在的UID→TUN单目标规则发送完成标记，Root TUN收到73B IP/UDP，证明默认出口通信发生在规则未删除期间：PASS |
| 正常及异常清理 | UID10218-10218→198.18.254.2/32、pref8200/table235，TUN销毁，Android全IPv4规则与路由前后字节一致；同SOURCE Root worker SIGKILL退出137，watchdog删除确实存在的孤立规则：PASS |

## 独立复核的制品与 SHA256

- CI [43833012235](https://github.com/lly8666/wbd-next/actions/runs/43833012235)，artifact **14209673218**，113文件，ZIP SHA256 `890e59d510d1390e4f43407d4b5a77f5f732e9383851e41f75a05a46669374a3`，已独立下载核对。
- 普通App私有 `mainstream/app-mainstream.json` SHA256 `eedc6261cbec6a4f5e9a654c8429fff7aaaafe878551ea6da417e8cd55587106`，`APP_MAINSTREAM_NETWORK_PASS`。
- host端 `mainstream/summary.json` SHA256 `d2c902946cbb6a40492056327542f1c02eff049d102e6ad97841b610f9997901`，`MAINSTREAM_APP_NETWORK_PASS` 且errors=[]。
- 本次原生 `native/manifest.json` SHA256 `8a8008c347fd1d15796b3ab6993adc4a0321a642b809a41697fe04adb2c7d26f`，Bionic x86_64二进制 SHA256 `8ad232cbbe644bd0e9f8f56cfe7f6f343a5ee2efb5fbb6d440e34b0d605dd5ad`。
- `ksu/summary.json` SHA256 `a8a15b4f0fc4f3c46628cd358566e68dddb574a68b0367421598115de60810d9`；`mainstream/rule-before.txt` 和after、route-before与after均逐字相同。[结构化证据矩阵](20261116-ksu-mainstream-matrix.json)。

## 未测边界

这是**App直发DNS/53**，不是系统DNS resolver/PrivateDNS/DoH的资格；受控Root TUN TCP+HTTP回复不是通用透明TCP/TLS代理；模拟器 `wlan0` 是虚拟Wi-Fi，不能冒充真实WiFi/蜂窝双网切换。没有全局netd策略修改、真实互联网路由或NAT/conntrack、物理热点/USB下游、真实ARM64/OEM/16KiB、IPv6/CLAT、长期FGS、断网自动恢复，这些都为NOT_RUN。主线/M0/共享核心与真实设备均未改动。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Register exact-source real Android16 KSU ordinary-App UDP, DNS53, TCP HTTP and netd-bound host underlay PASS with unchanged routes and SIGKILL recovery, leaving physical/NAT/system DNS unqualified."}
```
