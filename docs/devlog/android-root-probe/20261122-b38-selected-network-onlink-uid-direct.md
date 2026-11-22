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
