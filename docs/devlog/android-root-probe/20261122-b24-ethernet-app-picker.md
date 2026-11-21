# B24｜Android Root Ethernet原物理出口 + 多App本地搜索/批选 + 刷新保持Network

基线 `17a5343ce6fcfb8cccf9f7d632b494a6136f88b3`；B23签名Root APK/双ABI/Host/Linux oracle 11 SUCCESS、4个显式KSU客体SKIPPED。用户要求多完成日常功能，不用极端工况、防御框架和额外高CPU控制器。

1. **真实Ethernet物理出口**：原`PhysicalNetwork.available()`接受Android `TRANSPORT_ETHERNET` 上持有INTERNET且非VPN的真实ConnectivityManager Network，继续检查真实接口、ifindex、接口IPv4与LinkProperties一致、MTU；原RootService `onCapabilitiesChanged`复用相同 `PhysicalNetwork.physicalInternet()`，避免APP能选ETH但Service马上因WiFi/蜂窝专用门误Stop。原Go FakeTCP/TLS、原Rust M3/M4及物理RAW网卡绑定均不变，未宣称普通USB Ethernet设备必定合格。
2. **物理Network刷新与返回Activity**：刷新后继续选中严格同一Network handle/interface/index/IPv4/MTU；`onResume`读回现在的物理候选，不从旧离线句柄重连；当前运行中的Root owner仅由原Service watcher管理，UI不会自动换物理口或Root Start。
3. **真实选定App列表批选**：只在selected-app模式新增本地名称/包名/UID过滤（过滤时隐藏项目不会抹掉原勾选）、勾选匹配项按钮与一键清除。新生产纯Java `RootAppPickerModel`复用 `SelectedAppGroup.from()`判断最多8个不同UID/16包，先验证整个候选集再修改UI，最终Start仍依赖 `InstalledAppCatalog.stillSameGroup`和Service二次核验。**不请求QUERY_ALL_PACKAGES**，当前只展示已可见launchable App；无启动图标或Android系统不可见App不假装可选。
4. 正式Host编译和测试 `RootAppPickerModel`的UID/包名匹配、大小写、隐藏保留、重复UID去重、超8 UID与空筛选拒绝。App源码门核验Ethernet双侧物理条件和 onResume精准刷新；同源签名ARM64 Root APK、Bionic原 Go/Rust及原Linux Host Oracle由Actions决定。实体设备DNS/netd、Auto调档、真实应用TCP/UDP和CPU/吞吐均NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B24 original Ethernet physical Network/Service callback shared eligibility, exact UI refresh retention, and local launcher-App name/UID filter with bounded batch selection; no new data plane"}
```
