# B123 — IPv4-only Android default and scoped tether RA

User explicitly does not require DNS sent to IPv6 destinations: discard IPv6 as normal traffic. APK no longer requests system DNS6. Managed IPv4 DNS is independent of the old DNS6 setting, still returns local AAAA NODATA. Delete B122 capability/degraded startup and B120 managed downstream IPv6 DNS listener. No NAT6 commands in new default drop plans. Retain old journal reader/commands for exact upgrade cleanup, and older explicit advanced SIT behavior, not part of default. Do not alter protocol, Rust steady-state, B118 offload, or IPv4 tether.

AOSP RouterAdvertisementDaemon (https://android.googlesource.com/platform/packages/modules/Connectivity/+/311feaff8b4a66b0c8a7bc5ed72f916d666c683e/Tethering/src/android/net/ip/RouterAdvertisementDaemon.java) uses AF_INET6 SOCK_RAW ICMPv6. One scoped ip6tables filter OUTPUT rule blocks ICMPv6 type 134 on selected WiFi/USB downstream. Existing IPv6 journal owns/removes the rule; old journal defaults SuppressRA=false. No address deletion, no global sysctl, no new process, no polling, no DHCP change. Existing clients may retain old RA information until expiration or reconnect, link-local addresses remain; no claim of immediate withdrawal, hardware RA bypass not proven. IPv6 forwarding still enters existing drop path.

CI: real KSU default all-app path must reach auth/business A/AAAA and show no DNS6 owner; existing Linux namespace tests verify true TUN IPv6 entry and low-MTU drop/recovery; new veth namespace test sends actual ICMPv6 RA and checks exact selected-interface counter, other ICMPv6/interface unaffected and Stop restoration. Real Android WiFi/USB RA capture remains pending device test.

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Remove default IPv6 DNS setup, retain IPv4-only policy and scoped downstream RA suppression."}
```
