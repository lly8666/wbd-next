# B122｜DNS6 capability, retain IPv4 path

B121 device report source f7845b3 records selected Network hostname resolution, real TLS/authenticated lease/M4, DNS4_READY then ROUTE_FAILED_DNS6. B121 hosted Android x86 KSU job 139273613471, artifact 15031468992, independently reproduces exact boundary (DNS4_READY, DNS6 failure, exit1), whereas host Linux IPv6 NAT and B121 low-MTU recovery pass. Exact kernel errno of previous builds is not recorded.

References:
- https://wiki.metacubex.one/en/config/inbound/tun/ : Android auto-redirect limitations, capability check for IPv6.
- https://wiki.metacubex.one/config/dns/ : local AAAA empty answers independent of DNS transport.
- https://sing-box.sagernet.org/configuration/inbound/tun/ : existing TUN routes, DNS handling, unsupported network unreachable.
- https://android.googlesource.com/kernel/common/+/refs/heads/android14-6.1-2025-12/arch/arm64/configs/gki_defconfig : IPv4 NAT enabled; IPv6 filter/mangle/raw enabled, no IPv6 NAT in this configuration. Do not assume every vendor kernel shares this config.

B122 default drop mode probes IPv6 NAT once before DNS6 mutation; if missing or listener unavailable, or a newly created DNS6 owner failed with verified rollback, preserves DNS4 + existing scoped IPv6 entry drop, suppresses AAAA locally, skips downstream IPv6 NAT when DNS6 unavailable. No physical DNS fallback. Explicit SIT retains existing required semantics. Existing DNS6 journal recovery remains required. Report and status explicitly identify degraded DNS6; IPv6-destination DNS is NOT delivered in this mode and local-address exceptions still apply. This does not promise DNS6-only network or hotspot IPv6 DNS success. No new data path, no global sysctl or physical-interface mutations.

Hosted test checks actual kernel NAT availability independently, demands DNS6-ready when available or explicit NAT-probe limitation when unavailable, requires IPv6 drop ready plus real ordinary-App IPv4 TCP/UDP, real A and AAAA UDP/TCP, and owned Stop. For supported kernel also probes IPv6-destination DNS. The kernel compatibility hypothesis and real Android behavior remain pending until CI. Physical WiFi/USB/CN downstream tests remain unproven. No main change or broad regression.

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Avoid fatal default IPv6 NAT dependency, keep IPv4 DNS and scoped IPv6 drop; report unavailable IPv6 DNS explicitly and qualify real Android paths."}
```
