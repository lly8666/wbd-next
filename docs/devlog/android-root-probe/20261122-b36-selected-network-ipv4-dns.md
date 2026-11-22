# B36｜选中Network的IPv4 DNS直达原Go/Rust

B35自定义物理DNS数值已由App/Service→原Go peer-host原DNS wire UDP/TCP53→原Rust已认证M4物理UDP53完整接线，缺的是**用户已经选好的实体Network的LinkProperties DNS自动来源**。B36新增一个显式跟随开关，START读当前选中Network的DNS列表，仅取IPv4；Service于root前用同一Network的最新LinkProperties核对。没有Android默认网络回落或数据面DNS worker；原Go/Rust重用现成自定义上游，不改变握手、认证、/32租约、M3/PN、UID路由、Stop。未勾选默认仍223.5.5.5或手动地址。

本机/SAF预设只保存“是否跟随所选Network”的布尔值和手动备用IPv4，不缓存旧Network handle或启动时解析出的DNS。旧预设自动false。IPv6-only DNS明确不可在当前IPv4物理DNS路径使用；用户可改手动IPv4。测试是Host纯Java真实生产选择函数（含IPv6先行、无IPv4、无效IPv4）、预设往返及App→Service源码门；双ABI/签名APK/原Linux Oracle独立以本SOURCE Actions为准；不声称真实Android查询、App TCP53物理出站、系统netd DNS、IPv6业务或Game已通。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B36原Root App将用户选定的ConnectivityManager.Network IPv4 DNS冷接入B35原Go及B34原Rust的既有上游，不新增DNS热路径。"}
```
