# B38｜当前所选实体Network IPv4 on-link子网进入原UID私有直连

## 真实功能缺口

B33已经有生产 `RootDirectIPv4.canonicalCSV` →App/Service→原Go `--android-direct-cidrs` →`rootjournal.ParseDirectCIDRs` →owned UID 私有FIB throw路线，但用户要手抄 `192.168.1.0/24` 这类本机路由器直连段。B38在原App增加显式“自动加入所选物理Network的直连子网”：读取的是用户START所选的真实ConnectivityManager.Network `LinkProperties.getLinkAddresses()`，必须匹配已选IPv4源地址，按其前缀生成规范network CIDR；跟已有手填项合并去重，统一最多4项。Service同Network冷核对再将同一规范CIDR交已有原Go Root FIB管线。

- 默认关闭，不更改Normal/off、Fixed/Auto、DNS、TLS、租约、M3/PN/AEAD、Rust M4、generation/Stop，也不改Android main/default路由；
- 并入原throw规则只代表所选普通App UID先跳过WBD TUN，随后由Android自身路由处理，**不保证物理出口一定是用户选中的接口**；
- 用现成RootDirectIPv4及RootConnectionSettings保留用户冷开关与旧预设默认；Host测试涵盖规范网段、重复、4条配额、/32、错误前缀，源门追踪Go原rootjournal入口；实机UID路由、应用LAN TCP/UDP和设备切网NOT_RUN。

B37之前原Rust Health15/30在源码独立接通，CI结果不得由B38源码继承。B38源码/签名APK及Linux Oracle验收以自身同SOURCE Actions为准，不能把Host语法绿灯写成Android App E2E。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B38从用户所选真实Android Network的IPv4 LinkAddress自动构建on-link直连CIDR并复用B33原Go Root UID私有FIB throw，不新增数据面。"}
```


## 同 SOURCE 最终软件收据（2026-11-22）

B38产品 SOURCE [`41c374f4e83d`](https://github.com/lly8666/wbd-next/commit/41c374f4e83decf4d1446ac63688a592a0b7d396) 的 [Android dual64 #45028073114](https://github.com/lly8666/wbd-next/actions/runs/45028073114)：`arm64-native`、`root-arm64-app`、`linux-original-server-normal-off`、`linux-x86-original-server-d2-s0`、原M3、B1/B2 DNS 及相关Host共 **11 SUCCESS**；四个 Android x86/KSU 原生/NativeBridge/D2/TAP诊断 **SKIPPED**。Cuttlefish是host admission PASS，不是ARM64 Android guest实连。同步 [治理 #45028073121](https://github.com/lly8666/wbd-next/actions/runs/45028073121) Feature catalog SUCCESS，Governance Job SKIPPED。B38和此前 [B36 #45027169236](https://github.com/lly8666/wbd-next/actions/runs/45027169236)、[B37 #45027641087](https://github.com/lly8666/wbd-next/actions/runs/45027641087) 各有独立 11 SUCCESS / 4 SKIPPED 资格。最新代码尚无 Android 真实 App LAN TCP/UDP、System DNS、Game2/4、IPv6或性能PASS；以上均NOT_RUN/NOT_PROVEN。
