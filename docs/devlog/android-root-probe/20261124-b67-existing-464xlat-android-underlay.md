# B67｜现有 Android 464XLAT：IPv6-only Network 承载原 IPv4 FakeTCP

B66 `208de1c4b057767a71e2f411c840e0f0273c1627` [#45318384026](https://github.com/lly8666/wbd-next/actions/runs/45318384026) 查询时 DNS host 新测试已通过、治理通过，整构建未完。

Android 11+ public LinkProperties NAT64 /96、同真实 ConnectivityManager Network、parent usable IPv6 与 AOSP ClatCoordinator `v4-<parent>` RFC7335 /32，实际 kernel ifindex/MTU；native IPv4优先，CLAT仅IPv6-only。UI显示464XLAT，原START/cold recovery/rotation传原Network handle + translated ifname + IPv4 + MTU；Go在原SYN前检查真实parent/CLAT地址和选定netId route-get，原Bionic RAW bind、TLS/Admission/M4正常执行，不创建/删除/改配置clat，不使用额外翻译线程。CLAT已扣减的IPv4 MTU直接进入原outer budget，不重复减头。CLAT /32不是LAN，auto direct只保留手动CIDR；prefix/link失效走原Stop/Network callback。AOSP [ClatCoordinator](https://android.googlesource.com/platform/packages/modules/Connectivity/+/96a3f144a785872d624b63e2015f55545a5dcff5/service/src/com/android/server/connectivity/ClatCoordinator.java)。Host真实生产scope判定与Android ELF/签名APK按同源CI；IPv6-only实体承载、运营商PLAT/raw兼容NOT_RUN。内层IPv6包/认证IPv6租约/server shared-TUN分发仍MISSING，未改原IPv4协议或M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B67真实Android IPv6-only Network已有CLAT选择/原IPv4 FakeTCP绑定/MTU/route-get/冷恢复；内层IPv6仍待开发，实体未验。"}
```
